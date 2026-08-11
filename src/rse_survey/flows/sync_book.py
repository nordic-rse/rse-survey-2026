"""Prefect flow: write Quarto chapters and republish artifacts into the book."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from prefect import flow, task

from rse_survey.book.sync import sync_quarto_book
from rse_survey.config.paths import resolve_repo_path
from rse_survey.logging_config import flow_result, get_logger

log = get_logger("sync_book")


@task(name="sync_quarto_book")
def task_sync_quarto_book(book_path: str) -> dict[str, Any]:
    return sync_quarto_book(book_path)


@flow(name="sync_quarto_book")
def sync_book_flow(
    book_config: str | Path = "config/book.yml",
) -> dict[str, Any] | None:
    out = task_sync_quarto_book(str(resolve_repo_path(book_config)))
    log.info(
        "synced %s chapters (removed %s orphans)",
        out.get("chapters_written"),
        len(out.get("chapters_removed") or []),
    )
    return flow_result(out)
