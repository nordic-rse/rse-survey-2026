import numpy.testing as npt
import pandas as pd
import plotly.graph_objects as go
import pytest

from rse_survey_report.config import LIKERT_LEVELS
from rse_survey_report.plotting import (
    count_answers,
    plot_agreement,
    plot_bool,
    plot_choice,
    plot_likert,
    plot_likert2,
)

CODEBOOK = pd.DataFrame(
    [
        # single choice: BSc has no answers
        ("edu", "edu_0", "choice", "MSc", 1),
        ("edu", "edu_0", "choice", "PhD", 2),
        ("edu", "edu_0", "choice", "BSc", 3),
        # multiple choice with an "Other" free-text column
        ("disc", "disc[1]_0", "choice", "Physics", 1),
        ("disc", "disc[2]_0", "choice", "Biology", 2),
        ("disc", "disc[other]_0", "text_other", None, None),
        # bool as read from CSV: answers are text
        ("rse", "rse_0", "bool", "False", 1),
        ("rse", "rse_0", "bool", "True", 2),
        # grid: several columns with several answers each
        ("grid", "grid[1]_0", "choice", "low", 1),
        ("grid", "grid[1]_0", "choice", "high", 2),
        ("grid", "grid[2]_0", "choice", "low", 1),
        ("grid", "grid[2]_0", "choice", "high", 2),
    ],
    columns=["id", "col", "type", "answer", "order"],
).assign(question="Question text")

DF = pd.DataFrame(
    {
        "edu_0": ["PhD", "MSc", "PhD", None],
        "disc[1]_0": [True, False, None, False],
        "disc[2]_0": [True, True, None, False],
        "disc[other]_0": [None, None, None, "Chemistry"],
        "rse_0": [True, True, False, None],
        "grid[1]_0": ["low", "high", None, None],
        "grid[2]_0": ["high", "high", None, None],
        "grp": ["a", "a", "b", None],
    }
)


def test_count_answers_single_choice() -> None:
    counts = count_answers(DF, CODEBOOK, "edu")

    npt.assert_array_equal(counts["answer"], ["MSc", "PhD"])
    npt.assert_array_equal(counts["count"], [1, 2])
    npt.assert_allclose(counts["percent"], [100 / 3, 200 / 3])
    npt.assert_array_equal(counts["n_respondents"], [3, 3])


def test_count_answers_multiple_choice_counts_other_respondents() -> None:
    counts = count_answers(DF, CODEBOOK, "disc")

    npt.assert_array_equal(counts["answer"], ["Physics", "Biology"])
    npt.assert_array_equal(counts["count"], [1, 2])
    npt.assert_array_equal(counts["n_respondents"], [3, 3])


def test_count_answers_bool_from_text_codebook() -> None:
    counts = count_answers(DF, CODEBOOK, "rse")

    npt.assert_array_equal(counts["answer"], ["False", "True"])
    npt.assert_array_equal(counts["count"], [1, 2])


def test_count_answers_grid_column() -> None:
    counts = count_answers(DF, CODEBOOK, "grid[2]_0")

    npt.assert_array_equal(counts["answer"], ["high"])
    npt.assert_array_equal(counts["count"], [2])


def test_count_answers_grid_id_raises() -> None:
    with pytest.raises(ValueError, match="Pass one response column"):
        count_answers(DF, CODEBOOK, "grid")


def test_count_answers_unknown_question_raises() -> None:
    with pytest.raises(ValueError, match="not found"):
        count_answers(DF, CODEBOOK, "missing")


def test_plot_choice_bars_in_codebook_order() -> None:
    fig = plot_choice(DF, CODEBOOK, "edu")
    bar = fig.data[0]

    assert isinstance(bar, go.Bar)
    npt.assert_array_equal(bar.y, ["MSc", "PhD"])
    npt.assert_array_equal(bar.text, ["(n=1)", "(n=2)"])
    assert fig.layout.title.text == "Question text (n=3)"


