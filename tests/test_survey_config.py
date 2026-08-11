from pathlib import Path

from rse_survey.config import load_book_config

FIXTURES = Path(__file__).parent / "fixtures"
REPO = Path(__file__).resolve().parents[1]


def test_load_book_config_germany_focus(tmp_path):
    book_yml = tmp_path / "book.yml"
    book_yml.write_text(
        f"""
data_dir: {FIXTURES.as_posix()}
focus:
  label: Germany
  countries: [Germany]
age_column: socio3_0
age_groups:
  "Under 35": ["18 to 24 years", "25 to 34 years"]
  "35-44": ["35 to 44 years"]
compare_groups:
  Germany: [Germany]
  Netherlands: [Netherlands]
questions:
  edu1_0:
    title: Education
    response_kind: categorical
    tasks: [focus, by_age, between_countries]
""",
        encoding="utf-8",
    )
    # Point data_dir relative to tmp by rewriting as absolute already done
    cfg = load_book_config(book_yml, repo_root=REPO)
    assert cfg.focus_countries == ["Germany"]
    assert "edu1_0" in cfg.questions
    assert cfg.questions["edu1_0"].tasks[0] == "focus"
    assert cfg.presentation == "both"


def test_load_book_config_presentation(tmp_path):
    book_yml = tmp_path / "book.yml"
    book_yml.write_text(
        f"""
data_dir: {FIXTURES.as_posix()}
presentation: graphic
focus:
  label: Germany
  countries: [Germany]
age_groups: {{}}
compare_groups: {{}}
questions:
  edu1_0:
    title: Education
    response_kind: categorical
    tasks: [focus]
""",
        encoding="utf-8",
    )
    cfg = load_book_config(book_yml, repo_root=REPO)
    assert cfg.presentation == "graphic"


def test_load_book_config_category_order(tmp_path):
    book_yml = tmp_path / "book.yml"
    book_yml.write_text(
        f"""
data_dir: {FIXTURES.as_posix()}
focus:
  label: Germany
  countries: [Germany]
age_groups: {{}}
compare_groups: {{}}
questions:
  rse3_0:
    title: Who uses the code
    response_kind: categorical
    tasks: [focus]
    category_order:
      - "5 - Mostly other people"
      - "4"
      - "0 - Mostly me"
  rse1_0:
    title: Write software
    response_kind: categorical
    tasks: [focus]
    category_order: null
""",
        encoding="utf-8",
    )
    cfg = load_book_config(book_yml, repo_root=REPO)
    assert cfg.questions["rse3_0"].category_order == [
        "5 - Mostly other people",
        "4",
        "0 - Mostly me",
    ]
    assert cfg.questions["rse1_0"].category_order is None


def test_load_book_config_closed_categories(tmp_path):
    book_yml = tmp_path / "book.yml"
    book_yml.write_text(
        f"""
data_dir: {FIXTURES.as_posix()}
focus:
  label: Germany
  countries: [Germany]
age_groups: {{}}
compare_groups: {{}}
questions:
  edu2_0:
    title: Discipline
    response_kind: categorical_with_other
    closed_categories:
      - Computer science
      - Physical sciences
    tasks: [focus]
""",
        encoding="utf-8",
    )
    cfg = load_book_config(book_yml, repo_root=REPO)
    assert cfg.questions["edu2_0"].response_kind == "categorical_with_other"
    assert cfg.questions["edu2_0"].closed_categories == [
        "Computer science",
        "Physical sciences",
    ]


def test_categorical_with_other_requires_closed_categories(tmp_path):
    book_yml = tmp_path / "book.yml"
    book_yml.write_text(
        f"""
data_dir: {FIXTURES.as_posix()}
focus:
  label: Germany
  countries: [Germany]
age_groups: {{}}
compare_groups: {{}}
questions:
  edu2_0:
    title: Discipline
    response_kind: categorical_with_other
    tasks: [focus]
""",
        encoding="utf-8",
    )
    try:
        load_book_config(book_yml, repo_root=REPO)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "closed_categories" in str(exc)


def test_load_book_config_category_labels(tmp_path):
    book_yml = tmp_path / "book.yml"
    book_yml.write_text(
        f"""
data_dir: {FIXTURES.as_posix()}
focus:
  label: Germany
  countries: [Germany]
age_groups: {{}}
compare_groups: {{}}
questions:
  edu1_0:
    title: Education
    response_kind: categorical
    category_labels:
      "Very long original label": "Short label"
    tasks: [focus]
""",
        encoding="utf-8",
    )
    cfg = load_book_config(book_yml, repo_root=REPO)
    assert cfg.questions["edu1_0"].category_labels == {
        "Very long original label": "Short label"
    }


def test_load_book_config_category_groups(tmp_path):
    book_yml = tmp_path / "book.yml"
    book_yml.write_text(
        f"""
data_dir: {FIXTURES.as_posix()}
focus:
  label: Germany
  countries: [Germany]
age_groups: {{}}
compare_groups: {{}}
questions:
  soft1can_0:
    title: Experience
    response_kind: categorical
    category_groups:
      "0-5": ["0", "1", "2", "3", "4"]
      "15+": ["15+"]
    category_order: ["0-5", "15+"]
    tasks: [focus]
""",
        encoding="utf-8",
    )
    cfg = load_book_config(book_yml, repo_root=REPO)
    assert cfg.questions["soft1can_0"].category_groups == {
        "0-5": ["0", "1", "2", "3", "4"],
        "15+": ["15+"],
    }


def test_category_groups_rejects_overlapping_members(tmp_path):
    book_yml = tmp_path / "book.yml"
    book_yml.write_text(
        f"""
data_dir: {FIXTURES.as_posix()}
focus:
  label: Germany
  countries: [Germany]
age_groups: {{}}
compare_groups: {{}}
questions:
  soft1can_0:
    title: Experience
    response_kind: categorical
    category_groups:
      "0-5": ["0", "5"]
      "5-10": ["5", "6"]
    tasks: [focus]
""",
        encoding="utf-8",
    )
    try:
        load_book_config(book_yml, repo_root=REPO)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "appears in both" in str(exc)
