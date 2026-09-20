"""Quarto book with one chapter per survey question, as rse-book in R."""

import json
from pathlib import Path

import pandas as pd

from rse_survey_report.codebook import build_codebook
from rse_survey_report.config import (
    CATEGORIES,
    COMPARE,
    COUNTRY_GROUPS,
    TARGET,
    TARGET_COUNTRIES,
)
from rse_survey_report.freetext import TEXT_TYPES, Rule
from rse_survey_report.plotting import LIKERT_ACTUAL, LIKERT_DESIRED, _grid_items
from rse_survey_report.recode_maps import RECODE_MAPS
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

INDEX_INTRO = """\
# About {{.unnumbered}}

This book shows the answers to the International RSE Survey 2026 for
{countries}.

It uses the submitted responses only. Percentages are relative to the
respondents who answered each question.

Each chapter shows one survey question in four sections:

- **{label}**: all respondents.
- **By age group**: below 35, 35-45 and 45+.
- **Within {label}**: one group for each country.
- **Between countries**: {groups}.

Free-text answers appear as a table in the **{label}** section only. Rules
from the R rse-book group the answers into categories:

- An "Other" field always gets a table. Without rules, the table shows the
  answers unchanged.
- A free-text question gets a chapter only when it has rules.
- The Recoding appendix gives the category of each raw answer.

## Build the book

The chapters come from the codebook. Do not edit them by hand.

```bash
make book
```

The command writes `index.qmd`, `chapters/` and `_quarto.yml`. Then it renders
the book to `_book/`. The data must be in `data/2026/`.
"""


RECODING_INTRO = """\
# Recoding {#sec-recoding}

This appendix lists the free-text answers in this book. Each row gives the
category of one raw answer:

- **Unchanged**: no rule matches. The answer is its own category.
- **Recoded**: a rule assigns the answer to a category.
- **Excluded**: a rule removes the answer from the analysis.

The answers are split at commas. Identical answers from different respondents
count once. So `n` counts answer parts, not respondents.
"""


def compare_groups(
    target: str = TARGET,
    compare: list[str] = COMPARE,
    country_groups: dict[str, list[str]] = COUNTRY_GROUPS,
) -> dict[str, list[str]]:
    """List the country groups of the "Between countries" section.

    Parameters
    ----------
    target : str, optional
        Group of the chapter analyses, by default TARGET
    compare : list[str], optional
        Groups to compare the target with, by default COMPARE
    country_groups : dict[str, list[str]], optional
        Countries of each group, by default COUNTRY_GROUPS

    Returns
    -------
    dict[str, list[str]]
        The target first, then the compare groups. The target appears once,
        also when compare lists it.
    """
    names = [target] + [name for name in compare if name != target]
    return {name: country_groups[name] for name in names}