def test_plot_choice_top_margin_grows_with_title_lines() -> None:
    short = plot_choice(DF, CODEBOOK, "edu", title="Short").to_dict()["layout"]
    long = plot_choice(DF, CODEBOOK, "edu", title="word " * 40).to_dict()["layout"]

    assert long["title"]["text"].count("<br>") == 2
    assert long["margin"]["t"] == short["margin"]["t"] + 2 * 22
    # the plot area keeps its height
    assert long["height"] - long["margin"]["t"] == (
        short["height"] - short["margin"]["t"]
    )


def test_plot_bool_colors_false_red_true_green() -> None:
    bar = plot_bool(DF, CODEBOOK, "rse").data[0]

    assert isinstance(bar, go.Bar)
    npt.assert_array_equal(bar.y, ["False", "True"])
    npt.assert_array_equal(bar.marker.color, ["#D55E00", "#009E73"])


def test_plot_bool_rejects_choice_question() -> None:
    with pytest.raises(ValueError, match="not 'bool'"):
        plot_bool(DF, CODEBOOK, "edu")


TEAM = "I feel valued by... the team."
BOSS = "I feel valued by... my boss."

GRID_CODEBOOK = pd.DataFrame(
    [
        ("agr", "agr[1]_0", "agreement", "Disagree", 1, TEAM),
        ("agr", "agr[1]_0", "agreement", "Neither agree or disagree", 2, TEAM),
        ("agr", "agr[1]_0", "agreement", "Agree", 3, TEAM),
        ("agr", "agr[2]_0", "agreement", "Agree", 1, BOSS),
        ("time", "time[1]_0", "likert", "0% (None at all)", 1, "Time spent on coding?"),
        ("time", "time[1]_0", "likert", "20%", 2, "Time spent on coding?"),
        ("time", "time[2]_0", "likert", "20%", 1, "Time spent on teaching?"),
    ],
    columns=["id", "col", "type", "answer", "order", "question"],
)

GRID_DF = pd.DataFrame(
    {
        "agr[1]_0": ["Disagree", "Neither agree or disagree", "Agree", "Agree"],
        "agr[2]_0": ["Agree", "Agree", None, None],
        "time[1]_0": ["0% (None at all)", "20%", "20%", None],
        "time[2]_0": ["20%", None, None, None],
        "grp": ["a", "a", "b", None],
    }
)


def _bars(fig: go.Figure, name: str) -> list[go.Bar]:
    return [t for t in fig.data if isinstance(t, go.Bar) and t.name == name]


def test_plot_agreement_splits_neutral_around_zero() -> None:
    fig = plot_agreement(GRID_DF, GRID_CODEBOOK, "agr")
    neutral_left, neutral_right = _bars(fig, "Neither agree or disagree")
    (disagree,) = _bars(fig, "Disagree")
    (agree,) = _bars(fig, "Agree")

    npt.assert_array_equal(agree.y, ["the team. (n=4)", "my boss. (n=2)"])
    npt.assert_allclose(disagree.x, [-25, 0])
    npt.assert_allclose(neutral_left.x, [-12.5, 0])
    npt.assert_allclose(neutral_right.x, [12.5, 0])
    npt.assert_allclose(agree.x, [50, 100])
    assert fig.layout.title.text == "I feel valued by..."


def test_plot_likert_segments_in_scale_order() -> None:
    fig = plot_likert(GRID_DF, GRID_CODEBOOK, "time")
    bars = [t for t in fig.data if isinstance(t, go.Bar)]

    assert [bar.name for bar in bars] == LIKERT_LEVELS
    npt.assert_array_equal(bars[0].y, ["coding? (n=3)", "teaching? (n=1)"])
    npt.assert_allclose(bars[0].x, [100 / 3, 0])
    npt.assert_allclose(bars[1].x, [200 / 3, 100])


def test_plot_agreement_rejects_likert_question() -> None:
    with pytest.raises(ValueError, match="not 'agreement'"):
        plot_agreement(GRID_DF, GRID_CODEBOOK, "time")


