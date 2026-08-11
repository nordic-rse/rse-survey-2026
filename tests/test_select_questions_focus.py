"""Tests for focus select-question table + horizontal bar artifacts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from rse_survey.analysis.context import AnalysisContext
from rse_survey.analysis.tasks.select_questions import (
    FocusTask,
    build_summary_table,
    filter_focus_country,
    write_artifacts,
)
from rse_survey.artifacts.plots.style import SEMANTIC_CATEGORY_COLORS, category_fill_map
from rse_survey.config import QuestionConfig, load_book_config

REPO = Path(__file__).resolve().parents[1]


def test_category_fill_map_semantic_true_false():
    fills = category_fill_map(["True", "False", "PhD"])
    assert fills["True"] == SEMANTIC_CATEGORY_COLORS["True"]
    assert fills["False"] == SEMANTIC_CATEGORY_COLORS["False"]
    assert fills["PhD"] != fills["True"]


def test_is_true_false_categories_exclusive():
    from rse_survey.analysis.summarize.categorical import is_true_false_categories

    assert is_true_false_categories(["True", "False"])
    assert is_true_false_categories(["True"])
    assert not is_true_false_categories(
        ["True", "False", "I do not know what ORCID is"]
    )
    assert not is_true_false_categories(["Networking", "Training"])


def test_apply_category_labels_renames_values():
    from rse_survey.analysis.tasks.select_questions import (
        apply_category_labels,
        build_summary_table,
    )

    df = pd.DataFrame(
        {
            "row_id": [1, 2, 3],
            "country": ["Germany"] * 3,
            "question_id": ["edu1_0"] * 3,
            "value": [
                "University of Applied Sciences entrance qualification or subject-specific higher education entrance qualification (or similar)",
                "Masters Degree",
                "University of Applied Sciences entrance qualification or subject-specific higher education entrance qualification (or similar)",
            ],
        }
    )
    renamed = apply_category_labels(
        df,
        "edu1_0",
        {
            "University of Applied Sciences entrance qualification or subject-specific higher education entrance qualification (or similar)": "UAS entrance",
        },
    )
    summary = build_summary_table(renamed, "edu1_0", grouping_variable="focus")
    assert "UAS entrance" in set(summary["category"].astype(str))
    assert (
        "University of Applied Sciences entrance qualification or subject-specific higher education entrance qualification (or similar)"
        not in set(summary["category"].astype(str))
    )
    uas = summary.loc[summary["category"].eq("UAS entrance")].iloc[0]
    assert int(uas["n"]) == 2


def test_apply_category_groups_aggregates_values():
    from rse_survey.analysis.tasks.select_questions import (
        apply_category_groups,
        build_summary_table,
    )

    df = pd.DataFrame(
        {
            "row_id": [1, 2, 3, 4, 5],
            "country": ["Germany"] * 5,
            "question_id": ["soft1can_0"] * 5,
            "value": ["0", "4", "5", "14", "15+"],
        }
    )
    grouped = apply_category_groups(
        df,
        "soft1can_0",
        {
            "0-5": ["0", "1", "2", "3", "4"],
            "5-10": ["5", "6", "7", "8", "9"],
            "10-15": ["10", "11", "12", "13", "14"],
            "15+": ["15+"],
        },
    )
    summary = build_summary_table(
        grouped,
        "soft1can_0",
        grouping_variable="focus",
        category_order=["0-5", "5-10", "10-15", "15+"],
    )
    assert list(summary["category"].astype(str)) == ["0-5", "5-10", "10-15", "15+"]
    assert int(summary.loc[summary["category"].eq("0-5"), "n"].iloc[0]) == 2
    assert int(summary.loc[summary["category"].eq("5-10"), "n"].iloc[0]) == 1
    assert int(summary.loc[summary["category"].eq("10-15"), "n"].iloc[0]) == 1
    assert int(summary.loc[summary["category"].eq("15+"), "n"].iloc[0]) == 1


def test_filter_and_summary_table():
    df = pd.DataFrame(
        {
            "row_id": [1, 2, 3, 4],
            "country": ["Germany", "Germany", "Germany", "Netherlands"],
            "question_id": ["rse1_0"] * 4,
            "value": ["True", "True", "False", "True"],
        }
    )
    focus = filter_focus_country(df, ["Germany"])
    assert set(focus["country"]) == {"Germany"}
    summary = build_summary_table(focus, "rse1_0", grouping_variable="focus")
    assert list(summary.columns) == ["category", "n", "pct"]
    assert set(summary["category"]) == {"True", "False"}
    assert int(summary.loc[summary["category"].eq("True"), "n"].iloc[0]) == 2
    assert summary.attrs["N"] == 3
    true_pct = float(summary.loc[summary["category"].eq("True"), "pct"].iloc[0])
    assert true_pct == round(100 * 2 / 3, 1)


def test_multiselect_pct_uses_respondent_n():
    df = pd.DataFrame(
        {
            "row_id": [1, 1, 2],
            "country": ["Germany"] * 3,
            "question_id": ["org2can"] * 3,
            "value": ["Networking", "Training", "Networking"],
        }
    )
    summary = build_summary_table(df, "org2can", grouping_variable="focus")
    assert summary.attrs["N"] == 2
    net = summary.loc[summary["category"].eq("Networking")].iloc[0]
    assert int(net["n"]) == 2
    assert float(net["pct"]) == 100.0
    train = summary.loc[summary["category"].eq("Training")].iloc[0]
    assert int(train["n"]) == 1
    assert float(train["pct"]) == 50.0


def test_write_focus_artifacts_png(tmp_path: Path):
    summary = pd.DataFrame(
        {"category": ["True", "False"], "n": [10, 3], "pct": [76.9, 23.1]}
    )
    summary.attrs["N"] = 13
    files = write_artifacts(
        summary=summary,
        out_dir=tmp_path,
        question_id="rse1_0",
        title="Do you write software?",
        focus_label="Germany",
        grouping_variable="focus",
    )
    assert files["csv"].exists()
    assert files["md"].exists()
    assert files["png"].exists()
    assert files["png"].stat().st_size > 0
    md = files["md"].read_text(encoding="utf-8")
    assert "focus.png" in md
    assert "N=13" in md
    assert "| True |" in md


def test_write_artifacts_table_only(tmp_path: Path):
    summary = pd.DataFrame(
        {"category": ["True", "False"], "n": [10, 3], "pct": [76.9, 23.1]}
    )
    summary.attrs["N"] = 13
    files = write_artifacts(
        summary=summary,
        out_dir=tmp_path,
        question_id="rse1_0",
        title="Do you write software?",
        focus_label="Germany",
        grouping_variable="focus",
        presentation="table",
    )
    assert "png" not in files
    assert not (tmp_path / "focus.png").exists()
    md = files["md"].read_text(encoding="utf-8")
    assert "| True |" in md
    assert "focus.png" not in md


def test_write_artifacts_graphic_only(tmp_path: Path):
    summary = pd.DataFrame(
        {"category": ["True", "False"], "n": [10, 3], "pct": [76.9, 23.1]}
    )
    summary.attrs["N"] = 13
    files = write_artifacts(
        summary=summary,
        out_dir=tmp_path,
        question_id="rse1_0",
        title="Do you write software?",
        focus_label="Germany",
        grouping_variable="focus",
        presentation="graphic",
    )
    assert files["png"].exists()
    md = files["md"].read_text(encoding="utf-8")
    assert "focus.png" in md
    assert "| True |" not in md


def test_focus_task_skips_free_text(tmp_path: Path):
    book = load_book_config("config/book.yml", repo_root=REPO)
    q = QuestionConfig(
        question_id="skill2",
        title="Skills",
        response_kind="free_text",
        tasks=["focus"],
    )
    ctx = AnalysisContext(
        book=book,
        question=q,
        focus_df=pd.DataFrame(
            {
                "row_id": [1],
                "country": ["Germany"],
                "question_id": ["skill2"],
                "value": ["python"],
            }
        ),
        compare_df=pd.DataFrame(),
        artifacts_dir=tmp_path,
        hf_cache_dir=tmp_path,
        repo_root=REPO,
    )
    result = FocusTask().run(ctx)
    assert result.skipped
    assert "token_labels.csv" in (result.skip_reason or "")


def test_focus_task_codes_free_text_from_hf_labels(tmp_path: Path):
    book = load_book_config("config/book.yml", repo_root=REPO)
    q = QuestionConfig(
        question_id="currentEmp5_0",
        title="Job title",
        response_kind="free_text",
        tasks=["focus"],
        appendix=True,
    )
    labels_dir = tmp_path / "currentEmp5_0"
    labels_dir.mkdir()
    pd.DataFrame(
        {
            "token": ["rse", "developer", "group leader"],
            "category_llm": [
                "(Research) Software Engineer",
                "Software Developer",
                "Management Roles",
            ],
            "category_human": [
                "(Research) Software Engineer",
                "Software Developer",
                "Management Roles",
            ],
            "cluster_id": [1, 1, 4],
            "n": [1, 1, 1],
            "exclude": [0, 0, 0],
        }
    ).to_csv(labels_dir / "token_labels.csv", index=False)

    ctx = AnalysisContext(
        book=book,
        question=q,
        focus_df=pd.DataFrame(
            {
                "row_id": [1, 2, 3, 4],
                "country": ["Germany"] * 4,
                "question_id": ["currentEmp5_0"] * 4,
                "value": [
                    "RSE",
                    "developer",
                    "group leader",
                    "unsure",  # unmapped → dropped
                ],
            }
        ),
        compare_df=pd.DataFrame(),
        artifacts_dir=tmp_path / "artifacts",
        hf_cache_dir=tmp_path,
        repo_root=REPO,
    )
    result = FocusTask().run(ctx)
    assert not result.skipped
    summary = pd.read_csv(result.files["csv"])
    cats = set(summary["category"].astype(str))
    assert cats == {
        "(Research) Software Engineer",
        "Software Developer",
        "Management Roles",
    }
    assert "unsure" not in cats
    assert int(summary["n"].sum()) == 3
    md = result.files["md"].read_text(encoding="utf-8")
    assert "(Research) Software Engineer" in md
    assert "unsure" not in md
