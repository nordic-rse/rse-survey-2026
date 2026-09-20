"""Plots of the survey questions, one plot type per question type in the codebook."""

import os
import textwrap
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from rse_survey_report.config import AGREEMENT_LEVELS, LIKERT_LEVELS

CHOICE_COLOR = "darkblue"
BOOL_COLORS = {"False": "#D55E00", "True": "#009E73"}
LIKERT_COLORS = dict(
    zip(
        LIKERT_LEVELS,
        ["#fde725", "#7ad151", "#22a884", "#2a788e", "#414487", "#440154"],
        strict=True,
    )
)
AGREEMENT_COLORS = dict(
    zip(
        AGREEMENT_LEVELS,
        ["#b2302f", "#ec8a83", "#f0efec", "#6da7ec", "#1c5cab"],
        strict=True,
    )
)
GROUP_COLORS = [
    "#2a78d6",
    "#eb6834",
    "#1baf7a",
    "#eda100",
    "#e87ba4",
    "#008300",
    "#4a3aa7",
    "#e34948",
]
DARK_FILLS = {"#2a788e", "#414487", "#440154", "#1c5cab", "#b2302f"}
INK = "#1a1a19"
DIVERGING_XAXIS: dict[str, Any] = {
    "range": [-100, 100],
    "tickvals": [-100, -50, 0, 50, 100],
    "ticktext": ["100%", "50%", "0%", "50%", "100%"],
    "zeroline": True,
    "zerolinecolor": "#8a8984",
}
TITLE_PAD = 35
TITLE_LINE = 22
TITLE_GAP = 25

LIKERT_ACTUAL = "likert0"
LIKERT_DESIRED = "likert1"


def _wrap(text: str, width: int) -> str:
    """Wrap text for plotly, which breaks lines at <br>."""
    return "<br>".join(textwrap.wrap(text, width))


def _label_with_n(label: str, n_text: str) -> str:
    """Wrap a row label for plotly and keep its (n=...) part in one piece."""
    return f"{_wrap(label, 40)} ({n_text})".strip()


def _title(title: str, extra: int = 0) -> tuple[dict[str, Any], int]:
    """Wrap the title, pin it to the top of the figure, and return the top margin.

    The top margin grows with the number of title lines, so a long title does
    not overlap the plot. extra adds space below the title, e.g. for subplot
    titles.
    """
    text = _wrap(title, 70)
    n_lines = text.count("<br>") + 1
    layout = {"text": text, "y": 1, "yref": "container", "yanchor": "top"}
    layout["pad"] = {"t": TITLE_PAD}
    return layout, TITLE_PAD + TITLE_LINE * n_lines + TITLE_GAP + extra


def _question_rows(codebook: pd.DataFrame, question: str) -> pd.DataFrame:
    """Select the codebook rows of a question id or a response column."""
    rows = codebook[(codebook["id"] == question) | (codebook["col"] == question)]
    if rows.empty:
        raise ValueError(f"Question '{question}' not found in the codebook.")
    return rows


def _question_text(codebook: pd.DataFrame, question: str) -> str:
    """Return the question text of a question id or a response column."""
    return str(_question_rows(codebook, question)["question"].iat[0])


def _check_type(codebook: pd.DataFrame, question: str, expected: str) -> None:
    """Raise if the answers of a question do not have the expected type."""
    types = set(_question_rows(codebook, question)["type"]) - {"text_other"}
    if types != {expected}:
        raise ValueError(
            f"Question '{question}' has type {sorted(types)}, not '{expected}'."
        )


def _split_groups(
    df: pd.DataFrame, group_by: str | None
) -> list[tuple[str, pd.DataFrame]]:
    """Split the responses by the values of group_by, in the order of the values.

    Without group_by, all responses form one group without a name. Respondents
    without a group value are dropped. Categorical values keep their order,
    other values are sorted.
    """
    if group_by is None:
        return [("", df)]
    if group_by not in df:
        raise ValueError(f"Column '{group_by}' not found in the responses.")
    values = df[group_by]
    if isinstance(values.dtype, pd.CategoricalDtype):
        groups = [group for group in values.cat.categories if (values == group).any()]
    else:
        groups = sorted(values.dropna().unique(), key=str)
    return [(str(group), df[values == group]) for group in groups]


