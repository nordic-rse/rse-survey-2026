"""Repository paths and derived output locations.

Every hard-coded location the pipeline reads or writes lives here, so a
contributor moving an output directory changes one file.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rse_survey.config.book_config import BookConfig

REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_PROCESSED_DIR = "rse-book/_data"
CLEAN_LONG_NAME = "clean_long.csv"
CLEAN_META_NAME = "meta.json"


def resolve_repo_path(path: str | Path, repo_root: Path | None = None) -> Path:
    root = repo_root or REPO_ROOT
    p = Path(path)
    if p.is_absolute():
        return p
    return (root / p).resolve()


def artifacts_root(repo_root: Path | None = None) -> Path:
    """Per-question artifact tree consumed by the Quarto book."""
    return (repo_root or REPO_ROOT) / "rse-book" / "_artifacts"


def hf_cache_root(repo_root: Path | None = None) -> Path:
    """Root of the free-text coding freezes."""
    return (repo_root or REPO_ROOT) / "rse-book" / "_hf_freetext_cache"


def question_cache_dir(question_id: str, repo_root: Path | None = None) -> Path:
    """Free-text coding freeze directory for one question."""
    return hf_cache_root(repo_root) / question_id


def processed_dir_for(book: BookConfig, *, repo_root: Path | None = None) -> Path:
    root = repo_root or REPO_ROOT
    rel = book.processed_dir or DEFAULT_PROCESSED_DIR
    return resolve_repo_path(rel, root)


def clean_long_path(book: BookConfig, *, repo_root: Path | None = None) -> Path:
    return processed_dir_for(book, repo_root=repo_root) / CLEAN_LONG_NAME
