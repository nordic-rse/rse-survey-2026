import pandas as pd

from rse_survey_report.freetext import (
    allocate_tokens,
    allocation_table,
    markdown_table,
    summarize_allocation,
    text_table,
    text_tokens,
)

CODEBOOK = pd.DataFrame(
    [
        ("disc", "disc[1]_0", "choice", "Physics", 1),
        ("disc", "disc[other]_0", "text_other", None, None),
    ],
    columns=["id", "col", "type", "answer", "order"],
)

DF = pd.DataFrame(
    {
        "disc[1]_0": [True, False, True],
        "disc[other]_0": ["Chemistry", "chemistry, Geology", None],
    }
)

RULES = [
    (r"(?i)^py", "Python"),
    (r"(?i)python", "Other language"),
    (r"^none$", None),
]


def test_text_tokens_split_lower_and_dedupe() -> None:
    answers = pd.Series(["Python, R", "python,  r", "Python, R", None, " ,Julia"])
    assert list(text_tokens(answers)) == ["python", "r", "python", "r", "julia"]


def test_allocate_tokens_first_rule_wins() -> None:
    tokens = pd.Series(["python", "python", "none", "rust"])
    table = allocate_tokens(tokens, RULES)
    assert table["raw"].tolist() == ["python", "rust", "none"]
    assert table["category"].tolist()[:2] == ["Python", "rust"]
    assert pd.isna(table["category"].iat[2])
    assert table["allocation"].tolist() == ["Recoded", "Unchanged", "Excluded"]
    assert table["n"].tolist() == [2, 1, 1]


def test_allocate_tokens_ignores_case_in_patterns() -> None:
    table = allocate_tokens(pd.Series(["python"]), [(r"PYTHON", "Python")])
    assert table["category"].tolist() == ["Python"]


def test_summarize_allocation_drops_excluded() -> None:
    tokens = pd.Series(["python", "python", "none", "rust"])
    summary = summarize_allocation(allocate_tokens(tokens, RULES))
    assert summary["category"].tolist() == ["Python", "rust"]
    assert summary["n"].tolist() == [2, 1]
    assert summary["pct"].tolist() == [66.7, 33.3]


def test_markdown_table_escapes_pipes() -> None:
    table = pd.DataFrame({"a": ["x|y"], "n": [1]})
    assert (
        markdown_table(table, right={"n"})
        == "| a | n |\n| :-- | --: |\n| x\\|y | 1 |\n"
    )


def test_text_table_without_rules_shows_answers_unchanged() -> None:
    table = text_table(DF, CODEBOOK, "disc", recode_maps={})
    assert "| chemistry | 2 | 66.7 |" in table
    assert "| geology | 1 | 33.3 |" in table


def test_allocation_table_lists_raw_answers() -> None:
    table = allocation_table(
        DF, CODEBOOK, "disc", recode_maps={"disc": [(r"chem", "Chemistry")]}
    )
    assert "| chemistry | Chemistry | Recoded | 2 |" in table
    assert "| geology | geology | Unchanged | 1 |" in table
