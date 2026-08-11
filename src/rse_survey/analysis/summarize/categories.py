"""Remap answer values before they are counted.

Four independent transforms, applied by tasks in this order: aggregate raw
values into ``category_groups``, rename to display ``category_labels``, keep
only ``closed_categories``, or replace free text with its HF-coded category.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def _closed_set(closed_categories: list[str] | None) -> set[str]:
    return {str(c).strip() for c in (closed_categories or []) if str(c).strip()}


def filter_closed_answers(
    df: pd.DataFrame,
    question_id: str,
    closed_categories: list[str] | None,
) -> pd.DataFrame:
    """Keep rows for ``question_id`` whose value is in ``closed_categories``."""
    if df.empty or "question_id" not in df.columns or "value" not in df.columns:
        return df.iloc[0:0].copy()
    closed = _closed_set(closed_categories)
    if not closed:
        return df.iloc[0:0].copy()
    sub = df.loc[df["question_id"] == question_id].copy()
    if sub.empty:
        return sub
    values = sub["value"].astype(str).str.strip()
    keep = sub["value"].notna() & values.ne("") & values.str.lower().ne("nan")
    keep &= values.isin(closed)
    return sub.loc[keep].copy()


def token_labels_csv_path(hf_cache_dir: Path, question_id: str) -> Path:
    """Path to HF ``token_labels.csv`` for a question under the cache root."""
    return Path(hf_cache_dir) / question_id / "token_labels.csv"


def load_hf_token_category_map(labels_path: Path) -> dict[str, str]:
    """Map normalized token → ``category_human`` from an active labels file."""
    from rse_survey.coding.token_labels import active_token_labels

    if not labels_path.exists():
        return {}
    raw = pd.read_csv(labels_path)
    active = active_token_labels(raw)
    if active.empty or "token" not in active.columns:
        return {}
    tokens = active["token"].astype(str).str.lower().str.strip()
    cats = active["category"].astype(str).str.strip()
    # First label wins if a token appears more than once.
    return dict(zip(tokens, cats, strict=False))


def apply_hf_coded_categories(
    df: pd.DataFrame,
    question_id: str,
    *,
    labels_path: Path,
) -> pd.DataFrame:
    """Replace free-text answers with HF ``category_human`` labels.

    Tokenization matches the HF workflow (lowercase, split on commas). Tokens
    marked ``exclude=1`` or missing from the labels file are dropped. When one
    answer yields several tokens in the same category, keep one row per
    respondent × category.
    """
    if df.empty or "question_id" not in df.columns or "value" not in df.columns:
        return df.iloc[0:0].copy()
    token_map = load_hf_token_category_map(labels_path)
    if not token_map:
        return df.iloc[0:0].copy()

    sub = df.loc[df["question_id"] == question_id].copy()
    if sub.empty:
        return sub
    values = sub["value"].astype(str).str.strip()
    keep = sub["value"].notna() & values.ne("") & values.str.lower().ne("nan")
    sub = sub.loc[keep].copy()
    if sub.empty:
        return sub

    exploded = sub.assign(
        _token=sub["value"].astype(str).str.lower().str.split(",")
    ).explode("_token", ignore_index=False)
    exploded["_token"] = exploded["_token"].astype(str).str.strip()
    exploded = exploded.loc[exploded["_token"].ne("")].copy()
    exploded["value"] = exploded["_token"].map(token_map)
    exploded = exploded.loc[exploded["value"].notna()].copy()
    exploded = exploded.drop(columns=["_token"])
    if exploded.empty:
        return exploded

    dedupe_cols = [
        c
        for c in (
            "row_id",
            "question_id",
            "value",
            "country",
            "age_group",
            "country_group",
        )
        if c in exploded.columns
    ]
    if dedupe_cols:
        exploded = exploded.drop_duplicates(subset=dedupe_cols, keep="first")
    return exploded


def apply_category_labels(
    df: pd.DataFrame,
    question_id: str,
    category_labels: dict[str, str] | None,
) -> pd.DataFrame:
    """Replace answer ``value``s using ``category_labels`` (raw → display).

    Unmapped values are left unchanged. Matching is on stripped string equality.
    """
    if not category_labels or df.empty or "value" not in df.columns:
        return df
    mapping = {str(k).strip(): str(v) for k, v in category_labels.items()}
    if not mapping:
        return df
    out = df.copy()
    if "question_id" in out.columns:
        mask = out["question_id"].astype(str).eq(question_id)
    else:
        mask = pd.Series(True, index=out.index)
    if not mask.any():
        return out
    vals = out.loc[mask, "value"].astype(str).str.strip()
    out.loc[mask, "value"] = vals.map(lambda v: mapping.get(v, v))
    return out


def category_groups_to_mapping(
    category_groups: dict[str, list[str]] | None,
) -> dict[str, str] | None:
    """Flatten ``{group: [raw, …]}`` into ``{raw: group}``."""
    if not category_groups:
        return None
    mapping: dict[str, str] = {}
    for group_label, members in category_groups.items():
        for member in members:
            mapping[str(member).strip()] = str(group_label)
    return mapping or None


def apply_category_groups(
    df: pd.DataFrame,
    question_id: str,
    category_groups: dict[str, list[str]] | None,
) -> pd.DataFrame:
    """Aggregate raw answer values into group labels from ``category_groups``."""
    return apply_category_labels(
        df, question_id, category_groups_to_mapping(category_groups)
    )


def other_labels_by_country(
    df: pd.DataFrame,
    question_id: str,
    closed_categories: list[str] | None,
    *,
    country_col: str = "country_group",
) -> dict[str, list[str]]:
    """Unique Other (non-closed) labels per country; first-seen order, no counts."""
    if df.empty or "question_id" not in df.columns or "value" not in df.columns:
        return {}
    if country_col not in df.columns:
        return {}
    closed = _closed_set(closed_categories)
    sub = df.loc[df["question_id"] == question_id].copy()
    if sub.empty:
        return {}
    values = sub["value"].astype(str).str.strip()
    keep = sub["value"].notna() & values.ne("") & values.str.lower().ne("nan")
    keep &= ~values.isin(closed)
    sub = sub.loc[keep].copy()
    if sub.empty:
        return {}
    sub = sub.assign(_label=sub["value"].astype(str).str.strip())
    out: dict[str, list[str]] = {}
    for country, block in sub.groupby(country_col, sort=False):
        if pd.isna(country) or str(country).strip() == "":
            continue
        seen: set[str] = set()
        labels: list[str] = []
        for label in block["_label"].tolist():
            if label not in seen:
                seen.add(label)
                labels.append(label)
        if labels:
            out[str(country)] = labels
    return out