def count_answers(
    df: pd.DataFrame, codebook: pd.DataFrame, question: str
) -> pd.DataFrame:
    """Count the answers of a choice, bool, likert or agreement question.

    A question with one response column is single choice: each answer is
    counted. A question with one column per option is multiple choice: the
    True values of each option are counted. "Other" free text is not counted
    as an answer, but its respondents count as having answered.

    Parameters
    ----------
    df : pd.DataFrame
        Survey responses
    codebook : pd.DataFrame
        Codebook from build_codebook()
    question : str
        Question id (e.g. "edu1") or response column (e.g. "likert1[1]_0")

    Returns
    -------
    pd.DataFrame
        Answers in codebook order with the columns answer, count, percent,
        and n_respondents. Percent is relative to the respondents who answered
        the question. Answers without a count are dropped.

    Raises
    ------
    ValueError
        Raises if the question is not in the codebook
        Raises if the question has no choice, bool, likert or agreement answers
        Raises if the question has several columns with several answers each
    """
    rows = _question_rows(codebook, question)
    answers = rows[
        rows["type"].isin(["choice", "bool", "likert", "agreement"])
    ].sort_values("order")
    if answers.empty:
        raise ValueError(
            f"Question '{question}' has no choice, bool, likert or agreement answers."
        )
    cols = list(answers["col"].unique())

    if len(cols) == 1:
        # compare as text: a codebook read from CSV holds "True", not True
        responses = df[cols[0]].dropna().astype(str)
        n_respondents = len(responses)
        counts = answers["answer"].astype(str).map(responses.value_counts())
    elif answers["col"].is_unique:
        selected = df[cols].eq(True)
        other_cols = list(rows.loc[rows["type"] == "text_other", "col"])
        answered = selected.any(axis=1) | df[other_cols].notna().any(axis=1)
        n_respondents = int(answered.sum())
        counts = answers["col"].map(selected.sum())
    else:
        raise ValueError(
            f"Question '{question}' has several columns with several answers each. "
            "Pass one response column instead."
        )

    return (
        pd.DataFrame(
            {
                "answer": answers["answer"].astype(str),
                "count": counts.fillna(0).astype(int),
            }
        )
        .assign(
            percent=lambda d: 100 * d["count"] / n_respondents,
            n_respondents=n_respondents,
        )
        .query("count > 0")
        .reset_index(drop=True)
    )


def _bar_plot(
    counts: pd.DataFrame, title: str, color: str | list[str], bar_width: float
) -> go.Figure:
    """Plot horizontal bars of the answer percentages with (n=count) labels."""
    fig = go.Figure()
    if counts.empty:
        fig.add_annotation(text="No responses available.", showarrow=False)
        title_layout, top = _title(title)
        fig.update_layout(
            title=title_layout, template="plotly_white", margin={"t": top}
        )
        return fig

    fig.add_bar(
        x=counts["percent"],
        # plotly-stubs allows only numbers, plotly also takes category text
        y=[_wrap(answer, 40) for answer in counts["answer"]],  # type: ignore[arg-type]
        orientation="h",
        width=bar_width,
        marker_color=color,
        text=[f"(n={count})" for count in counts["count"]],
        textposition="outside",
        cliponaxis=False,
    )
    n_respondents = counts["n_respondents"].iat[0]
    title_layout, top = _title(f"{title} (n={n_respondents})")
    fig.update_layout(
        title=title_layout,
        template="plotly_white",
        xaxis={"title": "Percentage", "range": [0, counts["percent"].max() * 1.2]},
        yaxis={"autorange": "reversed"},
        # bottom margin: the plotly default of 80 px
        margin={"t": top, "b": 80},
        height=top + 50 + 40 * len(counts),
    )
    return fig


