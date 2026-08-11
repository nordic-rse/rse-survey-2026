"""Free-text answers → weighted token table.

Normalizes answers the same way for every question (lowercase, split on
commas, strip) and drops non-informative tokens before anything is embedded.
"""

from __future__ import annotations

import re

import pandas as pd

from rse_survey.config.book_config import BookConfig
from rse_survey.data.clean_dataset import load_focus_frame


def tokenize_series(series: pd.Series) -> pd.DataFrame:
    """Normalize free text like prepare_text_tokens(): lower, split commas, strip."""
    s = series.dropna().astype(str).str.lower().str.split(",").explode().str.strip()
    s = s[s != ""]
    counts = s.value_counts().rename_axis("raw").reset_index(name="n")
    return counts


# Default non-response / nonsense tokens dropped before embedding (casefolded).
_DEFAULT_EXCLUDE_EXACT = frozenset(
    {
        "none",
        "n/a",
        "na",
        "n.a.",
        "nil",
        "nothing",
        "no",
        "-",
        "—",
        "--",
        ".",
        "?",
        "etc",
        "etc.",
        "idk",
        "i don't know",
        "i dont know",
        "don't know",
        "dont know",
        "no idea",
        "not sure",
        "unknown",
        "no comment",
        "no opinion",
        "skip",
        "same",
        "see above",
    }
)

_DEFAULT_EXCLUDE_PATTERNS = (
    r"(?i)^n/?a\.?$",
    r"(?i)^nothing\b",
    r"(?i)brain\s*rot",
    r"(?i)^i\s+have\s+no\s+idea",
    r"(?i)^no\s+idea\b",
    r"(?i)^prefer not",
)


def filter_excluded_tokens(
    tokens: pd.DataFrame,
    *,
    exclude_exact: set[str] | None = None,
    exclude_patterns: list[str] | None = None,
    use_defaults: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Drop non-informative tokens. Returns ``(kept, excluded)``."""
    exact = set(_DEFAULT_EXCLUDE_EXACT) if use_defaults else set()
    if exclude_exact:
        exact |= {str(x).casefold().strip() for x in exclude_exact}
    patterns = list(_DEFAULT_EXCLUDE_PATTERNS) if use_defaults else []
    if exclude_patterns:
        patterns.extend(str(p) for p in exclude_patterns)

    compiled = [re.compile(p) for p in patterns]
    raw = tokens["raw"].astype(str)
    fold = raw.str.casefold().str.strip()
    mask = fold.isin(exact)
    for cre in compiled:
        mask = mask | raw.str.contains(cre, na=False, regex=True)

    excluded = tokens.loc[mask].copy()
    kept = tokens.loc[~mask].copy()
    if len(excluded):
        w = int(excluded["n"].sum()) if "n" in excluded.columns else len(excluded)
        print(
            f"Excluded {len(excluded)} non-informative token(s) "
            f"(weight={w}): "
            + ", ".join(
                excluded.sort_values("n", ascending=False)["raw"].head(12).astype(str)
            )
            + ("…" if len(excluded) > 12 else "")
        )
    return kept.reset_index(drop=True), excluded.reset_index(drop=True)


def load_focus_text_series(cfg: dict, book: BookConfig) -> pd.Series:
    """Return free-text answers from the focus slice of the clean long table.

    Reads ``rse-book/_data/clean_long.csv`` (run ``rse-survey process-data``
    first). Uses ``text_column`` / ``question_id`` to select answer rows.
    """
    focus = load_focus_frame(book)
    n_focus = int(focus["row_id"].nunique()) if len(focus) else 0
    countries = list(book.focus_countries)
    print(
        f"Focus filter first: countries={countries} → {n_focus} submitted respondent(s)"
    )
    if n_focus == 0:
        raise ValueError(
            f"No submitted respondents for focus countries {countries} "
            f"in clean long table (run `rse-survey process-data`)"
        )

    qid = str(cfg.get("text_column") or cfg["question_id"])
    # Prefer exact question_id match; also accept text_column as question stem
    candidates = [qid]
    if cfg.get("question_id") and str(cfg["question_id"]) not in candidates:
        candidates.append(str(cfg["question_id"]))
    sub = focus.loc[focus["question_id"].isin(candidates)].copy()
    if sub.empty:
        raise KeyError(
            f"No clean-long answers for free-text {qid!r}; "
            f"checked question_id={cfg.get('question_id')!r}"
        )
    series = sub["value"]
    n_non_null = int(series.notna().sum())
    print(
        f"Text from clean long question_id={candidates} ({n_non_null} non-null cell(s))"
    )
    return series


def load_tokens(cfg: dict, *, book: BookConfig) -> pd.DataFrame:
    series = load_focus_text_series(cfg, book)
    tokens = tokenize_series(series)
    use_defaults = bool(cfg.get("exclude_defaults", True))
    exact = cfg.get("exclude_exact")
    patterns = cfg.get("exclude_patterns")
    if exact is not None and not isinstance(exact, list):
        raise ValueError("exclude_exact must be a list of strings")
    if patterns is not None and not isinstance(patterns, list):
        raise ValueError("exclude_patterns must be a list of regex strings")
    kept, _excluded = filter_excluded_tokens(
        tokens,
        exclude_exact=set(exact) if exact else None,
        exclude_patterns=patterns,
        use_defaults=use_defaults,
    )
    if kept.empty:
        raise ValueError(
            f"No tokens left after focus filter + exclusions for "
            f"{cfg.get('question_id')!r} (focus={book.focus_countries})"
        )
    print(
        f"Tokens after focus filter + exclusions: "
        f"{len(kept)} unique (weight={int(kept['n'].sum())})"
    )
    return kept
