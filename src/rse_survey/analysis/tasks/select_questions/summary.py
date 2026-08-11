"""Long answer rows → the count/percentage table a view renders."""

from __future__ import annotations

import pandas as pd

from rse_survey.analysis.summarize.categorical import (
    apply_category_order,
    summarize_by_group,
    summarize_categorical_focus,
)
from rse_survey.analysis.tasks.select_questions.grouping import resolve_grouping


def build_summary_table(
    df: pd.DataFrame,
    question_id: str,
    *,
    grouping_variable: str | None = None,
    group_levels: list[str] | None = None,
    category_order: list[str] | None = None,
) -> pd.DataFrame:
    """Count/frequency table; optional facet via ``grouping_variable``."""
    spec = resolve_grouping(grouping_variable)
    if spec.group_col is None:
        summary = summarize_categorical_focus(df, question_id)
        return apply_category_order(summary, category_order)

    empty = pd.DataFrame(columns=[spec.group_col, "category", "n", "pct", "N"])
    empty.attrs["N"] = 0
    if spec.group_col not in df.columns:
        return empty

    framed = df.loc[df[spec.group_col].notna()].copy()
    if framed.empty:
        return empty

    summary = summarize_by_group(
        framed,
        question_id,
        spec.group_col,
        group_levels=group_levels,
    )
    return apply_category_order(summary, category_order, group_col=spec.group_col)


def total_respondents(summary: pd.DataFrame, group_col: str | None) -> int:
    n_total = int(summary.attrs.get("N") or 0)
    if n_total:
        return n_total
    if group_col and group_col in summary.columns and "N" in summary.columns:
        return int(summary.drop_duplicates(group_col)["N"].sum())
    if "n" in summary.columns and len(summary):
        return int(summary["n"].sum())
    return 0