def _grouped_bar_plot(
    groups: list[tuple[str, pd.DataFrame]],
    codebook: pd.DataFrame,
    question: str,
    title: str,
) -> go.Figure:
    """Plot the answer percentages per group as bars side by side.

    Follows plot_heatmap_category_barplot() with group_by in rse-book. Each
    percent is relative to the respondents of its group.
    """
    if len(groups) > len(GROUP_COLORS):
        raise ValueError(
            f"{len(groups)} groups, but the plot allows at most "
            f"{len(GROUP_COLORS)}. Merge groups first."
        )
    grouped = pd.concat([group_df for _, group_df in groups])
    answers = list(count_answers(grouped, codebook, question)["answer"])
    if not answers:
        return _bar_plot(pd.DataFrame(), title, CHOICE_COLOR, bar_width=0.9)

    fig = go.Figure()
    max_percent = 0.0
    for (group, group_df), color in zip(groups, GROUP_COLORS, strict=False):
        counts = count_answers(group_df, codebook, question)
        n_respondents = int(counts["n_respondents"].max()) if len(counts) else 0
        counts = counts.set_index("answer").reindex(answers, fill_value=0)
        max_percent = max(max_percent, float(counts["percent"].max()))
        fig.add_bar(
            x=counts["percent"],
            # plotly-stubs allows only numbers, plotly also takes category text
            y=[_wrap(answer, 40) for answer in answers],  # type: ignore[arg-type]
            orientation="h",
            name=f"{group} (n={n_respondents})",
            marker_color=color,
            text=[f"(n={count})" for count in counts["count"]],
            textposition="outside",
            cliponaxis=False,
        )
    title_layout, top = _title(title)
    plot_height = 20 + 22 * len(answers) * len(groups)
    fig.update_layout(
        barmode="group",
        title=title_layout,
        template="plotly_white",
        xaxis={"title": "Percentage", "range": [0, max_percent * 1.25]},
        yaxis={"autorange": "reversed"},
        # legend 70 px below the plot area, under the x-axis title
        legend={"orientation": "h", "yanchor": "top", "y": -70 / plot_height, "x": 0},
        margin={"t": top, "b": 120},
        height=top + plot_height + 120,
    )
    return fig


def plot_choice(
    df: pd.DataFrame,
    codebook: pd.DataFrame,
    question: str,
    title: str | None = None,
    group_by: str | None = None,
) -> go.Figure:
    """Plot the answer percentages of a single- or multiple-choice question.

    Follows plot_heatmap_category_barplot() in rse-book/R/postprocessing.R.

    Parameters
    ----------
    df : pd.DataFrame
        Survey responses
    codebook : pd.DataFrame
        Codebook from build_codebook()
    question : str
        Question id (e.g. "edu1") or response column (e.g. "likert1[1]_0")
    title : str | None, optional
        Plot title, by default the question text
    group_by : str | None, optional
        Column in df to group the respondents by (e.g. "age_group"), by
        default None. Each group gets its own bar per answer and colour.

    Returns
    -------
    go.Figure
        Horizontal bar plot, bars in codebook order

    Raises
    ------
    ValueError
        Raises if the question does not have type "choice"
        Raises if group_by is not a column of df
        Raises if group_by has more groups than GROUP_COLORS has colours
    """
    _check_type(codebook, question, "choice")
    if title is None:
        title = _question_text(codebook, question)
    if group_by is not None:
        groups = _split_groups(df, group_by)
        return _grouped_bar_plot(groups, codebook, question, title)
    counts = count_answers(df, codebook, question)
    return _bar_plot(counts, title, CHOICE_COLOR, bar_width=0.9)


def plot_bool(
    df: pd.DataFrame,
    codebook: pd.DataFrame,
    question: str,
    title: str | None = None,
    group_by: str | None = None,
) -> go.Figure:
    """Plot the False/True percentages of a bool question.

    Follows plot_likert_barplot() in rse-book/R/postprocessing.R.

    Parameters
    ----------
    df : pd.DataFrame
        Survey responses
    codebook : pd.DataFrame
        Codebook from build_codebook()
    question : str
        Question id (e.g. "rse1") or response column (e.g. "rse1_0")
    title : str | None, optional
        Plot title, by default the question text
    group_by : str | None, optional
        Column in df to group the respondents by (e.g. "age_group"), by
        default None. Each group gets one stacked False/True bar.

    Returns
    -------
    go.Figure
        Horizontal bar plot with the bars False (red) and True (green),
        in colours that stay distinct for red-green colour blindness

    Raises
    ------
    ValueError
        Raises if the question does not have type "bool"
        Raises if group_by is not a column of df
    """
    _check_type(codebook, question, "bool")
    if title is None:
        title = _question_text(codebook, question)
    if group_by is not None:
        _, data = _grid_counts(df, codebook, question, list(BOOL_COLORS), group_by)
        return _stacked_bar(data, title, BOOL_COLORS, diverging=False)
    counts = count_answers(df, codebook, question)
    colors = [BOOL_COLORS[answer] for answer in counts["answer"]]
    return _bar_plot(counts, title, colors, bar_width=0.7)


