"""Prefect flows: free-text coding propose / apply.

Thin wrappers — the coding itself lives in :mod:`rse_survey.coding.workflows`
so it stays runnable and testable without a Prefect runtime.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from prefect import flow, task

from rse_survey.coding.models import configure_hf_cache
from rse_survey.coding.token_labels import token_labels_path
from rse_survey.coding.workflows import run_apply_labels_only, run_propose_labels
from rse_survey.config.book_config import load_book_config
from rse_survey.config.coding_config import load_question_coding
from rse_survey.config.paths import question_cache_dir, resolve_repo_path
from rse_survey.logging_config import flow_result, get_logger

log = get_logger("code_free_text")


@task(name="hf-propose-labels")
def propose_labels_task(
    question_id: str,
    *,
    book_path: str,
    coding_path: str,
    overwrite_labels: bool = False,
    sample_tokens: int | None = None,
) -> dict[str, Any]:
    configure_hf_cache()
    book = load_book_config(book_path)
    cfg, path = load_question_coding(question_id, coding_path=coding_path)
    run_propose_labels(
        cfg,
        coding_path=path,
        book=book,
        sample_tokens=sample_tokens,
        overwrite_labels=overwrite_labels,
    )
    return {
        "question_id": question_id,
        "focus_countries": list(book.focus_countries),
        "coding_path": str(path),
        "cache_dir": str(question_cache_dir(question_id)),
        "token_labels": str(token_labels_path(question_id)),
    }


@task(name="hf-apply-labels")
def apply_labels_task(
    question_id: str,
    *,
    coding_path: str,
    sample_tokens: int | None = None,
    from_csv: bool = False,
) -> dict[str, Any]:
    cfg, path = load_question_coding(question_id, coding_path=coding_path)
    run_apply_labels_only(
        cfg,
        coding_path=path,
        sample_tokens=sample_tokens,
        from_csv=from_csv,
    )
    return {
        "question_id": question_id,
        "coding_path": str(path),
        "cache_dir": str(question_cache_dir(question_id)),
        "token_labels": str(token_labels_path(question_id)),
        "from_csv": from_csv,
    }


@flow(name="hf-freetext-propose")
def propose_flow(
    question_id: str,
    *,
    book_config: str | Path = "config/book.yml",
    coding_config: str | Path = "config/free_text_coding.yml",
    overwrite_labels: bool = False,
    sample_tokens: int | None = None,
) -> dict[str, Any] | None:
    out = propose_labels_task(
        question_id,
        book_path=str(resolve_repo_path(book_config)),
        coding_path=str(resolve_repo_path(coding_config)),
        overwrite_labels=overwrite_labels,
        sample_tokens=sample_tokens,
    )
    log.info("propose finished for %s", question_id)
    return flow_result(out)


@flow(name="hf-freetext-apply")
def apply_flow(
    question_id: str,
    *,
    coding_config: str | Path = "config/free_text_coding.yml",
    sample_tokens: int | None = None,
    from_csv: bool = False,
) -> dict[str, Any] | None:
    out = apply_labels_task(
        question_id,
        coding_path=str(resolve_repo_path(coding_config)),
        sample_tokens=sample_tokens,
        from_csv=from_csv,
    )
    log.info("apply finished for %s", question_id)
    return flow_result(out)
