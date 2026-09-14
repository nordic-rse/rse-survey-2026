"""Quarto book with one chapter per survey question, as rse-book in R."""

import json
from pathlib import Path

import pandas as pd

from rse_survey_report.codebook import build_codebook
from rse_survey_report.config import CATEGORIES, COMPARE_GROUPS, NORDICS
from rse_survey_report.plotting import LIKERT_ACTUAL, LIKERT_DESIRED, _grid_items
from rse_survey_report.utils import (
    add_age_group,
    get_data_path,
    load_data,
    preprocess_data,
)

BOOK_DIR = Path(__file__).resolve().parents[2] / "book"

# the book parts: all categories except the survey setup
BOOK_CATEGORIES = {k: v for k, v in CATEGORIES.items() if k != "Setup"}

PLOT_FUNCTIONS = {
    "bool": "plot_bool",
    "choice": "plot_choice",
    "likert": "plot_likert",
    "agreement": "plot_agreement",
}

QUARTO_HEADER = """\
project:
  type: book
  output-dir: _book
book:
  title: "International RSE Survey 2026"
  author: "RSE Survey Team"
  date: today
  chapters:
    - index.qmd
"""

QUARTO_FOOTER = """\
format:
  html:
    theme: cosmo
    toc: true
    code-fold: true
execute:
  echo: false
  warning: false
  freeze: auto
jupyter: python3
"""


