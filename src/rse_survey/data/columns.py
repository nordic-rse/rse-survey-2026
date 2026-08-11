"""Map configured question ids onto raw wide-format column names."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from rse_survey.config.book_config import BookConfig

QUESTION_ALIASES: dict[str, list[str]] = {
    # A configured question id can be spread over several raw column stems
    # (paired actual/desired arrays, or per-country variants of one question).
    # Every stem that resolves contributes its columns.
    "likert01": ["likert0", "likert1"],
    "tool4": ["tool4can", "tool4"],
    "tool5": ["tool5", "tool5can"],
}


def _stem_columns(code: str, columns: list[str]) -> list[str]:
    """Columns belonging to a single raw stem, most specific match first."""
    exact = [c for c in columns if c == code or c == f"{code}_0"]
    if exact:
        return exact
    pattern = re.compile(rf"^{re.escape(code)}\[.+\](?:_0)?$")
    matched = [c for c in columns if pattern.match(c)]
    if matched:
        return matched
    return [c for c in columns if c == code or c.startswith(code + "[")]


def question_columns(question_code: str, columns: list[str]) -> list[str]:
    """Match single-response `code` or multi-response `code[...]` stems.

    Aliased questions accumulate columns from *all* their stems rather than
    stopping at the first that matches, so paired arrays (``likert0`` +
    ``likert1``) and per-country variants (``tool5`` + ``tool5can``) are not
    silently truncated to whichever stem happens to resolve first.
    """
    candidates = [question_code]
    candidates.extend(QUESTION_ALIASES.get(question_code, []))

    out: list[str] = []
    seen: set[str] = set()
    for code in candidates:
        for col in _stem_columns(code, columns):
            if col not in seen:
                seen.add(col)
                out.append(col)
        # Un-aliased questions keep the original first-match-wins behaviour.
        if out and question_code not in QUESTION_ALIASES:
            break
    return out


def coding_question_ids(coding: dict[str, Any] | None) -> list[str]:
    if not coding:
        return []
    return [str(k) for k in coding.keys() if not str(k).startswith("_")]


def interest_question_ids(
    book: BookConfig,
    coding: dict[str, Any] | None = None,
) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for qid in list(book.question_ids) + coding_question_ids(coding):
        if qid not in seen:
            seen.add(qid)
            ids.append(qid)
    return ids


def select_interest_columns(
    tf: pd.DataFrame,
    book: BookConfig,
    question_ids: list[str],
) -> pd.DataFrame:
    """Keep demography columns plus all matched question columns."""
    demo = [
        "row_id",
        book.submit_column,
        book.country_column,
        book.age_column,
        book.year_column,
    ]
    keep: list[str] = []
    for col in demo:
        if col in tf.columns and col not in keep:
            keep.append(col)
    for qid in question_ids:
        for col in question_columns(qid, list(tf.columns)):
            if col not in keep:
                keep.append(col)
    missing_demo = [
        c for c in (book.country_column, book.submit_column) if c not in tf.columns
    ]
    if missing_demo:
        raise KeyError(f"Missing required columns: {missing_demo}")
    return tf.loc[:, keep].copy()
