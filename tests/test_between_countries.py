"""Tests for between_countries select-question view."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from rse_survey.analysis.context import AnalysisContext
from rse_survey.analysis.tasks.select_questions import (
    BetweenCountriesTask,
    build_summary_table,
    write_artifacts,
)
from rse_survey.config import QuestionConfig, load_book_config

REPO = Path(__file__).resolve().parents[1]


def test_between_countries_summary_includes_zeros():
    df = pd.DataFrame(
        {
            "row_id": [1, 2, 3],
            "country": ["Germany", "Netherlands", "Netherlands"],
            "country_group": ["Germany", "Netherlands", "Netherlands"],
            "question_id": ["rse1_0"] * 3,
            "value": ["True", "True", "False"],
        }
    )
    summary = build_summary_table(
        df,
        "rse1_0",
        grouping_variable="between_countries",
        group_levels=["Germany", "Netherlands", "United Kingdom"],
    )
    de = summary.loc[summary["country_group"].astype(str).eq("Germany")]
    assert set(de["category"].astype(str)) == {"True", "False"}
    assert int(de.loc[de["category"].eq("False"), "n"].iloc[0]) == 0


def test_write_between_countries_artifacts(tmp_path: Path):
    summary = pd.DataFrame(
        {
            "country_group": ["Germany", "Germany", "Netherlands", "Netherlands"],
            "category": ["True", "False", "True", "False"],
            "n": [10, 1, 5, 5],
            "pct": [90.9, 9.1, 50.0, 50.0],
            "N": [11, 11, 10, 10],
        }
    )
    summary.attrs["N"] = 21
    files = write_artifacts(
        summary=summary,
        out_dir=tmp_path,
        question_id="rse1_0",
        title="Do you write software?",
        focus_label="Germany",
        grouping_variable="between_countries",
        group_levels=["Germany", "Netherlands"],
    )
    assert files["png"].exists()
    assert "between_countries.png" in files["md"].read_text(encoding="utf-8")


def test_between_countries_skips_free_text(tmp_path: Path):
    book = load_book_config("config/book.yml", repo_root=REPO)
    q = QuestionConfig(
        question_id="skill2",
        title="Skills",
        response_kind="free_text",
        tasks=["between_countries"],
    )
    ctx = AnalysisContext(
        book=book,
        question=q,
        focus_df=pd.DataFrame(),
        compare_df=pd.DataFrame(
            {
                "row_id": [1],
                "country_group": ["Germany"],
                "question_id": ["skill2"],
                "value": ["python"],
            }
        ),
        artifacts_dir=tmp_path,
        hf_cache_dir=tmp_path,
        repo_root=REPO,
    )
    result = BetweenCountriesTask().run(ctx)
    assert result.skipped
    assert "token_labels.csv" in (result.skip_reason or "")