def _grid_items(
    codebook: pd.DataFrame, question: str
) -> tuple[str, list[str], list[str]]:
    """Split the item questions of a grid into the shared stem and item labels."""
    rows = _question_rows(codebook, question).drop_duplicates("col")
    rows = rows[rows["type"] != "text_other"]
    questions = [str(text).strip() for text in rows["question"]]
    if len(questions) == 1:
        return questions[0], list(rows["col"]), [""]
    stem = os.path.commonprefix(questions)
    stem = stem[: stem.rfind(" ") + 1]  # cut at a word boundary
    labels = [text[len(stem) :].strip() for text in questions]
    return stem.strip(), list(rows["col"]), labels


def _grid_counts(
    df: pd.DataFrame,
    codebook: pd.DataFrame,
    question: str,
    levels: list[str],
    group_by: str | None = None,
    group_in_label: bool = True,
) -> tuple[str, pd.DataFrame]:
    """Count the answers of each grid item on a fixed answer scale.

    One row per item, or per item and group. With group_in_label, the group
    name follows the item label; the column group holds it in any case. The
    column row numbers the rows in plot order.
    """
    stem, cols, labels = _grid_items(codebook, question)
    groups = _split_groups(df, group_by)
    frames: list[pd.DataFrame] = []
    for col, label in zip(cols, labels, strict=True):
        for group, group_df in groups:
            counts = count_answers(group_df, codebook, col)
            unknown = set(counts["answer"]) - set(levels)
            if unknown:
                raise ValueError(
                    f"Column '{col}' has answers outside the scale: {sorted(unknown)}."
                )
            # every answer is on the scale: the counts add up to the respondents
            n_respondents = int(counts["count"].sum())
            parts = (label, group) if group_in_label else (label,)
            row_label = " · ".join(part for part in parts if part)
            frames.append(
                counts.set_index("answer")[["count", "percent"]]
                .reindex(levels, fill_value=0)
                .rename_axis("answer")
                .reset_index()
                .assign(
                    item=_label_with_n(row_label, f"n={n_respondents}"),
                    label=row_label,
                    n_respondents=n_respondents,
                    group=group,
                    row=len(frames),
                )
            )
    return stem, pd.concat(frames, ignore_index=True)


def _add_segment(
    fig: go.Figure,
    segment: pd.DataFrame,
    y: list[str],
    level: str,
    share: float,
    colors: dict[str, str],
    showlegend: bool = True,
    label: bool = True,
    hover_prefix: str = "",
    row: int = 1,
) -> None:
    """Add one answer of a stacked bar plot as a trace.

    share scales the percent; a negative share draws the segment left of zero.
    row is the subplot of the trace.
    """
    color = colors[level]
    fig.add_bar(
        x=share * segment["percent"],
        # plotly-stubs allows only numbers, plotly also takes category text
        y=y,  # type: ignore[arg-type]
        orientation="h",
        name=level,
        legendgroup=level,
        legendrank=list(colors).index(level),
        showlegend=showlegend,
        marker={"color": color, "line": {"color": "white", "width": 2}},
        text=[f"{p:.0f}%" if label and p >= 5 else "" for p in segment["percent"]],
        textposition="inside",
        insidetextanchor="middle",
        textfont={"color": "white" if color in DARK_FILLS else INK},
        customdata=segment[["percent", "count"]].to_numpy(),
        hovertemplate=f"%{{y}}<br>{hover_prefix}%{{fullData.name}}: "
        "%{customdata[0]:.0f}% (n=%{customdata[1]})<extra></extra>",
        row=row,
        col=1,
    )


def _group_names(data: pd.DataFrame) -> list[str]:
    """Return the group names of grid counts in plot order."""
    return list(dict.fromkeys(data["group"]))


def _new_figure(groups: list[str]) -> go.Figure:
    """Create one subplot per group, stacked vertically with a shared x-axis.

    Without groups (one group without a name) the figure has one plot.
    """
    titles = [f"<b>{group}</b>" for group in groups] if any(groups) else None
    return make_subplots(
        rows=len(groups),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=min(0.08, 0.5 / len(groups)),
        subplot_titles=titles,
    )


