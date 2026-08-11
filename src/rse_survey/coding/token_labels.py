"""``token_labels.csv`` — the human-editable source of truth for coding.

Written by ``propose``/``apply``, then edited by hand: ``category_human``
reallocates a token, ``exclude=1`` drops it. Everything downstream (book
artifacts, appendix) reads this file, never the LLM draft.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from rse_survey.config.paths import question_cache_dir

TOKEN_LABELS_FILENAME = "token_labels.csv"
TOKEN_LABELS_COLUMNS = [
    "token",
    "category_llm",
    "category_human",
    "cluster_id",
    "n",
    "exclude",
]


def token_labels_path(question_id: str) -> Path:
    return question_cache_dir(question_id) / TOKEN_LABELS_FILENAME


def categorized_to_token_labels(categorized: pd.DataFrame) -> pd.DataFrame:
    """Human-editable token table: LLM category + human-editable copy."""
    df = categorized.rename(columns={"raw": "token"}).copy()
    # Guard against duplicate column names (legacy migrations)
    df = df.loc[:, ~df.columns.duplicated()].copy()
    if "n" not in df.columns:
        df["n"] = 1
    if "exclude" not in df.columns:
        df["exclude"] = 0
    if "category_llm" not in df.columns:
        if "category" not in df.columns:
            raise ValueError("categorized frame needs 'category' or 'category_llm'")
        cat = df["category"]
        if isinstance(cat, pd.DataFrame):
            cat = cat.iloc[:, 0]
        df["category_llm"] = cat
    if "category_human" not in df.columns:
        df["category_human"] = df["category_llm"]
    out = df[TOKEN_LABELS_COLUMNS].copy()
    out["category_llm"] = out["category_llm"].astype(str).str.strip()
    out["category_human"] = out["category_human"].astype(str).str.strip()
    out["cluster_id"] = out["cluster_id"].astype(int)
    out["n"] = out["n"].astype(int)
    out["exclude"] = _normalize_exclude_series(out["exclude"])
    return out.sort_values(
        ["exclude", "category_human", "token"], kind="mergesort"
    ).reset_index(drop=True)


def _normalize_exclude_series(values: pd.Series) -> pd.Series:
    """Coerce exclude flags to 0/1 (anything truthy / '1' → 1)."""
    s = values.fillna(0).astype(str).str.strip().str.lower()
    excluded = s.isin({"1", "1.0", "true", "yes", "y", "t"})
    numeric = pd.to_numeric(values, errors="coerce").fillna(0).ne(0)
    return (excluded | numeric).astype(int)


def _normalize_prev_token_labels(prev: pd.DataFrame) -> pd.DataFrame:
    """Normalize an on-disk token_labels table (incl. legacy ``category``)."""
    df = prev.copy()
    if "token" not in df.columns and "raw" in df.columns:
        df = df.rename(columns={"raw": "token"})
    df["token"] = df["token"].astype(str).str.strip()
    if "category_llm" not in df.columns and "category" in df.columns:
        df["category_llm"] = df["category"]
    if "category_human" not in df.columns:
        if "category" in df.columns:
            df["category_human"] = df["category"]
        elif "category_llm" in df.columns:
            df["category_human"] = df["category_llm"]
        else:
            df["category_human"] = ""
    if "exclude" not in df.columns:
        df["exclude"] = 0
    df["category_llm"] = df["category_llm"].astype(str).str.strip()
    df["category_human"] = df["category_human"].astype(str).str.strip()
    df["exclude"] = _normalize_exclude_series(df["exclude"])
    return df


def active_token_labels(token_labels: pd.DataFrame) -> pd.DataFrame:
    """Tokens included in analysis (exclude != 1); uses ``category_human``."""
    df = _normalize_prev_token_labels(token_labels)
    active = df.loc[df["exclude"].eq(0)].copy()
    active["category"] = active["category_human"]
    return active


def write_token_labels_csv(
    question_id: str,
    categorized: pd.DataFrame,
    *,
    preserve_human_edits: bool = True,
) -> Path:
    """Write ``token_labels.csv``.

    When an existing file is present, preserves:
    - ``exclude=1`` flags
    - ``category_human`` values that already differed from the previous
      ``category_llm`` (manual reallocations)
    """
    path = token_labels_path(question_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    table = categorized_to_token_labels(categorized)

    if preserve_human_edits and path.exists():
        prev = _normalize_prev_token_labels(pd.read_csv(path))
        prev_map = prev.drop_duplicates("token").set_index("token")[
            ["category_llm", "category_human", "exclude"]
        ]
        humans: list[str] = []
        excludes: list[int] = []
        for tok, llm in zip(table["token"], table["category_llm"], strict=True):
            llm_s = str(llm).strip()
            if tok in prev_map.index:
                row = prev_map.loc[tok]
                prev_h = str(row["category_human"]).strip()
                prev_l = str(row["category_llm"]).strip()
                excl = int(row["exclude"])
                # Keep human label if it was a real edit; else follow new LLM label
                humans.append(prev_h if prev_h and prev_h != prev_l else llm_s)
                excludes.append(excl)
            else:
                humans.append(llm_s)
                excludes.append(0)
        table["category_human"] = humans
        table["exclude"] = _normalize_exclude_series(pd.Series(excludes))
        table = table[TOKEN_LABELS_COLUMNS]
        table = table.sort_values(
            ["exclude", "category_human", "token"], kind="mergesort"
        ).reset_index(drop=True)

    table.to_csv(path, index=False)
    n_excl = int(table["exclude"].sum())
    n_edited = int(
        (table["category_human"].astype(str) != table["category_llm"].astype(str)).sum()
    )
    print(
        f"Wrote editable token labels ({len(table)} tokens"
        + (f", {n_edited} human-edited" if n_edited else "")
        + (f", {n_excl} exclude=1" if n_excl else "")
        + f") to {path}"
    )
    return path


def read_token_labels_csv(
    question_id: str, *, include_excluded: bool = True
) -> pd.DataFrame:
    """Load ``token_labels.csv`` (``category_human`` is the analysis label).

    Set ``include_excluded=False`` to drop rows with ``exclude=1``.
    """
    path = token_labels_path(question_id)
    legacy = question_cache_dir(question_id) / "token_categories.csv"
    if not path.exists() and legacy.exists():
        old = pd.read_csv(legacy)
        if "token" not in old.columns and "raw" in old.columns:
            old = old.rename(columns={"raw": "token"})
        if "n" not in old.columns:
            assign = question_cache_dir(question_id) / "cluster_assignments.csv"
            if assign.exists() and "token" in old.columns:
                counts = pd.read_csv(assign).rename(columns={"raw": "token"})
                if "n" in counts.columns:
                    old = old.merge(
                        counts[["token", "n"]].drop_duplicates("token"),
                        on="token",
                        how="left",
                    )
            if "n" not in old.columns:
                old["n"] = 1
            else:
                old["n"] = pd.to_numeric(old["n"], errors="coerce").fillna(1)
        if "cluster_id" not in old.columns:
            old["cluster_id"] = -1
        if "category" not in old.columns and "category_llm" in old.columns:
            old["category"] = old["category_llm"]
        if "category" not in old.columns:
            raise ValueError(
                f"Legacy {legacy} needs a 'category' (or 'category_llm') column"
            )
        old["exclude"] = 0
        # Pass a clean categorized frame (avoid renaming category_llm → category
        # while 'category' already exists — that duplicates the column).
        write_token_labels_csv(
            question_id,
            old[["token", "cluster_id", "category", "n", "exclude"]].rename(
                columns={"token": "raw"}
            ),
            preserve_human_edits=False,
        )
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run `rse-survey propose --question {question_id}` first."
        )
    raw_header = set(pd.read_csv(path, nrows=0).columns)
    df = _normalize_prev_token_labels(pd.read_csv(path))
    if "n" not in df.columns:
        df["n"] = 1
    if "cluster_id" not in df.columns:
        df["cluster_id"] = -1
    df["n"] = pd.to_numeric(df["n"], errors="coerce").fillna(1).astype(int)
    df["cluster_id"] = (
        pd.to_numeric(df["cluster_id"], errors="coerce").fillna(-1).astype(int)
    )
    df = df.loc[
        df["token"].ne("") & df["category_llm"].ne("") & df["category_human"].ne("")
    ].copy()
    df = df[TOKEN_LABELS_COLUMNS]
    if df.empty:
        raise ValueError(f"No labeled tokens in {path}")
    # Upgrade legacy single-category files in place
    if raw_header != set(TOKEN_LABELS_COLUMNS):
        df.to_csv(path, index=False)
    if not include_excluded:
        df = active_token_labels(df)
        if df.empty:
            raise ValueError(
                f"All tokens in {path} are marked exclude=1; nothing left for analysis"
            )
    return df


def write_category_summary_from_labels(
    question_id: str, token_labels: pd.DataFrame
) -> Path:
    out_dir = question_cache_dir(question_id)
    active = active_token_labels(token_labels)
    summary = (
        active.groupby("category_human", as_index=False)["n"]
        .sum()
        .rename(columns={"category_human": "category"})
        .sort_values("n", ascending=False)
    )
    path = out_dir / "category_summary.csv"
    summary.to_csv(path, index=False)
    return path


def print_tokens_per_cluster(
    assignments: pd.DataFrame,
    *,
    n: int = 10,
    labels: dict[int, str] | None = None,
) -> None:
    """Print up to ``n`` most frequent tokens per cluster for human label review."""
    if n <= 0:
        return
    df = assignments.copy()
    if "n" not in df.columns:
        df["n"] = 1
    print(f"\nToken samples (top {n} per cluster):")
    for c in sorted(int(x) for x in df["cluster_id"].dropna().unique()):
        subset = df.loc[df["cluster_id"] == c].sort_values("n", ascending=False)
        label = labels.get(c) if labels else None
        label_note = f" → {label}" if label else ""
        total = int(subset["n"].sum())
        examples = subset["raw"].head(n).tolist()
        print(
            f"\n=== cluster {c}{label_note}  [weight={total}, {len(subset)} unique] ==="
        )
        print(", ".join(examples))
    print()


def write_assignments(question_id: str, assignments: pd.DataFrame, meta: dict) -> Path:
    out_dir = question_cache_dir(question_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    assignments[["raw", "cluster_id", "n"]].to_csv(
        out_dir / "cluster_assignments.csv", index=False
    )
    with (out_dir / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"Wrote cluster assignments to {out_dir}")
    return out_dir


def write_labeled_freezes(
    question_id: str,
    assignments: pd.DataFrame,
    categorized: pd.DataFrame,
    meta: dict,
) -> Path:
    """Write cluster freeze + editable ``token_labels.csv`` (follow-up source of truth)."""
    out_dir = write_assignments(question_id, assignments, meta)
    labels_path = write_token_labels_csv(question_id, categorized)
    token_labels = read_token_labels_csv(question_id, include_excluded=True)
    write_category_summary_from_labels(question_id, token_labels)
    # Keep legacy filename in sync for older readers (active tokens only)
    active = active_token_labels(token_labels)
    legacy = active.rename(columns={"token": "raw"})
    legacy[["raw", "cluster_id", "category"]].to_csv(
        out_dir / "token_categories.csv", index=False
    )
    print(f"Wrote labeled freezes to {out_dir} (canonical: {labels_path.name})")
    return out_dir
