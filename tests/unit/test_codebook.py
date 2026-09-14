import numpy.testing as npt
import pandas as pd

from rse_survey_report.codebook import build_codebook


def test_build_codebook_agreement_in_scale_order() -> None:
    df_cols = pd.DataFrame({"New_name": ["agr_0"], "Question": ["I like it."]})
    df = pd.DataFrame({"agr_0": ["Agree", "Strongly disagree", "Disagree", None]})

    codebook = build_codebook(df_cols, df, categories={})

    npt.assert_array_equal(codebook["type"], ["agreement"] * 3)
    npt.assert_array_equal(
        codebook["answer"], ["Strongly disagree", "Disagree", "Agree"]
    )
    npt.assert_array_equal(codebook["order"], [1, 2, 3])
