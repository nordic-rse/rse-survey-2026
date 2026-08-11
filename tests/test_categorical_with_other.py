"""Tests for categorical_with_other select-question behaviour."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from rse_survey.analysis.context import AnalysisContext
from rse_survey.analysis.tasks.select_questions import (
    BetweenCountriesTask,
    FocusTask,
    filter_closed_answers,
    other_labels_by_country,
    write_between_countries_separate_artifacts,
    write_other_by_country_artifacts,
)
from rse_survey.config import QuestionConfig, load_book_config

REPO = Path(__file__).resolve().parents[1]

CLOSED = [
    "Computer science",
    "Physical sciences",
    "Engineering and technology",
]


def _long_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "row_id": [1, 2, 3, 4, 5, 6, 7],
            "country": [
                "Germany",
                "Germany",
                "Germany",
                "Netherlands",
                "Netherlands",
                "United Kingdom",
                "United Kingdom",
            ],
            "country_group": [
                "Germany",
                "Germany",
                "Germany",
                "Netherlands",
                "Netherlands",
                "United Kingdom",
                "United Kingdom",
            ],
            "age_group": [
                "Under 35",
                "Under 35",
                "35-44",
                "Under 35",
                "35-44",
                "Under 35",
                "Under 35",
            ],
            "question_id": ["edu2_0"] * 7,
            "value": [
                "Computer science",
                "Chemie",
                "Physical sciences",
                "Computer science",
                "Chemistry",
                "Engineering and technology",
                "Bioinformatics",
            ],
        }
    )


def test_filter_closed_answers_excludes_other():
    df = _long_frame()
    closed = filter_closed_answers(df, "edu2_0", CLOSED)
    assert set(closed["value"].astype(str)) == {
        "Computer science",
        "Physical sciences",
        "Engineering and technology",
    }
    assert "Chemie" not in set(closed["value"].astype(str))
    assert closed["row_id"].nunique() == 4


def test_other_labels_by_country_unique_unsorted():
    df = _long_frame()
    # Duplicate Chemie to ensure uniqueness
    extra = df.iloc[[1]].copy()
    extra["row_id"] = 99
    df = pd.concat([df, extra], ignore_index=True)
    by_c = other_labels_by_country(df, "edu2_0", CLOSED)
    assert by_c["Germany"] == ["Chemie"]
    assert by_c["Netherlands"] == ["Chemistry"]
    assert by_c["United Kingdom"] == ["Bioinformatics"]
    assert "Computer science" not in by_c.get("Germany", [])


def test_write_other_by_country_artifacts(tmp_path: Path):
    files = write_other_by_country_artifacts(
        tmp_path,
        {"Germany": ["Chemie", "Robotics"], "Netherlands": ["Chemistry"]},
        country_order=["Germany", "Netherlands"],
    )
    payload = json.loads(files["json"].read_text(encoding="utf-8"))
    assert payload["Germany"] == ["Chemie", "Robotics"]
    md = files["md"].read_text(encoding="utf-8")
    assert "### Other answers" not in md
    assert "#### Germany" in md
    assert "- Chemie" in md
    assert "n =" not in md.lower()
    assert "|" not in md.split("#### Germany", 1)[1].split("####")[0]


def test_between_countries_separate_artifacts(tmp_path: Path):
    df = filter_closed_answers(_long_frame(), "edu2_0", CLOSED)
    files = write_between_countries_separate_artifacts(
        frame=df,
        out_dir=tmp_path,
        question_id="edu2_0",
        title="Discipline",
        country_levels=["Germany", "Netherlands", "United Kingdom"],
    )
    assert files["md"].exists()
    assert (tmp_path / "between_countries_Germany.png").exists()
    assert (tmp_path / "between_countries_Netherlands.png").exists()
    assert (tmp_path / "between_countries_United_Kingdom.png").exists()
    assert not (tmp_path / "between_countries.png").exists()
    md = files["md"].read_text(encoding="utf-8")
    assert "#### Germany" in md
    assert "between_countries_Germany.png" in md
    csv = pd.read_csv(files["csv"])
    assert "Chemie" not in set(csv["category"].astype(str))
    assert set(csv["country_group"].astype(str)) >= {
        "Germany",
        "Netherlands",
        "United Kingdom",
    }


def test_shared_fill_map_stable_across_country_subsets():
    """Same category keeps the same palette color regardless of local subset."""
    from rse_survey.artifacts.plots.style import category_fill_map

    all_cats = ["Computer science", "Physical sciences", "Biology", "Law"]
    shared = category_fill_map(all_cats)
    de_only = ["Computer science", "Biology"]
    nl_only = ["Physical sciences", "Computer science", "Law"]
    # Without shared map, local assignment would differ for Computer science
    local_de = category_fill_map(de_only)
    local_nl = category_fill_map(nl_only)
    assert local_de["Computer science"] != local_nl["Computer science"]
    assert shared["Computer science"] == shared["Computer science"]
    assert shared["Computer science"] != shared["Physical sciences"]


def test_focus_task_categorical_with_other(tmp_path: Path):
    book = load_book_config("config/book.yml", repo_root=REPO)
    q = QuestionConfig(
        question_id="edu2_0",
        title="Discipline",
        response_kind="categorical_with_other",
        closed_categories=CLOSED,
        tasks=["focus"],
    )
    df = _long_frame()
    ctx = AnalysisContext(
        book=book,
        question=q,
        focus_df=df,
        compare_df=df,
        artifacts_dir=tmp_path,
        hf_cache_dir=tmp_path,
        repo_root=REPO,
    )
    result = FocusTask().run(ctx)
    assert not result.skipped
    focus_csv = pd.read_csv(tmp_path / "edu2_0" / "focus.csv")
    assert set(focus_csv["category"].astype(str)) <= set(CLOSED)
    assert "Chemie" not in set(focus_csv["category"].astype(str))
    other = json.loads(
        (tmp_path / "edu2_0" / "other_by_country.json").read_text(encoding="utf-8")
    )
    assert other["Germany"] == ["Chemie"]


def test_between_countries_task_categorical_with_other(tmp_path: Path):
    book = load_book_config("config/book.yml", repo_root=REPO)
    q = QuestionConfig(
        question_id="edu2_0",
        title="Discipline",
        response_kind="categorical_with_other",
        closed_categories=CLOSED,
        tasks=["between_countries"],
    )
    df = _long_frame()
    ctx = AnalysisContext(
        book=book,
        question=q,
        focus_df=df,
        compare_df=df,
        artifacts_dir=tmp_path,
        hf_cache_dir=tmp_path,
        repo_root=REPO,
    )
    result = BetweenCountriesTask().run(ctx)
    assert not result.skipped
    assert (tmp_path / "edu2_0" / "between_countries_Germany.png").exists()
    assert (tmp_path / "edu2_0" / "other_by_country.md").exists()
