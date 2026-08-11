"""Tests for by_age table + age-grouped horizontal bar artifacts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from rse_survey.analysis.context import AnalysisContext
from rse_survey.analysis.tasks.select_questions import (
    ByAgeTask,
    build_summary_table,
    write_artifacts,
)
from rse_survey.config import QuestionConfig, load_book_config

REPO = Path(__file__).resolve().parents[1]


def test_by_age_summary_table():
    df = pd.DataFrame(
        {
            "row_id": [1, 2, 3, 4],
            "country": ["Germany"] * 4,
            "age_group": ["Under 35", "Under 35", "35-44", "35-44"],
            "question_id": ["rse1_0"] * 4,
            "value": ["True", "False", "True", "True"],
        }
    )
    summary = build_summary_table(df, "rse1_0", grouping_variable="by_age")
    assert set(summary.columns) >= {"age_group", "category", "n", "pct", "N"}
    assert summary.attrs["N"] == 4
    under = summary.loc[summary["age_group"].astype(str).eq("Under 35")]
    assert set(under["category"]) == {"True", "False"}
    assert int(under["N"].iloc[0]) == 2


def test_by_age_includes_zero_count_true_false():
    # 35-44 only has True — False must still appear with n=0
    df = pd.DataFrame(
        {
            "row_id": [1, 2, 3],
            "country": ["Germany"] * 3,
            "age_group": ["Under 35", "Under 35", "35-44"],
            "question_id": ["rse1_0"] * 3,
            "value": ["True", "False", "True"],
        }
    )
    summary = build_summary_table(
        df,
        "rse1_0",
        grouping_variable="by_age",
        group_levels=["Under 35", "35-44", "45-54", "55+"],
    )
    older = summary.loc[summary["age_group"].astype(str).eq("35-44")]
    assert set(older["category"].astype(str)) == {"True", "False"}
    false_row = older.loc[older["category"].astype(str).eq("False")].iloc[0]
    assert int(false_row["n"]) == 0
    assert float(false_row["pct"]) == 0.0
    assert int(false_row["N"]) == 1


def test_by_age_drops_zero_count_non_binary():
    # 35-44 never chose Training — that category must not appear for 35-44
    df = pd.DataFrame(
        {
            "row_id": [1, 1, 2, 3],
            "country": ["Germany"] * 4,
            "age_group": ["Under 35", "Under 35", "Under 35", "35-44"],
            "question_id": ["org2can"] * 4,
            "value": ["Networking", "Training", "Networking", "Networking"],
        }
    )
    summary = build_summary_table(
        df,
        "org2can",
        grouping_variable="by_age",
        group_levels=["Under 35", "35-44"],
    )
    older = summary.loc[summary["age_group"].astype(str).eq("35-44")]
    assert set(older["category"].astype(str)) == {"Networking"}
    assert (older["n"] > 0).all()


def test_by_age_drops_zero_for_mixed_true_false_and_other():
    """True/False plus other labels: drop unused labels (n=0), including False."""
    df = pd.DataFrame(
        {
            "row_id": [1, 2, 3, 4],
            "country": ["Germany"] * 4,
            "age_group": ["Under 35", "Under 35", "Under 35", "55+"],
            "question_id": ["open1de_0"] * 4,
            "value": [
                "True",
                "False",
                "I do not know what ORCID is",
                "True",
            ],
        }
    )
    summary = build_summary_table(
        df,
        "open1de_0",
        grouping_variable="by_age",
        group_levels=["Under 35", "55+"],
    )
    older = summary.loc[summary["age_group"].astype(str).eq("55+")]
    assert set(older["category"].astype(str)) == {"True"}
    assert (older["n"] > 0).all()
    under = summary.loc[summary["age_group"].astype(str).eq("Under 35")]
    assert set(under["category"].astype(str)) == {
        "True",
        "False",
        "I do not know what ORCID is",
    }


def test_write_by_age_artifacts_png(tmp_path: Path):
    summary = pd.DataFrame(
        {
            "age_group": ["Under 35", "Under 35", "35-44", "35-44"],
            "category": ["True", "False", "True", "False"],
            "n": [8, 2, 5, 5],
            "pct": [80.0, 20.0, 50.0, 50.0],
            "N": [10, 10, 10, 10],
        }
    )
    summary.attrs["N"] = 20
    files = write_artifacts(
        summary=summary,
        out_dir=tmp_path,
        question_id="rse1_0",
        title="Do you write software?",
        focus_label="Germany",
        grouping_variable="by_age",
        group_levels=["Under 35", "35-44", "45-54", "55+"],
    )
    assert files["csv"].exists()
    assert files["md"].exists()
    assert files["png"].exists()
    assert files["png"].stat().st_size > 0
    md = files["md"].read_text(encoding="utf-8")
    assert "by_age.png" in md
    assert "N=20" in md


def test_by_age_skips_free_text(tmp_path: Path):
    book = load_book_config("config/book.yml", repo_root=REPO)
    q = QuestionConfig(
        question_id="skill2",
        title="Skills",
        response_kind="free_text",
        tasks=["by_age"],
    )
    ctx = AnalysisContext(
        book=book,
        question=q,
        focus_df=pd.DataFrame(
            {
                "row_id": [1],
                "country": ["Germany"],
                "age_group": ["Under 35"],
                "question_id": ["skill2"],
                "value": ["python"],
            }
        ),
        compare_df=pd.DataFrame(),
        artifacts_dir=tmp_path,
        hf_cache_dir=tmp_path,
        repo_root=REPO,
    )
    result = ByAgeTask().run(ctx)
    assert result.skipped
    assert "token_labels.csv" in (result.skip_reason or "")
