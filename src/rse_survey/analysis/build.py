"""Run the tasks a question configures, and write its artifact directory.

Pure functions — the Prefect flow in ``flows/build_artifacts.py`` calls these
once per question so each shows up as its own tracked task run.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from rse_survey.analysis.context import AnalysisContext
from rse_survey.analysis.registry import get_task
from rse_survey.artifacts.layout import question_artifact_dir, write_meta
from rse_survey.artifacts.tables import write_table_artifact

logger = logging.getLogger(__name__)

# validate_inputs runs once for the whole book, not per question.
BOOK_LEVEL_TASKS = frozenset({"validate_inputs"})


def write_question_meta(ctx: AnalysisContext) -> Path:
    """Record what was built for this question, next to its artifacts."""
    out_dir = question_artifact_dir(ctx.artifacts_dir, ctx.question.question_id)
    return write_meta(
        out_dir,
        {
            "question_id": ctx.question.question_id,
            "focus": ctx.book.focus_countries,
            "tasks": ctx.question.tasks,
            "response_kind": ctx.question.response_kind,
        },
    )


def write_token_allocation(ctx: AnalysisContext) -> Path | None:
    """Appendix table mapping each coded token to its category.

    Only for free-text / appendix questions that have been through
    ``rse-survey propose`` + ``apply``; silently skipped otherwise.
    """
    q = ctx.question
    if not q.appendix and q.response_kind != "free_text":
        return None

    from rse_survey.coding.token_labels import (
        active_token_labels,
        read_token_labels_csv,
    )

    qid = q.question_id
    try:
        df = read_token_labels_csv(qid, include_excluded=True)
    except FileNotFoundError:
        return None
    except Exception as exc:  # noqa: BLE001 — a bad freeze must not fail the build
        logger.warning("skip token_allocation for %s: %s", qid, exc)
        return None

    active = active_token_labels(df)
    if active.empty or not {"token", "category"} <= set(active.columns):
        return None

    out = (
        active[["token", "category"]]
        .drop_duplicates()
        .sort_values(["category", "token"], kind="mergesort")
    )
    files = write_table_artifact(
        question_artifact_dir(ctx.artifacts_dir, qid),
        "token_allocation",
        out,
        heading=f"Token → category ({qid})",
    )
    return files["md"]


def run_question_task(ctx: AnalysisContext, task_name: str) -> dict[str, Any]:
    """Run one registered task against a question; never raises on skip."""
    result = get_task(task_name).run(ctx)
    if result.skipped:
        logger.info(
            "skip %s/%s: %s", ctx.question.question_id, task_name, result.skip_reason
        )
    return {
        "question_id": ctx.question.question_id,
        "task": task_name,
        "skipped": result.skipped,
        "skip_reason": result.skip_reason,
        "files": {k: str(v) for k, v in result.files.items()},
    }


def build_question_artifacts(ctx: AnalysisContext) -> list[dict[str, Any]]:
    """Meta + every configured task + token allocation, for one question."""
    write_question_meta(ctx)
    results = [
        run_question_task(ctx, name)
        for name in ctx.question.tasks
        if name not in BOOK_LEVEL_TASKS
    ]
    write_token_allocation(ctx)
    return results