def load_book_data(
    year: int = 2026,
    countries: list[str] = TARGET_COUNTRIES,
    groups: dict[str, list[str]] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the codebook and the submitted responses for the book.

    Parameters
    ----------
    year : int, optional
        Year of the survey data, by default 2026
    countries : list[str], optional
        Countries of the chapter analyses, by default TARGET_COUNTRIES
    groups : dict[str, list[str]] | None, optional
        Country groups for the "Between countries" section, by default
        compare_groups()

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
        The codebook, the responses from countries with the column age_group,
        and the responses from groups with the column country_group
    """
    groups = compare_groups() if groups is None else groups
    df_raw = load_data(get_data_path("2026_tf.csv", year))
    df_cols = load_data(get_data_path("2026_all_cols.csv", year))
    codebook = build_codebook(df_cols, df_raw)

    df_clean = preprocess_data(df_raw, excl_var="submitdate_0")
    df_clean = add_age_group(df_clean[df_clean["complete"]].copy())
    df = df_clean[df_clean["country"].isin(countries)]

    country_group = {
        country: group
        for group, members in reversed(groups.items())
        for country in members
    }
    df_compare = df_clean.assign(
        country_group=pd.Categorical(
            df_clean["country"].map(country_group),
            categories=list(groups),
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


def free_text_kind(
    codebook: pd.DataFrame,
    question: str,
    recode_maps: dict[str, list[Rule]] = RECODE_MAPS,
) -> str | None:
    """Return the type of the free-text table of a question.

    Parameters
    ----------
    codebook : pd.DataFrame
        Codebook from build_codebook()
    question : str
        Question id (e.g. "skill2")
    recode_maps : dict[str, list[Rule]], optional
        Rules for each question, by default RECODE_MAPS

    Returns
    -------
    str | None
        "text_other" for a question with an "Other" column, "text" for a
        free-text question with rules in recode_maps, else None. Other
        free-text questions get no table, as in the R rse-book.
    """
    types = set(codebook.loc[codebook["id"] == question, "type"])
    if "text_other" in types:
        return "text_other"
    if "text" in types and question in recode_maps:
        return "text"
    return None


def _text_cell(question: str, kind: str) -> str:
    """Return a Python code cell that shows the free-text table of a question."""
    heading = "### Other answers\n\n" if kind == "text_other" else ""
    return (
        f"{heading}```{{python}}\n#| output: asis\n"
        f"print(text_table(df, codebook, {json.dumps(question)}))\n```\n\n"
        "@sec-recoding lists the raw answers of each category.\n"
    )


def chapter_qmd(
    codebook: pd.DataFrame,
    question: str,
    label: str = TARGET,
    calls: list[tuple[str, str | None]] | None = None,
    free_text: str | None = None,
) -> str:
    """Write the Quarto source of one chapter.

    Parameters
    ----------
    codebook : pd.DataFrame
        Codebook from build_codebook()
    question : str
        Question id (e.g. "edu1")
    label : str, optional
        Name of the countries in df, by default TARGET
    calls : list[tuple[str, str | None]] | None, optional
        Plot calls, by default plot_calls(codebook, question)
    free_text : str | None, optional
        Type of the free-text table from free_text_kind(), by default None
        (no table). The table is in the label section only.

    Returns
    -------
    str
        Chapter with the sections label, "By age group", "Within <label>",
        and "Between countries". A chapter without plots has the label
        section only. The chapter includes ../_setup.qmd, which defines
        codebook, df, and df_compare.
    """
    calls = plot_calls(codebook, question) if calls is None else calls
    title, _, _ = _grid_items(codebook, question)
    sections = [
        (label, "df", ""),
        ("By age group", "df", "age_group"),
        (f"Within {label}", "df", "country"),
        ("Between countries", "df_compare", "country_group"),
    ]
    if not calls:
        sections = sections[:1]
    parts = [
        f"---\ntitle: {json.dumps(title)}\nquestion_id: {question}\n---\n",
        "{{< include ../_setup.qmd >}}\n",
    ]
    for heading, data, group_by in sections:
        parts.append(f"## {heading}\n")
        parts.extend(_code_cell(*call, data, group_by) for call in calls)
        if free_text and heading == label:
            parts.append(_text_cell(question, free_text))
    return "\n".join(parts)


def _and_list(items: list[str]) -> str:
    """Join the items with commas and a final "and"."""
    if len(items) < 2:
        return "".join(items)
    return f"{', '.join(items[:-1])} and {items[-1]}"


def index_qmd(
    label: str = TARGET,
    countries: list[str] = TARGET_COUNTRIES,
    groups: dict[str, list[str]] | None = None,
) -> str:
    """Write the Quarto source of the landing page.

    Parameters
    ----------
    label : str, optional
        Name of the target group, by default TARGET
    countries : list[str], optional
        Countries of the target group, by default TARGET_COUNTRIES
    groups : dict[str, list[str]] | None, optional
        Country groups of the "Between countries" section, by default
        compare_groups()

    Returns
    -------
    str
        Landing page that names the target group and the compare groups
    """
    groups = compare_groups() if groups is None else groups
    names = _and_list(countries)
    return INDEX_INTRO.format(
        label=label,
        countries=names if names == label else f"{label}: {names}",
        groups=_and_list(list(groups)),
    )


def recoding_qmd(codebook: pd.DataFrame, questions: list[str]) -> str:
    """Write the Quarto source of the recoding appendix.

    Parameters
    ----------
    codebook : pd.DataFrame
        Codebook from build_codebook()
    questions : list[str]
        Ids of the questions with a free-text table

    Returns
    -------
    str
        Appendix with one section per question. Each section shows the
        category of each raw answer.
    """
    parts = [RECODING_INTRO, "{{< include ../_setup.qmd >}}\n"]
    for question in questions:
        title, _, _ = _grid_items(codebook, question)
        parts.append(f"## {title}\n")
        parts.append(
            "```{python}\n#| output: asis\n"
            f"print(allocation_table(df, codebook, {json.dumps(question)}))\n```\n"
        )
    return "\n".join(parts)


def _quarto_yml(parts: dict[str, list[str]], appendices: list[str]) -> str:
    """Write _quarto.yml with one book part per category and the appendices."""
    lines = [QUARTO_HEADER.rstrip("\n")]
    for category, questions in parts.items():
        lines.append(f"    - part: {json.dumps(category)}")
        lines.append("      chapters:")
        lines.extend(f"        - chapters/{question}.qmd" for question in questions)
    if appendices:
        lines.append("  appendices:")
        lines.extend(f"    - {path}" for path in appendices)
    return "\n".join(lines) + "\n" + QUARTO_FOOTER


def write_book(
    codebook: pd.DataFrame,
    df: pd.DataFrame,
    out_dir: Path = BOOK_DIR,
    label: str = TARGET,
    countries: list[str] = TARGET_COUNTRIES,
    categories: dict[str, list[str]] = BOOK_CATEGORIES,
    recode_maps: dict[str, list[Rule]] = RECODE_MAPS,
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
        Name of the countries in df, by default TARGET
    countries : list[str], optional
        Countries in df, for the landing page, by default TARGET_COUNTRIES
    categories : dict[str, list[str]], optional
        Book parts in this order, by default BOOK_CATEGORIES
    recode_maps : dict[str, list[Rule]], optional
        Rules for free-text answers, by default RECODE_MAPS

    Returns
    -------
    list[Path]
        Paths of the chapters. A question without plots or free-text table,
        or without responses in df, gets no chapter. Chapters follow the
        survey order within each part. Old chapters in out_dir/chapters are
        removed. Questions with a free-text table also get a section in
        out_dir/appendices/recoding.qmd. The landing page out_dir/index.qmd
        names the target group.
    """
    chapter_dir = out_dir / "chapters"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    for old in chapter_dir.glob("*.qmd"):
        old.unlink()

    answered = df.columns[df.notna().any()]
    parts: dict[str, list[str]] = {category: [] for category in categories}
    paths = []
    text_questions = []
    for key, rows in codebook.groupby("id", sort=False):
        question = str(key)
        category = str(rows["category"].iat[0])
        calls = plot_calls(codebook, question)
        text_cols = rows.loc[rows["type"].isin(TEXT_TYPES), "col"]
        free_text = (
            free_text_kind(codebook, question, recode_maps)
            if text_cols.isin(answered).any()
            else None
        )
        if (
            category not in parts
            or not (calls or free_text)
            or not rows["col"].isin(answered).any()
        ):
            continue
        path = chapter_dir / f"{question}.qmd"
        path.write_text(chapter_qmd(codebook, question, label, calls, free_text))
        parts[category].append(question)
        paths.append(path)
        if free_text:
            text_questions.append(question)

    appendix = out_dir / "appendices" / "recoding.qmd"
    appendix.unlink(missing_ok=True)
    if text_questions:
        appendix.parent.mkdir(exist_ok=True)
        appendix.write_text(recoding_qmd(codebook, text_questions))
    appendices = ["appendices/recoding.qmd"] if text_questions else []

    parts = {category: questions for category, questions in parts.items() if questions}
    (out_dir / "index.qmd").write_text(index_qmd(label, countries))
    (out_dir / "_quarto.yml").write_text(_quarto_yml(parts, appendices))
    return paths


if __name__ == "__main__":
    codebook, df, _ = load_book_data()
    paths = write_book(codebook, df)
    print(f"Wrote {len(paths)} chapters to {BOOK_DIR / 'chapters'}")
