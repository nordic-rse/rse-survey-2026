"""Free-text answers: split, recode, and count, as in the R rse-book."""

import re

import pandas as pd

from rse_survey_report.recode_maps import RECODE_MAPS

TEXT_TYPES = {"text", "text_other"}

# a rule maps a regex pattern to a category; category None excludes the answer
Rule = tuple[str, str | None]


def _compile(pattern: str) -> re.Pattern[str]:
    """Compile an R pattern; the inline (?i) flag becomes re.IGNORECASE."""
    return re.compile(pattern.replace("(?i)", ""), flags=re.IGNORECASE)


def text_tokens(answers: pd.Series) -> pd.Series:
    """Split free-text answers into normalized tokens.

    Parameters
    ----------
    answers : pd.Series
        Free-text answers, one per respondent and column

    Returns
    -------
    pd.Series
        One token per comma-separated part of each distinct answer, in lower
        case and with single spaces. Identical answers count once, as in the
        R rse-book. Empty tokens are dropped.
    """
    tokens = (
        answers.dropna()
        .astype(str)
        .drop_duplicates()
        .str.split(r",\s*")
        .explode()
        .str.lower()
        .str.split()
        .str.join(" ")
    )
    return tokens[tokens != ""].reset_index(drop=True)


def allocate_tokens(tokens: pd.Series, rules: list[Rule]) -> pd.DataFrame:
    """Assign each distinct token to a category.

    Parameters
    ----------
    tokens : pd.Series
        Tokens from text_tokens()
    rules : list[Rule]
        Pairs of regex pattern and category, in order of precedence. The
        first matching rule wins. A rule with category None excludes the
        token.

    Returns
    -------
    pd.DataFrame
        One row per distinct token with the columns raw, category,
        allocation ("Unchanged", "Recoded" or "Excluded"), and n. Rows are
        sorted by category size, category, and n; excluded tokens come last.
    """
    compiled = [(_compile(pattern), category) for pattern, category in rules]
    rows = []
    for raw, n in tokens.value_counts().items():
        match = next((c for p, c in compiled if p.search(str(raw))), raw)
        if match is None:
            allocation = "Excluded"
        elif match == raw:
            allocation = "Unchanged"
        else:
            allocation = "Recoded"
        rows.append({"raw": raw, "category": match, "allocation": allocation, "n": n})
    table = pd.DataFrame(rows, columns=["raw", "category", "allocation", "n"])
    cat_n = table.groupby("category", dropna=False)["n"].transform("sum")
    return (
        table.assign(excluded=table["category"].isna(), cat_n=cat_n)
        .sort_values(
            ["excluded", "cat_n", "category", "n", "raw"],
            ascending=[True, False, True, False, True],
        )
        .drop(columns=["excluded", "cat_n"])
        .reset_index(drop=True)
    )


def summarize_allocation(allocation: pd.DataFrame) -> pd.DataFrame:
    """Count the tokens in each category.

    Parameters
    ----------
    allocation : pd.DataFrame
        Table from allocate_tokens()

    Returns
    -------
    pd.DataFrame
        One row per category with the columns category, n, and pct (share of
        all tokens that are not excluded), sorted by n
    """
    counts = (
        allocation.dropna(subset=["category"])
        .groupby("category", as_index=False)["n"]
        .sum()
        .sort_values(["n", "category"], ascending=[False, True])
        .reset_index(drop=True)
    )
    return counts.assign(pct=(100 * counts["n"] / counts["n"].sum()).round(1))


def question_tokens(
    df: pd.DataFrame, codebook: pd.DataFrame, question: str
) -> pd.Series:
    """Return the tokens of all free-text columns of a question."""
    cols = codebook.loc[
        (codebook["id"] == question) & codebook["type"].isin(TEXT_TYPES), "col"
    ]
    cols = [col for col in cols.unique() if col in df.columns]
    if not cols:
        return pd.Series(dtype=str)
    return text_tokens(pd.concat([df[col] for col in cols], ignore_index=True))


def markdown_table(table: pd.DataFrame, right: set[str] = frozenset()) -> str:
    """Write a data frame as a Markdown table; columns in right align right."""

    def cell(value: object) -> str:
        return "" if pd.isna(value) else str(value).replace("|", "\\|")

    header = "| " + " | ".join(table.columns) + " |"
    align = "| " + " | ".join("--:" if c in right else ":--" for c in table.columns)
    body = [
        "| " + " | ".join(cell(v) for v in row) + " |"
        for row in table.itertuples(index=False)
    ]
    return "\n".join([header, align + " |", *body]) + "\n"


def text_table(
    df: pd.DataFrame,
    codebook: pd.DataFrame,
    question: str,
    recode_maps: dict[str, list[Rule]] = RECODE_MAPS,
) -> str:
    """Write the category counts of a free-text question as Markdown.

    Parameters
    ----------
    df : pd.DataFrame
        Survey responses
    codebook : pd.DataFrame
        Codebook from build_codebook()
    question : str
        Question id (e.g. "skill2")
    recode_maps : dict[str, list[Rule]], optional
        Rules for each question, by default RECODE_MAPS. A question without
        rules shows its answers unchanged.

    Returns
    -------
    str
        Markdown table with the columns Category, n, and %
    """
    allocation = allocate_tokens(
        question_tokens(df, codebook, question), recode_maps.get(question, [])
    )
    summary = summarize_allocation(allocation).rename(
        columns={"category": "Category", "pct": "%"}
    )
    return markdown_table(summary, right={"n", "%"})


def allocation_table(
    df: pd.DataFrame,
    codebook: pd.DataFrame,
    question: str,
    recode_maps: dict[str, list[Rule]] = RECODE_MAPS,
) -> str:
    """Write the category of each raw answer of a free-text question as Markdown.

    Parameters
    ----------
    df : pd.DataFrame
        Survey responses
    codebook : pd.DataFrame
        Codebook from build_codebook()
    question : str
        Question id (e.g. "skill2")
    recode_maps : dict[str, list[Rule]], optional
        Rules for each question, by default RECODE_MAPS

    Returns
    -------
    str
        Markdown table with the columns Raw answer, Category, Allocation, and n
    """
    allocation = allocate_tokens(
        question_tokens(df, codebook, question), recode_maps.get(question, [])
    ).rename(
        columns={
            "raw": "Raw answer",
            "category": "Category",
            "allocation": "Allocation",
        }
    )
    return markdown_table(allocation, right={"n"})
