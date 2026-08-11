from pathlib import Path

from rse_survey.data import (
    assign_age_groups,
    filter_survey_respondents,
    question_columns,
    read_tf,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_read_and_filter_germany():
    tf = read_tf(FIXTURES)
    focus = filter_survey_respondents(tf, ["Germany"])
    # Fixture has 2 Germany rows in 2026 and 1 in 2025
    assert len(focus) == 3
    assert set(focus["socio1_0"]) == {"Germany"}


def test_filter_preserves_survey_row_id():
    import pandas as pd

    tf = pd.DataFrame(
        {
            "row_id": ["2026_1", "2026_2", "2026_3"],
            "submitdate_0": ["2026-01-01", "2026-01-01", "2026-01-01"],
            "socio1_0": ["Germany", "Netherlands", "Germany"],
        }
    )
    focus = filter_survey_respondents(tf, ["Germany"])
    assert list(focus["row_id"]) == ["2026_1", "2026_3"]


def test_question_columns_and_age_groups():
    tf = read_tf(FIXTURES)
    assert question_columns("edu1_0", list(tf.columns)) == ["edu1_0"]
    multi = question_columns("org2can", list(tf.columns))
    assert "org2can[SQ001]_0" in multi
    aged = assign_age_groups(
        filter_survey_respondents(tf, ["Germany"]),
        {
            "Under 35": ["18 to 24 years", "25 to 34 years"],
            "35-44": ["35 to 44 years"],
        },
    )
    assert set(aged["age_group"].astype(str)) <= {"Under 35", "35-44"}


def test_assign_age_groups_keep_unmapped():
    import pandas as pd

    df = pd.DataFrame(
        {
            "socio3_0": ["25 to 34 years", "Prefer not to say"],
        }
    )
    kept = assign_age_groups(
        df,
        {"Under 35": ["25 to 34 years"]},
        drop_unmapped=False,
    )
    assert len(kept) == 2
    assert pd.isna(kept.loc[1, "age_group"])
