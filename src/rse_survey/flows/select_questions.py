"""Prefect flow: one select-question view (focus / by age / between countries)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from prefect import flow, task

from rse_survey.analysis.context import AnalysisContext, build_context, load_frames
from rse_survey.analysis.tasks.select_questions import (
    resolve_grouping,
    run_select_question,
)
from rse_survey.artifacts.layout import question_artifact_dir, write_meta
from rse_survey.config.book_config import load_book_config
from rse_survey.config.paths import resolve_repo_path
from rse_survey.logging_config import flow_result, get_logger

log = get_logger("select_questions")


@task(name="load_context")
def task_load_context(book_path: str, question_id: str) -> AnalysisContext:
    book = load_book_config(book_path)
    focus_df, compare_df = load_frames(book)
    return build_context(book, question_id, focus_df, compare_df)


@task(name="write_view_meta")
def task_write_meta(ctx: AnalysisContext, grouping_variable: str) -> Path:
    spec = resolve_grouping(grouping_variable)
    out_dir = question_artifact_dir(ctx.artifacts_dir, ctx.question.question_id)
    return write_meta(
        out_dir,
        {
            "question_id": ctx.question.question_id,
            "task": spec.stem,
            "grouping_variable": spec.key,
            "focus": ctx.book.focus_countries,
            "response_kind": ctx.question.response_kind,
        },
    )


@task(name="run_select_question")
def task_run_view(ctx: AnalysisContext, grouping_variable: str) -> dict[str, Any]:
    result = run_select_question(ctx, grouping_variable=grouping_variable)
    return {
        "question_id": result.question_id,
        "grouping_variable": grouping_variable,
        "stem": result.task_name,
        "skipped": result.skipped,
        "reason": result.skip_reason,
        "files": {k: str(v) for k, v in (result.files or {}).items()},
    }


@flow(name="select_questions")
def select_questions_flow(
    question_id: str,
    *,
    grouping_variable: str = "focus",
    book_config: str | Path = "config/book.yml",
) -> dict[str, Any] | None:
    """Ordered select-question pipeline: frame → summary → artifacts.

    ``grouping_variable``: ``focus`` | ``by_age`` | ``between_countries``.
    Returns a result dict only when logging mode is ``debug``.
    """
    book_path = str(resolve_repo_path(book_config))
    spec = resolve_grouping(grouping_variable)

    ctx = task_load_context(book_path, question_id)
    task_write_meta(ctx, spec.key)
    out = task_run_view(ctx, spec.key)

    if out["skipped"]:
        log.info("%s / %s skipped: %s", question_id, spec.key, out["reason"])
    else:
        files = out["files"]
        log.info(
            "%s / %s → %s",
            question_id,
            spec.key,
            files.get("png") or files.get("md") or ctx.artifacts_dir,
        )
    return flow_result(out)