PAIR_CODEBOOK = pd.DataFrame(
    [
        ("likert0", "likert0[1]_0", "likert", LIKERT_LEVELS[0], 1, "Spent on coding?"),
        ("likert0", "likert0[1]_0", "likert", "20%", 2, "Spent on coding?"),
        ("likert0", "likert0[2]_0", "likert", "20%", 1, "Spent on teaching?"),
        ("likert1", "likert1[1]_0", "likert", "20%", 1, "Wanted for coding?"),
        ("likert1", "likert1[2]_0", "likert", "20%", 1, "Wanted for teaching?"),
    ],
    columns=["id", "col", "type", "answer", "order", "question"],
)

PAIR_DF = pd.DataFrame(
    {
        "likert0[1]_0": ["0% (None at all)", "20%", "20%"],
        "likert0[2]_0": ["20%", None, None],
        "likert1[1]_0": ["20%", "20%", None],
        "likert1[2]_0": ["20%", "20%", "20%"],
    }
)


def test_plot_likert2_actual_left_desired_right() -> None:
    fig = plot_likert2(PAIR_DF, PAIR_CODEBOOK)
    actual_0, _ = _bars(fig, "0% (None at all)")
    actual_20, desired_20 = _bars(fig, "20%")

    npt.assert_array_equal(actual_20.y, ["coding? (n=3 | 2)", "teaching? (n=1 | 3)"])
    npt.assert_allclose(actual_0.x, [-100 / 3, 0])
    npt.assert_allclose(actual_20.x, [-200 / 3, -100])
    npt.assert_allclose(desired_20.x, [100, 100])
    assert actual_20.showlegend
    assert not desired_20.showlegend


def test_plot_choice_grouped_percent_within_group() -> None:
    fig = plot_choice(DF, CODEBOOK, "edu", group_by="grp")
    group_a, group_b = [t for t in fig.data if isinstance(t, go.Bar)]

    assert [group_a.name, group_b.name] == ["a (n=2)", "b (n=1)"]
    npt.assert_array_equal(group_a.y, ["MSc", "PhD"])
    npt.assert_allclose(group_a.x, [50, 50])
    npt.assert_allclose(group_b.x, [0, 100])


def test_plot_bool_grouped_keeps_red_green() -> None:
    fig = plot_bool(DF, CODEBOOK, "rse", group_by="grp")
    (false,) = _bars(fig, "False")
    (true,) = _bars(fig, "True")

    npt.assert_array_equal(false.y, ["a (n=2)", "b (n=1)"])
    npt.assert_allclose(false.x, [0, 100])
    npt.assert_allclose(true.x, [100, 0])
    assert false.marker.color == "#D55E00"
    assert true.marker.color == "#009E73"


def test_plot_agreement_grouped_rows_per_item_and_group() -> None:
    fig = plot_agreement(GRID_DF, GRID_CODEBOOK, "agr", group_by="grp")
    (agree,) = _bars(fig, "Agree")

    npt.assert_array_equal(
        agree.y,
        [
            "the team. · a (n=2)",
            "the team. · b (n=1)",
            "my boss. · a (n=2)",
            "my boss. · b (n=0)",
        ],
    )
    npt.assert_allclose(agree.x, [0, 100, 100, 0])


def test_group_by_missing_column_raises() -> None:
    with pytest.raises(ValueError, match="not found in the responses"):
        plot_likert(GRID_DF, GRID_CODEBOOK, "time", group_by="missing")


def test_plot_likert_grouped_one_subplot_per_group() -> None:
    fig = plot_likert(GRID_DF, GRID_CODEBOOK, "time", group_by="grp")
    none_a, none_b = _bars(fig, "0% (None at all)")

    assert [a.text for a in fig.layout.annotations] == ["<b>a</b>", "<b>b</b>"]
    assert (none_a.yaxis, none_b.yaxis) == ("y", "y2")
    npt.assert_array_equal(none_a.y, ["coding? (n=2)", "teaching? (n=1)"])
    npt.assert_array_equal(none_b.y, ["coding? (n=1)", "teaching? (n=0)"])
    npt.assert_allclose(none_a.x, [50, 0])
    assert none_a.showlegend
    assert not none_b.showlegend
