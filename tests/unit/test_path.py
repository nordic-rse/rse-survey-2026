from pathlib import Path

import pytest

from rse_survey_report.utils import get_data_path


def test_get_data_path_for_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        get_data_path("missing.csv", 2026)


def test_get_data_path_success() -> None:
    path = get_data_path(file="test.csv", year=2026, data_dir="tests/unit/test_data")
    expected_path = Path(__file__).parent / "test_data" / "2026" / "test.csv"
    assert path == expected_path