def _stacked_layout(
    fig: go.Figure,
    title: str,
    xaxis: dict[str, Any],
    n_rows: int,
    n_subplots: int = 1,
    top: int = 0,
) -> float:
    """Lay out a stacked bar plot: legend at the bottom, first row on top.

    n_rows is the number of bars per subplot; top adds space above the plot.
    Returns the height of the plot area in pixels.
    """
    plot_height = n_subplots * (45 * n_rows + 40)
    # subplot titles sit above the first subplot, below the figure title
    title_layout, title_top = _title(title, extra=20 if fig.layout.annotations else 0)
    # bottom margin: the x-axis title and a legend of up to two lines
    margin = {"t": title_top + top, "b": 170}
    fig.update_layout(
        barmode="relative",
        title=title_layout,
        template="plotly_white",
        # legend 70 px below the plot area, under the x-axis title
        legend={"orientation": "h", "yanchor": "top", "y": -70 / plot_height, "x": 0},
        uniformtext={"minsize": 9, "mode": "hide"},
        margin=margin,
        height=plot_height + margin["t"] + margin["b"],
    )
    fig.update_xaxes(xaxis)
    fig.update_xaxes(title_text="Share of respondents", row=n_subplots, col=1)
    fig.update_yaxes(autorange="reversed")
    return plot_height


def _stacked_bar(
    data: pd.DataFrame,
    title: str,
    colors: dict[str, str],
    diverging: bool,
    subplots: bool = False,
) -> go.Figure:
    """Plot one horizontal bar per row with the answers as stacked segments.

    A diverging bar puts the answers before the middle answer left of zero,
    the answers after it right of zero, and half of the middle answer on each
    side. With subplots, each group gets its own subplot.
    """
    levels = list(colors)
    # (answer, share of its percent, whether it carries the legend and label)
    if diverging:
        mid = len(levels) // 2
        segments = (
            [(levels[mid], -0.5, False)]
            + [(level, -1.0, True) for level in reversed(levels[:mid])]
            + [(levels[mid], 0.5, True)]
            + [(level, 1.0, True) for level in levels[mid + 1 :]]
        )
    else:
        segments = [(level, 1.0, True) for level in levels]

    groups = _group_names(data) if subplots else [""]
    fig = _new_figure(groups)
    for subplot, group in enumerate(groups, start=1):
        group_data = data[data["group"] == group] if subplots else data
        for level, share, main in segments:
            segment = group_data[group_data["answer"] == level]
            _add_segment(
                fig,
                segment,
                list(segment["item"]),
                level,
                share,
                colors,
                showlegend=main and subplot == 1,
                label=main,
                row=subplot,
            )
    xaxis: dict[str, Any] = (
        DIVERGING_XAXIS if diverging else {"range": [0, 100], "ticksuffix": "%"}
    )
    _stacked_layout(
        fig, title, xaxis, data["row"].nunique() // len(groups), len(groups)
    )
    return fig


def plot_likert(
    df: pd.DataFrame,
    codebook: pd.DataFrame,
    question: str,
    title: str | None = None,
    group_by: str | None = None,
) -> go.Figure:
    """Plot the time shares of a likert question as 100% stacked bars.

    One bar per item. The segments run from "0% (None at all)" to
    "100% (All my time)" in viridis, yellow to purple.

    Parameters
    ----------
    df : pd.DataFrame
        Survey responses
    codebook : pd.DataFrame
        Codebook from build_codebook()
    question : str
        Question id (e.g. "likert1") or response column (e.g. "likert1[1]_0")
    title : str | None, optional
        Plot title, by default the question text that the items share
    group_by : str | None, optional
        Column in df to group the respondents by (e.g. "age_group"), by
        default None. Each group gets its own subplot.

    Returns
    -------
    go.Figure
        Horizontal 100% stacked bar plot, one bar per item, one subplot per
        group

    Raises
    ------
    ValueError
        Raises if the question does not have type "likert"
        Raises if an answer is not in LIKERT_LEVELS
        Raises if group_by is not a column of df
    """
    _check_type(codebook, question, "likert")
    stem, data = _grid_counts(
        df, codebook, question, LIKERT_LEVELS, group_by, group_in_label=False
    )
    title = stem if title is None else title
    return _stacked_bar(data, title, LIKERT_COLORS, diverging=False, subplots=True)


