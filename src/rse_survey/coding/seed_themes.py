"""Keyword-seeded themes: pin known categories before clustering the rest.

Lets a codebook fix the categories it already knows (regex per theme) so the
unsupervised step only has to explain what is left over.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd


def apply_seed_themes(
    tokens: pd.DataFrame,
    seed_themes: dict[str, list[str]],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[int, str]]:
    """Pre-assign tokens matching keyword patterns to fixed codebook themes.

    ``seed_themes`` maps English category name → list of regex patterns.
    First matching theme wins. Returns
    ``(seeded_assignments, residual_tokens, seed_labels)``.
    """
    if not seed_themes:
        return (
            tokens.iloc[0:0].assign(cluster_id=pd.Series(dtype=int)),
            tokens,
            {},
        )

    theme_names = list(seed_themes.keys())
    compiled: list[tuple[str, list[re.Pattern[str]]]] = []
    for name, pats in seed_themes.items():
        if not pats:
            raise ValueError(f"seed_themes[{name!r}] needs at least one pattern")
        compiled.append((name, [re.compile(str(p)) for p in pats]))

    seed_ids = {name: i for i, name in enumerate(theme_names)}
    seed_labels = {i: name for name, i in seed_ids.items()}

    assigned_rows: list[dict[str, Any]] = []
    residual_mask = []
    for _, row in tokens.iterrows():
        text = str(row["raw"])
        hit: str | None = None
        for name, cres in compiled:
            if any(cre.search(text) for cre in cres):
                hit = name
                break
        if hit is None:
            residual_mask.append(True)
        else:
            residual_mask.append(False)
            assigned_rows.append(
                {
                    "raw": row["raw"],
                    "n": row["n"] if "n" in row else 1,
                    "cluster_id": seed_ids[hit],
                }
            )

    residual = tokens.loc[residual_mask].reset_index(drop=True)
    seeded = pd.DataFrame(assigned_rows)
    if len(seeded):
        counts = (
            seeded.groupby("cluster_id", as_index=False)["n"].sum()
            if "n" in seeded.columns
            else seeded.groupby("cluster_id").size().rename("n").reset_index()
        )
        for _, r in counts.iterrows():
            cid = int(r["cluster_id"])
            print(
                f"Seed theme {seed_labels[cid]!r}: "
                f"{int((seeded.cluster_id == cid).sum())} token(s), weight={int(r['n'])}"
            )
    print(
        f"Seed themes claimed {len(seeded)} token(s); "
        f"{len(residual)} residual for clustering"
    )
    return seeded, residual, seed_labels


def parse_seed_themes(cfg: dict) -> dict[str, list[str]]:
    raw = cfg.get("seed_themes")
    if raw is None:
        return {}
    if not isinstance(raw, dict) or not raw:
        raise ValueError("seed_themes must be a non-empty mapping of name → patterns")
    out: dict[str, list[str]] = {}
    for name, pats in raw.items():
        if isinstance(pats, str):
            pats = [pats]
        if not isinstance(pats, list) or not pats:
            raise ValueError(f"seed_themes[{name!r}] must be a list of regexes")
        out[str(name)] = [str(p) for p in pats]
    return out
