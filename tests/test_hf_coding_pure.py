"""Pure HF coding helpers (no model downloads)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from rse_survey.coding import (
    apply_labels,
    filter_excluded_tokens,
    labels_from_config,
    load_tokens,
    save_labels_to_coding_yml,
    tokenize_series,
)
from rse_survey.config import load_book_config, load_question_coding
from rse_survey.data import read_tf

FIXTURES = Path(__file__).parent / "fixtures"


def test_tokenize_series_splits_and_counts() -> None:
    s = pd.Series(["Python, R", "python", "Git", None, ""])
    out = tokenize_series(s)
    assert set(out.columns) == {"raw", "n"}
    counts = dict(zip(out["raw"], out["n"], strict=True))
    assert counts["python"] == 2
    assert counts["r"] == 1
    assert counts["git"] == 1


def test_filter_excluded_tokens_defaults() -> None:
    tokens = pd.DataFrame({"raw": ["python", "none", "n/a", "git"], "n": [3, 2, 1, 4]})
    kept, excluded = filter_excluded_tokens(tokens)
    assert set(kept["raw"]) == {"python", "git"}
    assert set(excluded["raw"]) == {"none", "n/a"}


def test_labels_from_config_and_apply() -> None:
    cfg = {"labels": {"0": "A", 1: "B"}}
    labels = labels_from_config(cfg)
    assert labels == {0: "A", 1: "B"}
    assignments = pd.DataFrame({"raw": ["x", "y"], "cluster_id": [0, 1], "n": [1, 2]})
    categorized = apply_labels(assignments, labels)
    assert list(categorized["category"]) == ["A", "B"]


def test_load_tokens_filters_to_focus_country(tmp_path: Path) -> None:
    from rse_survey.data import build_clean_dataset

    book_yml = tmp_path / "book.yml"
    book_yml.write_text(
        f"""
data_dir: {FIXTURES.as_posix()}
processed_dir: {(tmp_path / "_data").as_posix()}
focus:
  label: Germany
  countries: [Germany]
age_column: socio3_0
age_groups:
  "Under 35": ["18 to 24 years", "25 to 34 years"]
  "35-44": ["35 to 44 years"]
  "45-54": ["45 to 54 years"]
compare_groups:
  Germany: [Germany]
  Netherlands: [Netherlands]
  United Kingdom: ["United Kingdom"]
  United States: ["United States"]
waves:
  year_column: Year_0
  include: [2026]
questions:
  skill2:
    title: Skills
    response_kind: free_text
""",
        encoding="utf-8",
    )
    book = load_book_config(book_yml)
    build_clean_dataset(book)
    cfg = {
        "question_id": "skill2",
        "text_column": "skill2",
        "exclude_defaults": True,
    }
    tokens = load_tokens(cfg, book=book)
    tf = read_tf(FIXTURES)
    de = tf.loc[
        tf["socio1_0"].eq("Germany")
        & tf["Year_0"].astype(str).str.replace(".0", "").eq("2026"),
        "skill2",
    ]
    expected = set(tokenize_series(de)["raw"])
    assert set(tokens["raw"]) == expected
    assert "r" not in set(tokens["raw"])  # Netherlands-only in fixtures
    assert "hpc" not in set(tokens["raw"])  # UK-only
    assert "old" not in set(tokens["raw"])  # 2025 Germany row filtered out


def test_token_labels_csv_is_editable_source_of_truth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from rse_survey.coding import token_labels as tl
    from rse_survey.coding import workflows as wf

    # Both modules resolve the freeze directory at call time.
    monkeypatch.setattr(tl, "question_cache_dir", lambda qid: tmp_path / qid)
    monkeypatch.setattr(wf, "question_cache_dir", lambda qid: tmp_path / qid)
    assignments = pd.DataFrame(
        {
            "raw": ["python", "rust", "git"],
            "cluster_id": [0, 0, 1],
            "n": [3, 1, 2],
        }
    )
    labels = {0: "Languages", 1: "Tools"}
    categorized = apply_labels(assignments, labels)
    tl.write_labeled_freezes("skill2", assignments, categorized, {"q": "skill2"})

    path = tl.token_labels_path("skill2")
    assert path.exists()
    table = pd.read_csv(path)
    assert list(table.columns[:3]) == ["token", "category_llm", "category_human"]
    assert set(table["token"]) == {"python", "rust", "git"}
    assert (table["category_llm"] == table["category_human"]).all()

    # Human reallocates one token and excludes another
    table.loc[table["token"].eq("rust"), "category_human"] = "Systems"
    table.loc[table["token"].eq("git"), "exclude"] = 1
    table.to_csv(path, index=False)

    cfg = {"question_id": "skill2", "labels": labels}
    wf.run_apply_labels_only(cfg, coding_path=tmp_path / "dummy.yml", from_csv=True)
    refreshed = tl.read_token_labels_csv("skill2", include_excluded=True)
    rust = refreshed.loc[refreshed["token"].eq("rust")].iloc[0]
    assert rust["category_llm"] == "Languages"
    assert rust["category_human"] == "Systems"
    assert int(refreshed.loc[refreshed["token"].eq("git"), "exclude"].iloc[0]) == 1
    active = tl.active_token_labels(refreshed)
    assert "git" not in set(active["token"])
    summary = pd.read_csv(tmp_path / "skill2" / "category_summary.csv")
    assert "Systems" in set(summary["category"])
    assert "Tools" not in set(summary["category"])  # only git was in Tools

    # YAML apply preserves human edits that differ from previous LLM label
    new_labels = {0: "Coding", 1: "Tools"}
    categorized2 = apply_labels(assignments, new_labels)
    tl.write_token_labels_csv("skill2", categorized2, preserve_human_edits=True)
    after = tl.read_token_labels_csv("skill2", include_excluded=True)
    rust2 = after.loc[after["token"].eq("rust")].iloc[0]
    assert rust2["category_llm"] == "Coding"
    assert rust2["category_human"] == "Systems"  # preserved edit
    assert int(after.loc[after["token"].eq("git"), "exclude"].iloc[0]) == 1


def test_load_and_save_question_coding(tmp_path: Path) -> None:
    coding = tmp_path / "free_text_coding.yml"
    coding.write_text(
        yaml.safe_dump(
            {
                "skill2": {
                    "text_column": "skill2",
                    "k": 3,
                    "labels": {0: "Old"},
                    "data_path": "legacy/ignored.csv",
                }
            }
        ),
        encoding="utf-8",
    )
    cfg, path = load_question_coding("skill2", coding_path=coding)
    assert cfg["question_id"] == "skill2"
    assert cfg["k"] == 3
    assert "data_path" not in cfg
    assert path == coding.resolve() or path == coding

    save_labels_to_coding_yml(
        "skill2",
        {0: "New A", 1: "New B"},
        coding_path=coding,
    )
    reloaded = yaml.safe_load(coding.read_text(encoding="utf-8"))
    assert reloaded["skill2"]["labels"] == {0: "New A", 1: "New B"}
    assert reloaded["skill2"]["text_column"] == "skill2"
    assert "data_path" not in reloaded["skill2"]
