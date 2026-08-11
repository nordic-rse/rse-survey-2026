"""Sub-item handling for likert arrays (paired actual/desired, per statement)."""

from __future__ import annotations

import pandas as pd

from rse_survey.analysis.tasks.select_questions import (
    filter_item,
    question_items,
)
from rse_survey.data import question_columns
from rse_survey.data.reshape import (
    _option_label_lookup,
    to_long,
)


def _all_cols(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["New_name", "Old_name", "Question", "Option"])


LIKERT_META = _all_cols(
    [
        {
            "New_name": "likert0[1]_0",
            "Old_name": "likert0[1]. ...",
            "Question": (
                " On average, how much of your time is spent on [developing software?]"
            ),
            "Option": "developing software?",
        },
        {
            "New_name": "likert0[2]_0",
            "Old_name": "likert0[2]. ...",
            "Question": " On average, how much of your time is spent on [research?]",
            "Option": "research?",
        },
        {
            "New_name": "likert1[1]_0",
            "Old_name": "likert1[1]. ...",
            "Question": (
                " On average, how much time would you like to spend on"
                " [developing software?]"
            ),
            "Option": "developing software?",
        },
        {
            "New_name": "likert1[2]_0",
            "Old_name": "likert1[2]. ...",
            "Question": (
                " On average, how much time would you like to spend on [research?]"
            ),
            "Option": "research?",
        },
    ]
)


def _tf() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "row_id": [1, 2],
            "socio1_0": ["Germany", "Germany"],
            "country_group": ["Germany", "Germany"],
            "age_group": ["35-44", "35-44"],
            "Year_0": [2026, 2026],
            "likert0[1]_0": ["20%", "40%"],
            "likert0[2]_0": ["60%", "20%"],
            "likert1[1]_0": ["40%", "60%"],
            "likert1[2]_0": ["20%", "20%"],
        }
    )


def test_question_columns_accumulates_across_aliases():
    """likert01 spans two stems; stopping at the first drops all of 'desired'."""
    cols = list(_tf().columns)
    matched = question_columns("likert01", cols)
    assert matched == [
        "likert0[1]_0",
        "likert0[2]_0",
        "likert1[1]_0",
        "likert1[2]_0",
    ]


def test_question_columns_unaliased_keeps_first_match():
    cols = ["likert5b[1]_0", "likert5b[2]_0", "edu1_0"]
    assert question_columns("likert5b", cols) == [
        "likert5b[1]_0",
        "likert5b[2]_0",
    ]
    assert question_columns("edu1_0", cols) == ["edu1_0"]


def test_to_long_labels_paired_items_with_condition():
    long_df = to_long(
        _tf(),
        LIKERT_META,
        ["likert01"],
        item_conditions={"likert01": {"likert0": "Actual", "likert1": "Desired"}},
        item_questions={"likert01"},
    )
    assert "item" in long_df.columns
    assert set(long_df["item"]) == {
        "Developing software (Actual)",
        "Developing software (Desired)",
        "Research (Actual)",
        "Research (Desired)",
    }
    # Both halves survive: 2 respondents x 4 array rows
    assert len(long_df) == 8
    actual = long_df.loc[long_df["item"] == "Developing software (Actual)", "value"]
    desired = long_df.loc[long_df["item"] == "Developing software (Desired)", "value"]
    assert sorted(actual) == ["20%", "40%"]
    assert sorted(desired) == ["40%", "60%"]


def test_to_long_without_conditions_uses_plain_item_labels():
    long_df = to_long(
        _tf(),
        LIKERT_META,
        ["likert01"],
        item_questions={"likert01"},
    )
    assert set(long_df["item"]) == {"Developing software", "Research"}


def test_to_long_skips_items_for_non_item_questions():
    """Checkbox grids bracket answer options, not sub-questions."""
    long_df = to_long(
        _tf(),
        LIKERT_META,
        ["likert01"],
        item_questions=set(),
    )
    assert (long_df["item"] == "").all()


def test_option_label_falls_back_to_bracketed_question_text():
    """Some rows have no pre-extracted Option; recover it from the wording."""
    meta = _all_cols(
        [
            {
                "New_name": "likert2a[1]_0",
                "Old_name": "likert2a[1]. ... [Directly reference the software]",
                "Question": " ...software? [Directly reference the software]",
                "Option": None,
            },
            {
                "New_name": "likert2a[2]_0",
                "Old_name": "likert2a[2]. ...",
                "Question": " ...software? [I reference a published paper]",
                "Option": "I reference a published paper",
            },
        ]
    )
    lookup = _option_label_lookup(meta)
    assert lookup["likert2a[1]_0"] == "Directly reference the software"
    assert lookup["likert2a[2]_0"] == "I reference a published paper"


def _long_with_items(items: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "question_id": ["likert01"] * len(items),
            "item": items,
            "value": ["20%"] * len(items),
        }
    )


def test_question_items_needs_at_least_two_to_split():
    assert question_items(_long_with_items(["Research"]), "likert01") == []
    assert question_items(_long_with_items(["", ""]), "likert01") == []


def test_question_items_respects_configured_order():
    df = _long_with_items(["Research (Desired)", "Research (Actual)"])
    ordered = question_items(
        df, "likert01", ["Research (Actual)", "Research (Desired)"]
    )
    assert ordered == ["Research (Actual)", "Research (Desired)"]


def test_question_items_appends_unconfigured_labels():
    df = _long_with_items(["B", "A", "Z"])
    assert question_items(df, "likert01", ["A", "B"]) == ["A", "B", "Z"]


def test_filter_item_selects_one_sub_question():
    df = _long_with_items(["A", "B", "A"])
    assert len(filter_item(df, "A")) == 2
    assert filter_item(df, "missing").empty