def plot_agreement(
    df: pd.DataFrame,
    codebook: pd.DataFrame,
    question: str,
    title: str | None = None,
    group_by: str | None = None,
) -> go.Figure:
    """Plot the answers of an agreement question as diverging stacked bars.

    One bar per item, centred on the neutral answer: disagree (red) left of
    zero, agree (blue) right of zero.

    Parameters
    ----------
    df : pd.DataFrame
        Survey responses
    codebook : pd.DataFrame
        Codebook from build_codebook()
    question : str
        Question id (e.g. "likert4c") or response column (e.g. "likert4c[1]_0")
    title : str | None, optional
        Plot title, by default the question text that the items share
    group_by : str | None, optional
        Column in df to group the respondents by (e.g. "age_group"), by
        default None. Each item gets one bar per group.

    Returns
    -------
    go.Figure
        Horizontal diverging stacked bar plot, one bar per item (and group)

    Raises
    ------
    ValueError
        Raises if the question does not have type "agreement"
        Raises if an answer is not in AGREEMENT_LEVELS
        Raises if group_by is not a column of df
    """
    _check_type(codebook, question, "agreement")
    stem, data = _grid_counts(df, codebook, question, AGREEMENT_LEVELS, group_by)
    title = stem if title is None else title
    return _stacked_bar(data, title, AGREEMENT_COLORS, diverging=True)


def plot_likert2(
    df: pd.DataFrame,
    codebook: pd.DataFrame,
    title: str = "Actual and desired time per activity",
    group_by: str | None = None,
) -> go.Figure:
    """Plot the actual (likert0) and desired (likert1) time shares back to back.

    One row per activity. Actual time runs from zero to the left, desired
    time from zero to the right. On both sides "0% (None at all)" starts at
    zero and "100% (All my time)" ends at the outside.

    Parameters
    ----------
    df : pd.DataFrame
        Survey responses
    codebook : pd.DataFrame
        Codebook from build_codebook()
    title : str, optional
        Plot title, by default "Actual and desired time per activity"
    group_by : str | None, optional
        Column in df to group the respondents by (e.g. "age_group"), by
        default None. Each group gets its own subplot.

    Returns
    -------
    go.Figure
        Horizontal back-to-back stacked bar plot, one row per activity, one
        subplot per group. The row labels give the respondents as
        (n=actual | desired).

    Raises
    ------
    ValueError
        Raises if likert0 or likert1 does not have type "likert"
        Raises if likert0 and likert1 do not have the same number of items
        Raises if group_by is not a column of df
    """
    _check_type(codebook, LIKERT_ACTUAL, "likert")
    _check_type(codebook, LIKERT_DESIRED, "likert")
    _, actual = _grid_counts(
        df, codebook, LIKERT_ACTUAL, LIKERT_LEVELS, group_by, group_in_label=False
    )
    _, desired = _grid_counts(
        df, codebook, LIKERT_DESIRED, LIKERT_LEVELS, group_by, group_in_label=False
    )
    rows_actual = actual.drop_duplicates("row")
    rows_desired = desired.drop_duplicates("row")
    if len(rows_actual) != len(rows_desired):
        raise ValueError(
            f"{LIKERT_ACTUAL} and {LIKERT_DESIRED} must have the same items."
        )
    y_labels = [
        _label_with_n(label, f"n={n_actual} | {n_desired}")
        for label, n_actual, n_desired in zip(
            rows_actual["label"],
            rows_actual["n_respondents"],
            rows_desired["n_respondents"],
            strict=True,
        )
    ]

    groups = _group_names(actual)
    fig = _new_figure(groups)
    sides = [(actual, -1.0, "Actual time"), (desired, 1.0, "Desired time")]
    for subplot, group in enumerate(groups, start=1):
        for data, share, side in sides:
            group_data = data[data["group"] == group]
            for level in LIKERT_LEVELS:
                segment = group_data[group_data["answer"] == level]
                _add_segment(
                    fig,
                    segment,
                    [y_labels[row] for row in segment["row"]],
                    level,
                    share,
                    LIKERT_COLORS,
                    showlegend=share < 0 and subplot == 1,
                    hover_prefix=f"{side}, ",
                    row=subplot,
                )
    grouped = any(groups)
    plot_height = _stacked_layout(
        fig,
        title,
        DIVERGING_XAXIS,
        len(y_labels) // len(groups),
        len(groups),
        top=30 if grouped else 0,
    )
    # the side headers sit above the title of the first subplot
    for share, side in [(-1.0, "Actual time"), (1.0, "Desired time")]:
        fig.add_annotation(
            x=50 * share,
            y=1 + (30 / plot_height if grouped else 0),
            xref="x",
            yref="paper",
            yanchor="bottom",
            text=f"<b>{side}</b>",
            showarrow=False,
        )
    return fig
