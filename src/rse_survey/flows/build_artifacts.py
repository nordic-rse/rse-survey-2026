"""Prefect flow: validate the book, then build every question's artifacts.

The single entry point for ``rse-survey build-artifacts``. Each question is one
tracked task run; the work itself lives in :mod:`rse_survey.analysis.build`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from prefect import flow, task

from rse_survey.analysis.build import build_question_artifacts
from rse_survey.analysis.context import build_context, load_frames
from rse_survey.analysis.registry import ensure_builtin_tasks_loaded
from rse_survey.config.book_config import BookConfig, load_book_config
from rse_survey.config.paths import REPO_ROOT, artifacts_root
from rse_survey.data.validation import validate_inputs
from rse_survey.logging_config import flow_result, get_logger

log = get_logger("build_artifacts")


@task(name="validate_inputs")
def task_validate_inputs(book: BookConfig) -> dict[str, Any]:
    result = validate_inputs(book, raise_on_error=True)
    return {"warnings": [w.message for w in result.warnings]}


@task(name="load_clean_long")
def task_load_frames(
    book: BookConfig, repo_root: Path
) -> tuple[pd.DataFrame, pd.DataFrame]:
    focus_df, compare_df = load_frames(book, repo_root=repo_root)
    log.info(
        "loaded %s focus row(s), %s compare row(s)", len(focus_df), len(compare_df)
    )
    return focus_df, compare_df


@task(name="build_question")
def task_build_question(
    book: BookConfig,
    question_id: str,
    focus_df: pd.DataFrame,
    compare_df: pd.DataFrame,
    repo_root: Path,
) -> list[dict[str, Any]]:
    ensure_builtin_tasks_loaded()
    ctx = build_context(book, question_id, focus_df, compare_df, repo_root=repo_root)
    return build_question_artifacts(ctx)


@flow(name="build_book_artifacts")
def build_artifacts_flow(
    book_config: str | Path | None = None,
    question_ids: list[str] | None = None,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any] | None:
    """Build per-question artifacts for the whole book, or a subset."""
    root = repo_root or REPO_ROOT
    book = load_book_config(book_config, repo_root=root)
    task_validate_inputs(book)

    artifacts_root(root).mkdir(parents=True, exist_ok=True)
    focus_df, compare_df = task_load_frames(book, root)

    results: list[dict[str, Any]] = []
    for qid in question_ids or book.question_ids:
        if qid not in book.questions:
            log.warning("Unknown question id %s — skipped", qid)
            continue
        results.extend(task_build_question(book, qid, focus_df, compare_df, root))

    log.info("built %s task runs", len(results))
    return flow_result({"n_task_runs": len(results), "results": results})
