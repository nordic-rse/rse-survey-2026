from pathlib import Path

import numpy.testing as npt
import pandas as pd
import pytest

from rse_survey_report.codebook import add_country, build_codebook, save_codebook


def test_build_codebook_agreement_in_scale_order() -> None:
    df_cols = pd.DataFrame({"New_name": ["agr_0"], "Question": ["I like it."]})
    df = pd.DataFrame({"agr_0": ["Agree", "Strongly disagree", "Disagree", None]})

    codebook = build_codebook(df_cols, df, categories={})

    npt.assert_array_equal(codebook["type"], ["agreement"] * 3)
    npt.assert_array_equal(
        codebook["answer"], ["Strongly disagree", "Disagree", "Agree"]
    )
    npt.assert_array_equal(codebook["order"], [1, 2, 3])


def test_add_country_lists_the_countries_that_answered() -> None:
    df = pd.DataFrame(
        {
            "country": ["Norway", "Finland", "Germany"],
            "complete": [True, True, True],
            "q1_0": ["yes", "no", None],
            "q2_0": [None, None, "yes"],
            "q3_0": [None, None, None],
        }
    )
    codebook = pd.DataFrame({"col": ["q1_0", "q2_0", "q3_0"]})

    res = add_country(codebook, df)

    npt.assert_array_equal(res["country"], ["Finland, Norway", "Germany", ""])


def test_add_country_without_country_column() -> None:
    df = pd.DataFrame({"complete": [True], "q1_0": ["yes"]})

    with pytest.raises(ValueError, match="country"):
        add_country(pd.DataFrame({"col": ["q1_0"]}), df)


def test_save_codebook(tmp_path: Path) -> None:
    codebook = pd.DataFrame(dict(id=[1], country=["Finland"]))
    test_path = tmp_path / "2026" / "test_codebook.csv"

    out = save_codebook(codebook, path=test_path)
    assert out.is_file()
    assert out == test_path

    read_codebook = pd.read_csv(out)
    pd.testing.assert_frame_equal(read_codebook, codebook)


def test_save_codebook_missing_country() -> None:
    codebook = pd.DataFrame(dict(id=[1]))

    with pytest.raises(KeyError, match="country"):
        save_codebook(codebook, "failed_codebook.csv")
