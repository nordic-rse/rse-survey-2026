"""Run one select-question view end to end, and register it as three tasks.

frame → optional recoding → summary → artifacts. The three registered tasks
differ only in which ``GroupingSpec`` they pass.
"""

from __future__ import annotations

from pathlib import Path

from rse_survey.analysis.context import AnalysisContext, TaskResult
from rse_survey.analysis.registry import register
from rse_survey.analysis.summarize.categorical import (
    apply_category_order,
    summarize_by_group,
)
from rse_survey.analysis.summarize.categories import (
    apply_category_groups,
    apply_category_labels,
    apply_hf_coded_categories,
    filter_closed_answers,
    other_labels_by_country,
    token_labels_csv_path,
)
from rse_survey.analysis.tasks.select_questions.artifacts import (
    write_artifacts,
    write_between_countries_separate_artifacts,
    write_other_by_country_artifacts,
    write_per_item_artifacts,
)
from rse_survey.analysis.tasks.select_questions.grouping import (
    SELECT_KINDS,
    analysis_frame,
    group_levels_for,
    question_items,
    resolve_grouping,
)
from rse_survey.analysis.tasks.select_questions.summary import build_summary_table
from rse_survey.artifacts.layout import question_artifact_dir


def _write_other_for_question(ctx: AnalysisContext, out_dir: Path) -> dict[str, Path]:
    compare = ctx.compare_df
    if compare.empty or "country_group" not in compare.columns:
        frame = analysis_frame(ctx, resolve_grouping("between_countries"))
    else:
        frame = compare.loc[compare["country_group"].notna()].copy()
    by_country = other_labels_by_country(
        frame,
        ctx.question.question_id,
        ctx.question.closed_categories,
        country_col="country_group",
    )
    return write_other_by_country_artifacts(
        out_dir,
        by_country,
        country_order=list(ctx.book.compare_groups.keys()),
    )


