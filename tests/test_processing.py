"""Tests for the clean long-format data processing pipeline."""

from __future__ import annotations

from pathlib import Path

from rse_survey.analysis.summarize.categorical import (
    summarize_by_group,
    summarize_categorical_focus,
)
from rse_survey.config import load_book_config
from rse_survey.data import (
    add_group_columns,
    build_clean_dataset,
    filter_countries,
    filter_years,
    focus_long,
    interest_question_ids,
    load_clean_long,
    load_raw,
    select_interest_columns,
    to_long,
)

FIXTURES = Path(__file__).parent / "fixtures"
REPO = Path(__file__).resolve().parents[1]


def _write_book(tmp_path: Path, *, waves: bool = True) -> Path:
    waves_block = (
        """
waves:
  year_column: Year_0
  include: [2026]
"""
        if waves
        else ""
    )
    book_yml = tmp_path / "book.yml"
    book_yml.write_text(
        f"""
data_dir: {FIXTURES.as_posix()}
processed_dir: {(tmp_path / "_data").as_posix()}
focus:
  label: Germany
  countries: [Germany]
age_column: socio3_0
age_groups:
  "Under 35": ["18 to 24 years", "25 to 34 years"]
  "35-44": ["35 to 44 years"]
  "45-54": ["45 to 54 years"]
compare_groups:
  Germany: [Germany]
  Netherlands: [Netherlands]
  United Kingdom: ["United Kingdom"]
  United States: ["United States"]
{waves_block}
questions:
  edu1_0:
    title: Education
    response_kind: categorical
  org2can:
    title: Organisation hopes
    response_kind: categorical
  skill2:
    title: Skills
    response_kind: free_text
""",
        encoding="utf-8",
    )
    return book_yml


def test_filter_countries_and_years(tmp_path):
    book = load_book_config(_write_book(tmp_path), repo_root=REPO)
    tf, _ = load_raw(book)
    qids = interest_question_ids(book)
    tf = select_interest_columns(tf, book, qids)
    filtered = filter_countries(tf, book)
    assert set(filtered["socio1_0"]) <= {
        "Germany",
        "Netherlands",
        "United Kingdom",
        "United States",
    }
    # Fixture includes a 2025 Germany row that year filter should drop
    assert (filtered["Year_0"].astype(str) == "2025").any()
    years = filter_years(filtered, book)
    assert set(years["Year_0"].astype(str).str.replace(".0", "", regex=False)) == {
        "2026"
    }
    assert len(years) == 5


def test_age_and_country_groups(tmp_path):
    book = load_book_config(_write_book(tmp_path), repo_root=REPO)
    tf, _ = load_raw(book)
    tf = select_interest_columns(tf, book, interest_question_ids(book))
    tf = filter_countries(tf, book)
    tf = filter_years(tf, book)
    grouped = add_group_columns(tf, book)
    assert "age_group" in grouped.columns
    assert "country_group" in grouped.columns
    assert grouped["age_group"].notna().all()
    de = grouped.loc[grouped["socio1_0"] == "Germany"]
    assert set(de["age_group"].astype(str)) <= {"Under 35", "35-44"}


def test_to_long_decodes_multiselect(tmp_path):
    book = load_book_config(_write_book(tmp_path), repo_root=REPO)
    tf, all_cols = load_raw(book)
    tf = select_interest_columns(tf, book, interest_question_ids(book))
    tf = filter_countries(tf, book)
    tf = filter_years(tf, book)
    tf = add_group_columns(tf, book)
    long_df = to_long(
        tf,
        all_cols,
        interest_question_ids(book),
        country_column=book.country_column,
        year_column=book.year_column,
    )
    assert set(long_df.columns) >= {
        "row_id",
        "country",
        "country_group",
        "year",
        "age_group",
        "question_id",
        "option_code",
        "value",
    }
    org = long_df.loc[long_df["question_id"] == "org2can"]
    assert "Networking" in set(org["value"])
    assert "Training" in set(org["value"])
    assert "networking" in set(org["value"])  # free-text other
    assert "False" not in set(org["value"].astype(str))
    edu = long_df.loc[long_df["question_id"] == "edu1_0"]
    assert set(edu["option_code"].astype(str)) == {""}
    assert "PhD" in set(edu["value"])


def test_build_and_load_clean_dataset(tmp_path):
    book_path = _write_book(tmp_path)
    book = load_book_config(book_path, repo_root=REPO)
    out = build_clean_dataset(book, repo_root=REPO)
    assert out.exists()
    clean = load_clean_long(book, repo_root=REPO)
    focus = focus_long(clean, book)
    assert set(focus["country"]) == {"Germany"}
    assert focus["row_id"].nunique() == 2

    summary = summarize_categorical_focus(focus, "edu1_0")
    assert not summary.empty
    assert set(summary["category"]) <= {"PhD", "Master"}

    by_country = summarize_by_group(clean, "edu1_0", "country_group")
    assert "country_group" in by_country.columns
    assert by_country["n"].sum() > 0
