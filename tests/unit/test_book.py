from pathlib import Path

import pandas as pd

from rse_survey_report.book import chapter_qmd, plot_calls, write_book

CODEBOOK = pd.DataFrame(
    [
        # single choice
        ("edu", "edu_0", "choice", "MSc", 1, "Education"),
        ("edu", "edu_0", "choice", "PhD", 2, "Education"),
        # multiple choice with an "Other" free-text column
        ("disc", "disc[1]_0", "choice", "Physics", 1, "Education"),
        ("disc", "disc[2]_0", "choice", "Biology", 2, "Education"),
        ("disc", "disc[other]_0", "text_other", None, None, "Education"),
        # bool
        ("rse", "rse_0", "bool", "False", 1, "RSE role"),
        ("rse", "rse_0", "bool", "True", 2, "RSE role"),
        # grid: several columns with several answers each
        ("grid", "grid[1]_0", "choice", "low", 1, "RSE role"),
        ("grid", "grid[1]_0", "choice", "high", 2, "RSE role"),
        ("grid", "grid[2]_0", "choice", "low", 1, "RSE role"),
        ("grid", "grid[2]_0", "choice", "high", 2, "RSE role"),
        # time shares
        ("likert0", "likert0[1]_0", "likert", "20%", 1, "Likert scales"),
        ("likert1", "likert1[1]_0", "likert", "20%", 1, "Likert scales"),
        # free text
        ("note", "note_0", "text", None, None, "RSE role"),
    ],
    columns=["id", "col", "type", "answer", "order", "category"],
).assign(question="Question text")

DF = pd.DataFrame(
    {
        "edu_0": ["PhD", None],
        "disc[1]_0": [True, False],
        "disc[2]_0": [True, True],
        "disc[other]_0": [None, None],
        "rse_0": [None, None],
        "grid[1]_0": ["low", None],
        "grid[2]_0": ["high", None],
        "likert0[1]_0": ["20%", None],
        "likert1[1]_0": ["20%", None],
        "note_0": ["hello", None],
    }
)

CATEGORIES: dict[str, list[str]] = {
    "RSE role": [],
    "Education": [],
    "Likert scales": [],
}


def test_plot_calls_single_and_multiple_choice() -> None:
    assert plot_calls(CODEBOOK, "edu") == [("plot_choice", "edu")]
    assert plot_calls(CODEBOOK, "disc") == [("plot_choice", "disc")]


def test_plot_calls_grid_gets_one_plot_per_column() -> None:
    assert plot_calls(CODEBOOK, "grid") == [
        ("plot_choice", "grid[1]_0"),
        ("plot_choice", "grid[2]_0"),
    ]


def test_plot_calls_bool_and_likert() -> None:
    assert plot_calls(CODEBOOK, "rse") == [("plot_bool", "rse")]
    assert plot_calls(CODEBOOK, "likert0") == [("plot_likert", "likert0")]
    assert plot_calls(CODEBOOK, "likert1") == [
        ("plot_likert", "likert1"),
        ("plot_likert2", None),
    ]


def test_plot_calls_free_text_gets_no_plot() -> None:
    assert plot_calls(CODEBOOK, "note") == []


def test_chapter_qmd_has_setup_and_sections() -> None:
    qmd = chapter_qmd(CODEBOOK, "edu")
    assert qmd.startswith('---\ntitle: "Question text"\nquestion_id: edu\n---\n')
    assert "{{< include ../_setup.qmd >}}" in qmd
    for heading in ["Nordics", "By age group", "Within Nordics", "Between countries"]:
        assert f"## {heading}\n" in qmd
    assert 'plot_choice(df, codebook, "edu").show()' in qmd
    assert 'plot_choice(df, codebook, "edu", group_by="age_group").show()' in qmd
    assert (
        'plot_choice(df_compare, codebook, "edu", group_by="country_group").show()'
        in qmd
    )


def test_chapter_qmd_likert2_has_no_question_argument() -> None:
    qmd = chapter_qmd(CODEBOOK, "likert1")
    assert "plot_likert2(df, codebook).show()" in qmd


def test_write_book_skips_unanswered_and_free_text(tmp_path: Path) -> None:
    paths = write_book(CODEBOOK, DF, tmp_path, categories=CATEGORIES)
    stems = [path.stem for path in paths]
    assert stems == ["edu", "disc", "grid", "likert0", "likert1"]


def test_write_book_orders_parts_by_categories(tmp_path: Path) -> None:
    write_book(CODEBOOK, DF, tmp_path, categories=CATEGORIES)
    yml = (tmp_path / "_quarto.yml").read_text()
    assert yml.index('part: "RSE role"') < yml.index('part: "Education"')
    assert yml.index("chapters/grid.qmd") < yml.index("chapters/edu.qmd")


def test_write_book_removes_old_chapters(tmp_path: Path) -> None:
    old = tmp_path / "chapters" / "old.qmd"
    old.parent.mkdir()
    old.write_text("old")
    write_book(CODEBOOK, DF, tmp_path, categories=CATEGORIES)
    assert not old.exists()
