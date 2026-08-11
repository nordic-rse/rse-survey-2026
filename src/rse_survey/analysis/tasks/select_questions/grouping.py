"""How a select-question view is sliced, and what rows it covers.

Three groupings share one code path: ``focus`` (the report's own country),
``by_age`` and ``between_countries``. A ``GroupingSpec`` is the only thing
that differs between them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

import pandas as pd

from rse_survey.analysis.context import AnalysisContext
from rse_survey.config.book_config import BookConfig

SELECT_KINDS = frozenset({"categorical", "likert", "categorical_with_other"})
# free_text is handled when HF ``token_labels.csv`` is present (coded categories).

GroupingKey = Literal["focus", "by_age", "between_countries"]
FrameScope = Literal["focus", "compare"]


@dataclass(frozen=True)
class GroupingSpec:
    """How a select-question view is sliced."""

    key: GroupingKey
    stem: str
    group_col: str | None
    scope: FrameScope


GROUPING_SPECS: dict[GroupingKey, GroupingSpec] = {
    "focus": GroupingSpec("focus", "focus", None, "focus"),
    "by_age": GroupingSpec("by_age", "by_age", "age_group", "focus"),
    "between_countries": GroupingSpec(
        "between_countries", "between_countries", "country_group", "compare"
    ),
}


def resolve_grouping(grouping_variable: str | None = None) -> GroupingSpec:
    key = "focus" if not grouping_variable else grouping_variable
    if key not in GROUPING_SPECS:
        known = ", ".join(repr(k) for k in GROUPING_SPECS)
        raise KeyError(
            f"Unknown grouping_variable={grouping_variable!r}; expected one of: {known}"
        )
    return GROUPING_SPECS[key]  # type: ignore[index]


def filter_focus_country(df: pd.DataFrame, focus_countries: list[str]) -> pd.DataFrame:
    """Keep rows for the report focus country/countries."""
    if df.empty or "country" not in df.columns:
        return df.iloc[0:0].copy()
    return df.loc[df["country"].isin(focus_countries)].copy()


def analysis_frame(ctx: AnalysisContext, spec: GroupingSpec) -> pd.DataFrame:
    """Long frame for this grouping (focus countries or compare groups)."""
    if spec.scope == "focus":
        return filter_focus_country(ctx.focus_df, ctx.book.focus_countries)

    compare = ctx.compare_df
    if compare.empty or "country_group" not in compare.columns:
        return compare.iloc[0:0].copy()
    return compare.loc[compare["country_group"].notna()].copy()


def group_levels_for(book: BookConfig, spec: GroupingSpec) -> list[str] | None:
    if spec.group_col == "age_group":
        return list(book.age_groups.keys())
    if spec.group_col == "country_group":
        return list(book.compare_groups.keys())
    return None


def item_slug(name: str, index: int) -> str:
    """Filename-safe stem for a sub-item; statements can be long sentences."""
    slug = re.sub(r"[^\w]+", "_", str(name).strip().lower(), flags=re.UNICODE)
    slug = slug.strip("_")[:48].strip("_")
    return slug or f"item{index + 1}"


def question_items(
    df: pd.DataFrame,
    question_id: str,
    item_order: list[str] | None = None,
) -> list[str]:
    """Distinct sub-item labels present for a question, in display order.

    Returns ``[]`` for questions without an item dimension (single-item
    arrays, checkbox grids, plain categoricals), which keeps them on the
    existing single-table rendering path.
    """
    if df.empty or "item" not in df.columns or "question_id" not in df.columns:
        return []
    sub = df.loc[df["question_id"] == question_id, "item"]
    labels = sub.dropna().astype(str).str.strip()
    present = [lab for lab in dict.fromkeys(labels.tolist()) if lab]
    if len(present) < 2:
        return []
    if not item_order:
        return present
    wanted = [str(x) for x in item_order]
    seen = set(present)
    ordered = [lab for lab in wanted if lab in seen]
    ordered.extend(lab for lab in present if lab not in set(wanted))
    return ordered


def filter_item(df: pd.DataFrame, item: str) -> pd.DataFrame:
    if "item" not in df.columns:
        return df.iloc[0:0].copy()
    return df.loc[df["item"].astype(str).str.strip() == str(item)].copy()
