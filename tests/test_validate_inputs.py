from pathlib import Path

from rse_survey.config import load_book_config
from rse_survey.data.validation import validate_inputs

FIXTURES = Path(__file__).parent / "fixtures"
REPO = Path(__file__).resolve().parents[1]


def test_validate_inputs_ok(tmp_path):
    # Copy fixture names expected by loader
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "2026_tf.csv").write_text(
        (FIXTURES / "2026_tf_sample.csv").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (data_dir / "2026_all_cols.csv").write_text(
        (FIXTURES / "2026_all_cols_sample.csv").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    book_yml = tmp_path / "book.yml"
    book_yml.write_text(
        f"""
data_dir: {data_dir.as_posix()}
focus:
  label: Germany
  countries: [Germany]
age_column: socio3_0
age_groups:
  "Under 35": ["25 to 34 years"]
  "35-44": ["35 to 44 years"]
compare_groups:
  Germany: [Germany]
questions:
  edu1_0:
    response_kind: categorical
    tasks: [focus]
""",
        encoding="utf-8",
    )
    book = load_book_config(book_yml, repo_root=REPO)
    result = validate_inputs(book, raise_on_error=True)
    assert result.ok
