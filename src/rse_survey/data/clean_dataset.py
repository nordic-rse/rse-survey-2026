"""Write, read and slice the clean long-format dataset.

``build_clean_dataset`` is the whole raw → clean pipeline as one call; the
Prefect flow in ``flows/process_data.py`` runs the same steps as tracked tasks.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from rse_survey.config.book_config import BookConfig
from rse_survey.config.coding_config import load_free_text_coding
from rse_survey.config.paths import (
    CLEAN_LONG_NAME,
    CLEAN_META_NAME,
    REPO_ROOT,
    clean_long_path,
    processed_dir_for,
)
from rse_survey.data.columns import interest_question_ids, select_interest_columns
from rse_survey.data.filters import add_group_columns, filter_countries, filter_years
from rse_survey.data.readers import load_raw
from rse_survey.data.reshape import book_item_conditions, book_item_questions, to_long


def save_clean_long(
    df: pd.DataFrame,
    out_dir: Path,
    *,
    meta_extra: dict[str, Any] | None = None,
) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / CLEAN_LONG_NAME
    df.to_csv(path, index=False)
    meta = {
        "written_at": datetime.now(UTC).isoformat(),
        "n_rows": int(len(df)),
        "n_respondents": int(df["row_id"].nunique()) if len(df) else 0,
        "countries": sorted(df["country"].dropna().astype(str).unique().tolist())
        if len(df)
        else [],
        "years": sorted(
            {int(y) if str(y).isdigit() else y for y in df["year"].dropna().tolist()},
            key=str,
        )
        if len(df)
        else [],
        "question_ids": sorted(df["question_id"].dropna().astype(str).unique().tolist())
        if len(df)
        else [],
    }
    if meta_extra:
        meta.update(meta_extra)
    (out_dir / CLEAN_META_NAME).write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )
    return path


def build_clean_dataset(
    book: BookConfig,
    *,
    coding_path: str | Path | None = None,
    out_dir: Path | None = None,
    repo_root: Path | None = None,
) -> Path:
    """Run the full raw → clean long pipeline and write outputs."""
    root = repo_root or REPO_ROOT
    coding = load_free_text_coding(coding_path, repo_root=root)
    qids = interest_question_ids(book, coding)

    tf, all_cols = load_raw(book)
    tf = select_interest_columns(tf, book, qids)
    tf = filter_countries(tf, book)
    tf = filter_years(tf, book)
    tf = add_group_columns(tf, book)
    long_df = to_long(
        tf,
        all_cols,
        qids,
        country_column=book.country_column,
        year_column=book.year_column,
        item_conditions=book_item_conditions(book),
        item_questions=book_item_questions(book),
    )
    dest = Path(out_dir) if out_dir else processed_dir_for(book, repo_root=root)
    return save_clean_long(
        long_df,
        dest,
        meta_extra={
            "focus_countries": list(book.focus_countries),
            "compare_groups": {k: list(v) for k, v in book.compare_groups.items()},
            "waves": book.waves,
        },
    )


def load_clean_long(
    book: BookConfig,
    *,
    repo_root: Path | None = None,
) -> pd.DataFrame:
    path = clean_long_path(book, repo_root=repo_root)
    if not path.exists():
        raise FileNotFoundError(
            f"Missing clean dataset {path}. Run `rse-survey process-data` first."
        )
    df = pd.read_csv(path, low_memory=False)
    # Restore configured categorical order when possible
    if "age_group" in df.columns and book.age_groups:
        df["age_group"] = pd.Categorical(
            df["age_group"],
            categories=list(book.age_groups.keys()),
            ordered=True,
        )
    if "country_group" in df.columns and book.compare_groups:
        df["country_group"] = pd.Categorical(
            df["country_group"],
            categories=list(book.compare_groups.keys()),
            ordered=True,
        )
    return df


def focus_long(clean_df: pd.DataFrame, book: BookConfig) -> pd.DataFrame:
    return clean_df.loc[clean_df["country"].isin(book.focus_countries)].copy()


def compare_long(clean_df: pd.DataFrame, book: BookConfig) -> pd.DataFrame:
    return clean_df.loc[clean_df["country_group"].notna()].copy()


def load_focus_frame(book: BookConfig) -> pd.DataFrame:
    """Focus slice of the clean long-format dataset."""
    return focus_long(load_clean_long(book), book)


def load_compare_frame(book: BookConfig) -> pd.DataFrame:
    """Compare-group slice of the clean long-format dataset."""
    return compare_long(load_clean_long(book), book)