def load_book_data(
    year: int = 2026,
    countries: list[str] = NORDICS,
    compare_groups: dict[str, list[str]] = COMPARE_GROUPS,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the codebook and the submitted responses for the book.

    Parameters
    ----------
    year : int, optional
        Year of the survey data, by default 2026
    countries : list[str], optional
        Countries of the chapter analyses, by default NORDICS
    compare_groups : dict[str, list[str]], optional
        Country groups for the "Between countries" section, by default
        COMPARE_GROUPS

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
        The codebook, the responses from countries with the column age_group,
        and the responses from compare_groups with the column country_group
    """
    df_raw = load_data(get_data_path("2026_tf.csv", year))
    df_cols = load_data(get_data_path("2026_all_cols.csv", year))
    codebook = build_codebook(df_cols, df_raw)

    df_clean = preprocess_data(df_raw, excl_var="submitdate_0")
    df_clean = add_age_group(df_clean[df_clean["complete"]].copy())
    df = df_clean[df_clean["country"].isin(countries)]

    country_group = {
        country: group
        for group, members in reversed(compare_groups.items())
        for country in members
    }
    df_compare = df_clean.assign(
        country_group=pd.Categorical(
            df_clean["country"].map(country_group),
            categories=list(compare_groups),
            ordered=True,
        )
    ).dropna(subset=["country_group"])
    return codebook, df, df_compare


def plot_calls(codebook: pd.DataFrame, question: str) -> list[tuple[str, str | None]]:
    """List the plot functions and their targets for a question.

    Parameters
    ----------
    codebook : pd.DataFrame
        Codebook from build_codebook()
    question : str
        Question id (e.g. "edu1")

    Returns
    -------
    list[tuple[str, str | None]]
        Pairs of plot function name and question id or response column.
        A choice grid (several columns with several answers each) gets one
        plot per column. The desired-time question (LIKERT_DESIRED) also
        gets plot_likert2, which has no question argument (target None).
        Free-text and empty questions get no plot.
    """
    rows = codebook[codebook["id"] == question]
    types = set(rows["type"].dropna()) - {"text_other"}
    if len(types) != 1 or (kind := types.pop()) not in PLOT_FUNCTIONS:
        return []

    answers = rows[rows["type"] == kind]
    cols = list(answers["col"].unique())
    calls: list[tuple[str, str | None]]
    if kind == "choice" and len(cols) > 1 and not answers["col"].is_unique:
        calls = [(PLOT_FUNCTIONS[kind], col) for col in cols]
    else:
        calls = [(PLOT_FUNCTIONS[kind], question)]

    if question == LIKERT_DESIRED and (codebook["id"] == LIKERT_ACTUAL).any():
        calls.append(("plot_likert2", None))
    return calls


def _code_cell(function: str, target: str | None, data: str, group_by: str) -> str:
    """Return a Python code cell that shows one plot."""
    args = [data, "codebook"]
    if target is not None:
        args.append(json.dumps(target))
    if group_by:
        args.append(f"group_by={json.dumps(group_by)}")
    return f"```{{python}}\n{function}({', '.join(args)}).show()\n```\n"


def chapter_qmd(
    codebook: pd.DataFrame,
    question: str,
    label: str = "Nordics",
    calls: list[tuple[str, str | None]] | None = None,
) -> str:
    """Write the Quarto source of one chapter.

    Parameters
    ----------
    codebook : pd.DataFrame
        Codebook from build_codebook()
    question : str
        Question id (e.g. "edu1")
    label : str, optional
        Name of the countries in df, by default "Nordics"
    calls : list[tuple[str, str | None]] | None, optional
        Plot calls, by default plot_calls(codebook, question)

    Returns
    -------
    str
        Chapter with the sections label, "By age group", "Within <label>",
        and "Between countries". The chapter includes ../_setup.qmd, which
        defines codebook, df, and df_compare.
    """
    calls = plot_calls(codebook, question) if calls is None else calls
    title, _, _ = _grid_items(codebook, question)
    sections = [
        (label, "df", ""),
        ("By age group", "df", "age_group"),
        (f"Within {label}", "df", "country"),
        ("Between countries", "df_compare", "country_group"),
    ]
    parts = [
        f"---\ntitle: {json.dumps(title)}\nquestion_id: {question}\n---\n",
        "{{< include ../_setup.qmd >}}\n",
    ]
    for heading, data, group_by in sections:
        parts.append(f"## {heading}\n")
        parts.extend(_code_cell(*call, data, group_by) for call in calls)
    return "\n".join(parts)


def _quarto_yml(parts: dict[str, list[str]]) -> str:
    """Write _quarto.yml with one book part per category."""
    lines = [QUARTO_HEADER.rstrip("\n")]
    for category, questions in parts.items():
        lines.append(f"    - part: {json.dumps(category)}")
        lines.append("      chapters:")
        lines.extend(f"        - chapters/{question}.qmd" for question in questions)
    return "\n".join(lines) + "\n" + QUARTO_FOOTER


def write_book(
    codebook: pd.DataFrame,
    df: pd.DataFrame,
    out_dir: Path = BOOK_DIR,
    label: str = "Nordics",
    categories: dict[str, list[str]] = BOOK_CATEGORIES,
) -> list[Path]:
    """Write one chapter per plottable question and the book _quarto.yml.

    Parameters
    ----------
    codebook : pd.DataFrame
        Codebook from build_codebook()
    df : pd.DataFrame
        Survey responses of the chapter analyses
    out_dir : Path, optional
        Book directory, by default <repo root>/book
    label : str, optional
        Name of the countries in df, by default "Nordics"
    categories : dict[str, list[str]], optional
        Book parts in this order, by default BOOK_CATEGORIES

    Returns
    -------
    list[Path]
        Paths of the chapters. A question without plots, or without
        responses in df, gets no chapter. Chapters follow the survey order
        within each part. Old chapters in out_dir/chapters are removed.
    """
    chapter_dir = out_dir / "chapters"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    for old in chapter_dir.glob("*.qmd"):
        old.unlink()

    answered = df.columns[df.notna().any()]
    parts: dict[str, list[str]] = {category: [] for category in categories}
    paths = []
    for question, rows in codebook.groupby("id", sort=False):
        category = str(rows["category"].iat[0])
        calls = plot_calls(codebook, str(question))
        if category not in parts or not calls or not rows["col"].isin(answered).any():
            continue
        path = chapter_dir / f"{question}.qmd"
        path.write_text(chapter_qmd(codebook, str(question), label, calls))
        parts[category].append(str(question))
        paths.append(path)

    parts = {category: questions for category, questions in parts.items() if questions}
    (out_dir / "_quarto.yml").write_text(_quarto_yml(parts))
    return paths


if __name__ == "__main__":
    codebook, df, _ = load_book_data()
    paths = write_book(codebook, df)
    print(f"Wrote {len(paths)} chapters to {BOOK_DIR / 'chapters'}")
