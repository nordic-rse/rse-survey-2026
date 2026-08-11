"""Categorical / free-text / likert summary helpers for view tasks."""

from __future__ import annotations

import pandas as pd

# True/False: always show both sides, including n=0.
_TRUE_FALSE = ("True", "False")


def _question_rows(df: pd.DataFrame, question_id: str) -> pd.DataFrame:
    if df.empty or "question_id" not in df.columns:
        return df.iloc[0:0].copy()
    return df.loc[df["question_id"] == question_id].copy()


def _nonempty_answer_mask(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    return series.notna() & s.ne("") & s.str.lower().ne("nan")


def is_true_false_categories(categories: list[str]) -> bool:
    """True if categories are exclusively True/False (case-insensitive).

    Mixed questions (True/False plus other labels) are not treated as
    binary: unused labels with ``n=0`` are dropped.
    """
    lowers = {
        str(c).strip().lower()
        for c in categories
        if c is not None and str(c).strip() and str(c).strip().lower() != "nan"
    }
    if not lowers:
        return False
    return lowers <= {"true", "false"}


def complete_true_false_levels(categories: list[str]) -> list[str]:
    """Return levels with both True and False when either is present."""
    levels: list[str] = []
    seen_lower: set[str] = set()
    for raw in categories:
        label = str(raw)
        key = label.lower()
        if key in seen_lower:
            continue
        seen_lower.add(key)
        levels.append(label)

    if not is_true_false_categories(levels):
        return levels

    lower_to_label = {c.lower(): c for c in levels}
    for label in _TRUE_FALSE:
        if label.lower() not in lower_to_label:
            levels.append(label)
            lower_to_label[label.lower()] = label
    return levels


def apply_category_order(
    summary: pd.DataFrame,
    category_order: list[str] | None,
    *,
    category_col: str = "category",
    pct_col: str = "pct",
    group_col: str | None = None,
) -> pd.DataFrame:
    """Order summary rows by ``category_order``, or by ``pct`` descending.

    When ``category_order`` is ``None``/empty, keep frequency order (highest
    ``pct`` first). Configured labels come first in the given order; any
    unexpected categories are appended (still by ``pct`` descending).
    """
    if summary.empty or category_col not in summary.columns:
        return summary

    def _order_block(block: pd.DataFrame) -> pd.DataFrame:
        out = block.copy()
        if not category_order:
            return out.sort_values(
                pct_col, ascending=False, kind="mergesort"
            ).reset_index(drop=True)
        order = [str(x) for x in category_order]
        rank = {c: i for i, c in enumerate(order)}
        labels = out[category_col].astype(str)
        out = out.assign(
            _ord=labels.map(lambda c: rank.get(c, len(order))),
            _pct=pd.to_numeric(out[pct_col], errors="coerce").fillna(0.0),
        )
        out = out.sort_values(
            ["_ord", "_pct"], ascending=[True, False], kind="mergesort"
        )
        return out.drop(columns=["_ord", "_pct"]).reset_index(drop=True)

    attrs = dict(summary.attrs)
    if group_col and group_col in summary.columns:
        parts = [_order_block(gdf) for _, gdf in summary.groupby(group_col, sort=False)]
        out = pd.concat(parts, ignore_index=True) if parts else summary.iloc[0:0]
    else:
        out = _order_block(summary)
    out.attrs.update(attrs)
    return out


def complete_category_levels(categories: list[str]) -> list[str]:
    """Back-compat alias for ``complete_true_false_levels``."""
    return complete_true_false_levels(categories)


def summarize_categorical_focus(
    df: pd.DataFrame,
    question_id: str,
    *,
    categories: list[str] | None = None,
    pad_true_false: bool | None = None,
) -> pd.DataFrame:
    """Summarize answer values for one question from a clean long table.

    ``n`` is the count per answer item. ``pct`` is percent of respondents who
    answered the question (``N`` unique ``row_id``s). For multi-select items,
    percents can sum to more than 100.

    Exclusive True/False answers always include both sides (``n=0`` when unused).
    All other categories with ``n=0`` are dropped. Mixed True/False + other
    labels never pad zeros; set ``pad_true_false`` when the caller knows the
    question-level answer set.
    """
    empty = pd.DataFrame(columns=["category", "n", "pct"])
    empty.attrs["N"] = 0
    sub = _question_rows(df, question_id)
    if sub.empty or "value" not in sub.columns:
        return empty

    keep = _nonempty_answer_mask(sub["value"])
    sub = sub.loc[keep].copy()
    if sub.empty:
        return empty

    if "row_id" in sub.columns:
        n_respondents = int(sub["row_id"].nunique())
    else:
        n_respondents = int(len(sub))

    counts = (
        sub["value"]
        .astype(str)
        .str.strip()
        .value_counts()
        .rename_axis("category")
        .reset_index(name="n")
    )
    counts["pct"] = (
        (100 * counts["n"] / n_respondents).round(1) if n_respondents else 0.0
    )

    observed = [str(c) for c in counts["category"].tolist()]
    if pad_true_false is None:
        hint = [str(c) for c in categories] if categories is not None else []
        pad_true_false = is_true_false_categories(observed + hint)

    # Exclusive True/False: complete both sides (optionally from ``categories``)
    if pad_true_false:
        levels = complete_true_false_levels(
            [str(c) for c in categories] if categories is not None else observed
        )
        by_cat = {str(r["category"]): r for _, r in counts.iterrows()}
        rows = []
        for cat in levels:
            if cat in by_cat:
                rows.append(
                    {
                        "category": cat,
                        "n": int(by_cat[cat]["n"]),
                        "pct": float(by_cat[cat]["pct"]),
                    }
                )
            else:
                rows.append({"category": cat, "n": 0, "pct": 0.0})
        out = pd.DataFrame(rows)
        out.attrs["N"] = n_respondents
        return out

    out = counts.loc[counts["n"].astype(int) > 0].copy()
    out.attrs["N"] = n_respondents
    return out


def summarize_by_group(
    df: pd.DataFrame,
    question_id: str,
    group_col: str,
    *,
    group_levels: list[str] | None = None,
) -> pd.DataFrame:
    """Summarize answers within each group.

    Each row includes ``N`` = unique respondents in that group who answered.
    ``attrs['N']`` is unique respondents across all groups.

    Exclusive True/False: both sides appear in every group (``n=0`` when unused).
    Other / mixed categories: only ``n>0`` rows are kept per group.
    """
    empty = pd.DataFrame(columns=[group_col, "category", "n", "pct", "N"])
    empty.attrs["N"] = 0
    sub = _question_rows(df, question_id)
    if sub.empty or group_col not in sub.columns:
        return empty

    answered = sub.loc[_nonempty_answer_mask(sub["value"])].copy()
    if answered.empty:
        return empty

    if "row_id" in answered.columns:
        overall_n = int(answered["row_id"].nunique())
    else:
        overall_n = int(len(answered))

    observed_cats = answered["value"].astype(str).str.strip().tolist()
    overall_is_tf = is_true_false_categories(observed_cats)
    tf_levels = complete_true_false_levels(observed_cats) if overall_is_tf else None

    if group_levels is not None:
        frame_groups = set(sub[group_col].dropna().astype(str))
        present_groups = [g for g in group_levels if str(g) in frame_groups]
    else:
        present_groups = list(dict.fromkeys(answered[group_col].astype(str).tolist()))

    parts = []
    for group_val in present_groups:
        group_df = sub.loc[sub[group_col].astype(str).eq(str(group_val))]
        tab = summarize_categorical_focus(
            group_df,
            question_id,
            categories=tf_levels,
            pad_true_false=overall_is_tf,
        )
        n_group = int(tab.attrs.get("N") or 0)
        if tab.empty and overall_is_tf and tf_levels is not None:
            tab = pd.DataFrame([{"category": c, "n": 0, "pct": 0.0} for c in tf_levels])
            tab.attrs["N"] = 0
            n_group = 0
        elif tab.empty:
            continue
        tab = tab.copy()
        tab.insert(0, group_col, group_val)
        tab["N"] = n_group
        parts.append(tab)

    if not parts:
        return empty
    out = pd.concat(parts, ignore_index=True)
    out.attrs["N"] = overall_n
    return out
