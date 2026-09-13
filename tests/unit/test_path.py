from pathlib import Path

import numpy.testing as npt
import pandas as pd
import pytest

from rse_survey_report.utils import get_data_path, load_data


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

    npt.assert_array_equal(actual_vars, pd.Index(["submitdate_0", "socio1_0"]))
    npt.assert_equal(actual_rows, 3)
