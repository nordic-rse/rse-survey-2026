from pathlib import Path

import numpy.testing as npt
import pandas as pd
import pytest

from rse_survey_report.utils import (
    get_data_path,
    load_data,
    parse_questions,
    preprocess_data,
)


def test_get_data_path_for_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        get_data_path("missing.csv", 2026)


def test_get_data_path_success() -> None:
    path = get_data_path(file="test.csv", year=2026, data_dir="tests/unit/test_data")
    expected_path = Path(__file__).parent / "test_data" / "2026" / "test.csv"
    assert path == expected_path


def test_load_data_without_rows() -> None:
    path = get_data_path(file="empty.csv", year=2026, data_dir="tests/unit/test_data")
    with pytest.raises(ValueError, match="no rows"):
        load_data(path)


def test_load_data_success() -> None:
    path = get_data_path(file="test.csv", year=2026, data_dir="tests/unit/test_data")
    df = load_data(path)
    actual_vars = df.columns
    actual_rows = len(df)

    assert "Unnamed: 0" not in actual_vars
    npt.assert_array_equal(actual_vars, pd.Index(["submitdate_0", "socio1_0"]))
    npt.assert_equal(actual_rows, 3)


def test_preprocess_data_without_rows() -> None:
    df_na = pd.DataFrame(columns=["submitdate_0", "socio1_0"])
    with pytest.raises(ValueError, match="no rows"):
        preprocess_data(df_na)


def test_preprocess_data_without_required_cols() -> None:
    df_test1 = pd.DataFrame({"socio1_0": ["Germany", "Peru"], "rse1_0": [False, True]})
    with pytest.raises(ValueError):
        preprocess_data(df_test1)

    df_test2 = pd.DataFrame(
        {
            "submitdate_0": ["2026-01-19 20:32:26", "2026-01-19 20:32:26"],
            "rse1_0": [False, True],
        }
    )
    with pytest.raises(ValueError):
        preprocess_data(df_test2)


def test_preprocess_success() -> None:
    path = get_data_path(file="test.csv", year=2026, data_dir="tests/unit/test_data")
    df = load_data(path)
    df_clean = preprocess_data(df)
    actual_vars = df_clean.columns

    npt.assert_array_equal(actual_vars, pd.Index(["country", "complete"]))


def test_parse_questions_success() -> None:
    df = pd.DataFrame(
        {
            "New_name": [
                "currentEmp10_0",
                "currentEmp10[other]_0",
                "org3nord[7]_0",
                "fund3_0",
                "genAI3_0",
                "ethnicity_latino",
                "ukrse1_0",
                "likert5b[1]_0",
            ],
            "Question": [
                " What is your employment?",
                " What is your employment? [Other]",
                " Which tools? [Git]",
                " Which grants? (e.g. DCC [TDCC-NES], etc)",
                " How will AI affect demand? []",
                " Latino",
                " Are you a member?   \tBelgium https://be-rse.org/ "
                "\tGermany http://de-rse.org/  ",
                "  [My experience is in demand]",
            ],
        }
    )
    expected = pd.DataFrame(
        {
            "id": [
                "currentEmp10",
                "currentEmp10",
                "org3nord",
                "fund3",
                "genAI3",
                "ethnicity_latino",
                "ukrse1",
                "likert5b_1",
            ],
            "mc_id": [None, "other", "7", None, None, None, None, "1"],
            "question": [
                "What is your employment?",
                "What is your employment?",
                "Which tools?",
                "Which grants?",
                "How will AI affect demand?",
                "Latino",
                "Are you a member?",
                "My experience is in demand",
            ],
            "mc_answer": [
                None,
                "Other",
                "Git",
                None,
                "",
                None,
                None,
                "My experience is in demand",
            ],
            "col": df["New_name"],
            # likert5b gets its category before it gets the item suffix
            "category": [
                "Employment",
                "Employment",
                None,
                None,
                None,
                None,
                None,
                "Likert scales",
            ],
        }
    )
    categories = {"Employment": ["currentEmp10"], "Likert scales": ["likert5b"]}

    pd.testing.assert_frame_equal(parse_questions(df, categories=categories), expected)


# def test_get_counts_question_country_success() -> None:
