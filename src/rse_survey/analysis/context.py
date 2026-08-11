"""What an analysis task is handed, and what it hands back."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from rse_survey.config.book_config import BookConfig, QuestionConfig
from rse_survey.config.paths import REPO_ROOT, artifacts_root, hf_cache_root


@dataclass
class TaskResult:
    task_name: str
    question_id: str
    files: dict[str, Path] = field(default_factory=dict)
    skipped: bool = False
    skip_reason: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisContext:
    book: BookConfig
    question: QuestionConfig
    focus_df: pd.DataFrame
    compare_df: pd.DataFrame
    artifacts_dir: Path
    hf_cache_dir: Path
    repo_root: Path


def load_frames(
    book: BookConfig, *, repo_root: Path | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """``(focus_df, compare_df)`` from the clean long table.

    Load once per run and reuse across questions — the CSV is the slow part.
    """
    from rse_survey.data.clean_dataset import compare_long, focus_long, load_clean_long

    clean_df = load_clean_long(book, repo_root=repo_root)
    return focus_long(clean_df, book), compare_long(clean_df, book)


def build_context(
    book: BookConfig,
    question_id: str,
    focus_df: pd.DataFrame,
    compare_df: pd.DataFrame,
    *,
    repo_root: Path | None = None,
) -> AnalysisContext:
    """Assemble the context for one question against pre-loaded frames."""
    if question_id not in book.questions:
        raise KeyError(f"Unknown question id {question_id!r}")
    root = repo_root or REPO_ROOT
    return AnalysisContext(
        book=book,
        question=book.questions[question_id],
        focus_df=focus_df,
        compare_df=compare_df,
        artifacts_dir=artifacts_root(root),
        hf_cache_dir=hf_cache_root(root),
        repo_root=root,
    )
