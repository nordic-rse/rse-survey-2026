import numpy.testing as npt
import pandas as pd

from rse_survey_report.utils import add_age_group


def test_add_age_group_maps_ages_to_ordered_groups() -> None:
    df = pd.DataFrame(
        {
            "socio3_0": [
                "18 to 24 years",
                "35 to 44 years",
                "Age 65 or older",
                "Prefer not to say",
                None,
            ]
        }
    )

    groups = add_age_group(df)["age_group"]

    npt.assert_array_equal(groups.cat.categories, ["Below 35", "35-45", "45+"])
    npt.assert_array_equal(groups.iloc[:3], ["Below 35", "35-45", "45+"])
    assert groups.iloc[3:].isna().all()
