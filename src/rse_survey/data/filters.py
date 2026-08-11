"""Row filters and derived grouping columns (respondents, countries, years, age)."""

from __future__ import annotations

import logging

import pandas as pd

from rse_survey.config.book_config import BookConfig

logger = logging.getLogger(__name__)


def is_submitted_response(submitdate: pd.Series) -> pd.Series:
    s = submitdate.astype(str).str.strip()
    return submitdate.notna() & s.ne("") & s.str.lower().ne("nan")


def filter_survey_respondents(
    tf: pd.DataFrame,
    countries: list[str],
    *,
    country_column: str = "socio1_0",
    submit_column: str = "submitdate_0",
) -> pd.DataFrame:
    if country_column not in tf.columns:
        raise KeyError(f"Missing country column {country_column!r}")
    if submit_column not in tf.columns:
        raise KeyError(f"Missing submit column {submit_column!r}")
    mask = tf[country_column].isin(countries) & is_submitted_response(tf[submit_column])
    out = tf.loc[mask].copy()
    # Preserve survey row_id when present (needed to join free-text side tables).
    if "row_id" not in out.columns:
        out["row_id"] = range(1, len(out) + 1)
    cols = ["row_id"] + [c for c in out.columns if c != "row_id"]
    return out.loc[:, cols]


def assign_age_groups(
    df: pd.DataFrame,
    age_groups: dict[str, list[str]],
    *,
    age_column: str = "socio3_0",
    group_col: str = "age_group",
    drop_unmapped: bool = True,
) -> pd.DataFrame:
    label_to_group: dict[str, str] = {}
    for group_name, labels in age_groups.items():
        for lab in labels:
            label_to_group[str(lab)] = group_name
    out = df.copy()
    out[group_col] = out[age_column].map(label_to_group)
    if drop_unmapped:
        out = out.loc[out[group_col].notna()].copy()
    # preserve configured order
    levels = list(age_groups.keys())
    out[group_col] = pd.Categorical(out[group_col], categories=levels, ordered=True)
    return out


def target_countries(book: BookConfig) -> list[str]:
    countries = set(book.focus_countries)
    for vals in book.compare_groups.values():
        countries.update(vals)
    return sorted(countries)


def filter_countries(tf: pd.DataFrame, book: BookConfig) -> pd.DataFrame:
    return filter_survey_respondents(
        tf,
        target_countries(book),
        country_column=book.country_column,
        submit_column=book.submit_column,
    )


def filter_years(tf: pd.DataFrame, book: BookConfig) -> pd.DataFrame:
    waves = book.waves or {}
    include = waves.get("include")
    if not include:
        logger.warning("waves.include unset — skipping year filter")
        return tf
    year_col = book.year_column
    if year_col not in tf.columns:
        raise KeyError(f"Missing year column {year_col!r}")
    want = {str(y) for y in include}

    def _year_str(x: object) -> str:
        if isinstance(x, float) and x == int(x):
            return str(int(x))
        return str(x)

    years = tf[year_col].map(_year_str)
    # also accept bare ints as strings without .0
    years = years.str.replace(r"\.0$", "", regex=True)
    return tf.loc[years.isin(want)].copy()


def add_group_columns(tf: pd.DataFrame, book: BookConfig) -> pd.DataFrame:
    out = assign_age_groups(
        tf,
        book.age_groups,
        age_column=book.age_column,
        group_col="age_group",
        drop_unmapped=False,
    )
    country_to_group: dict[str, str] = {}
    for group_name, countries in book.compare_groups.items():
        for c in countries:
            country_to_group[str(c)] = group_name
    out["country_group"] = out[book.country_column].map(country_to_group)
    levels = list(book.compare_groups.keys())
    out["country_group"] = pd.Categorical(
        out["country_group"], categories=levels, ordered=True
    )
    return out