def run_select_question(
    ctx: AnalysisContext,
    *,
    grouping_variable: str | None = None,
) -> TaskResult:
    """Run one select-question view: frame → summary → artifacts."""
    spec = resolve_grouping(grouping_variable)
    qid = ctx.question.question_id
    task_name = spec.stem
    kind = ctx.question.response_kind
    labels_path = token_labels_csv_path(ctx.hf_cache_dir, qid)
    coded_free_text = kind == "free_text" and labels_path.exists()

    if kind not in SELECT_KINDS and not coded_free_text:
        reason = (
            f"{task_name} needs HF token_labels.csv for free_text "
            f"(missing {labels_path})"
            if kind == "free_text"
            else (f"{task_name} is for select questions (got response_kind={kind!r})")
        )
        return TaskResult(
            task_name=task_name,
            question_id=qid,
            skipped=True,
            skip_reason=reason,
        )

    frame = analysis_frame(ctx, spec)
    if frame.empty:
        reason = (
            "no respondents in focus"
            if spec.scope == "focus"
            else "empty compare frame or missing columns"
        )
        return TaskResult(
            task_name=task_name,
            question_id=qid,
            skipped=True,
            skip_reason=reason,
        )

    if spec.group_col is not None and spec.group_col not in frame.columns:
        return TaskResult(
            task_name=task_name,
            question_id=qid,
            skipped=True,
            skip_reason=f"{spec.group_col} missing from clean data",
        )

    out_dir = question_artifact_dir(ctx.artifacts_dir, qid)
    order = ctx.question.category_order
    closed = ctx.question.closed_categories
    labels = ctx.question.category_labels
    groups = ctx.question.category_groups
    with_other = kind == "categorical_with_other"

    if coded_free_text:
        frame = apply_hf_coded_categories(frame, qid, labels_path=labels_path)
        if frame.empty:
            return TaskResult(
                task_name=task_name,
                question_id=qid,
                skipped=True,
                skip_reason=f"no HF-coded answers for {qid}",
            )
    elif with_other:
        frame = filter_closed_answers(frame, qid, closed)
        if frame.empty:
            return TaskResult(
                task_name=task_name,
                question_id=qid,
                skipped=True,
                skip_reason=f"no closed-category answers for {qid}",
            )

    # Aggregate raw values into groups, then optional display renames.
    # closed_categories always match raw survey labels before these steps.
    # HF-coded free_text already uses final category_human labels.
    if not coded_free_text:
        frame = apply_category_groups(frame, qid, groups)
        frame = apply_category_labels(frame, qid, labels)

    # Multi-item arrays (likert grids) carry an extra sub-question dimension:
    # report each item separately instead of pooling them into one distribution.
    items = question_items(frame, qid, ctx.question.item_order)

    files: dict[str, Path] = {}
    if with_other and spec.key == "between_countries":
        levels = group_levels_for(ctx.book, spec) or []
        files = write_between_countries_separate_artifacts(
            frame=frame,
            out_dir=out_dir,
            question_id=qid,
            title=ctx.question.title,
            country_levels=levels,
            presentation=ctx.book.presentation,
            category_order=order,
        )
        if not files:
            return TaskResult(
                task_name=task_name,
                question_id=qid,
                skipped=True,
                skip_reason=f"no answers for {qid}",
            )
    elif items and spec.group_col is not None:
        files = write_per_item_artifacts(
            frame=frame,
            out_dir=out_dir,
            question_id=qid,
            title=ctx.question.title,
            items=items,
            spec=spec,
            group_levels=group_levels_for(ctx.book, spec),
            presentation=ctx.book.presentation,
            category_order=order,
        )
        if not files:
            return TaskResult(
                task_name=task_name,
                question_id=qid,
                skipped=True,
                skip_reason=f"no answers for {qid}",
            )
    elif items:
        # Focus view: items fit on one chart, faceted so paired
        # actual/desired rows sit next to each other.
        summary = apply_category_order(
            summarize_by_group(frame, qid, "item", group_levels=items),
            order,
            group_col="item",
        )
        if summary.empty:
            return TaskResult(
                task_name=task_name,
                question_id=qid,
                skipped=True,
                skip_reason=f"no answers for {qid}",
            )
        files = write_artifacts(
            summary=summary,
            out_dir=out_dir,
            question_id=qid,
            title=ctx.question.title,
            focus_label=ctx.book.focus_label,
            grouping_variable=spec.key,
            group_levels=items,
            presentation=ctx.book.presentation,
            category_order=order,
            facet_col="item",
        )
    else:
        levels = group_levels_for(ctx.book, spec)
        summary = build_summary_table(
            frame,
            qid,
            grouping_variable=spec.key,
            group_levels=levels,
            category_order=order,
        )
        if summary.empty:
            return TaskResult(
                task_name=task_name,
                question_id=qid,
                skipped=True,
                skip_reason=f"no answers for {qid}",
            )
        files = write_artifacts(
            summary=summary,
            out_dir=out_dir,
            question_id=qid,
            title=ctx.question.title,
            focus_label=ctx.book.focus_label,
            grouping_variable=spec.key,
            group_levels=levels,
            presentation=ctx.book.presentation,
            category_order=order,
        )

    if with_other:
        other_files = _write_other_for_question(ctx, out_dir)
        files.update({f"other_{k}": v for k, v in other_files.items()})

    return TaskResult(task_name=task_name, question_id=qid, files=files)


@register
class FocusTask:
    name = "focus"

    def run(self, ctx: AnalysisContext) -> TaskResult:
        return run_select_question(ctx, grouping_variable="focus")


@register
class ByAgeTask:
    name = "by_age"

    def run(self, ctx: AnalysisContext) -> TaskResult:
        return run_select_question(ctx, grouping_variable="by_age")


@register
class BetweenCountriesTask:
    name = "between_countries"

    def run(self, ctx: AnalysisContext) -> TaskResult:
        return run_select_question(ctx, grouping_variable="between_countries")
