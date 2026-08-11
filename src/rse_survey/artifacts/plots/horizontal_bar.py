"""Horizontal bar charts for categorical survey summaries."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from plotnine import (
    aes,
    coord_flip,
    element_text,
    facet_wrap,
    geom_col,
    geom_text,
    ggplot,
    labs,
    scale_fill_manual,
    scale_y_continuous,
    theme,
)

from rse_survey.artifacts.plots.style import category_fill_map, theme_rse


def _pct_axis():
    return scale_y_continuous(
        limits=(0, 112),
        breaks=list(range(0, 101, 20)),
        labels=lambda br: [str(int(b)) if b <= 100 else "" for b in br],
        expand=(0, 0),
    )


def _drop_zero_n(df: pd.DataFrame, n_col: str) -> pd.DataFrame:
    """Omit categories with n=0 from bar charts."""
    n = pd.to_numeric(df[n_col], errors="coerce").fillna(0)
    return df.loc[n > 0].copy()


def _category_levels_for_plot(
    present: list[str],
    *,
    pct_order_ascending: list[str],
    category_order: list[str] | None,
) -> list[str]:
    """Resolve bar-axis category levels.

    With ``coord_flip``, the first level is at the *bottom*. Default frequency
    charts put low pct at the bottom. Configured ``category_order`` is listed
    top→bottom in tables, so levels are reversed for the plot.
    """
    if not category_order:
        return pct_order_ascending
    order = [str(c) for c in category_order]
    present_set = set(present)
    configured = [c for c in order if c in present_set]
    extras = [c for c in pct_order_ascending if c not in set(configured)]
    # Bottom → top on the flipped axis
    return list(reversed(configured + extras))


def horizontal_bar_chart(
    summary: pd.DataFrame,
    *,
    category_col: str = "category",
    pct_col: str = "pct",
    n_col: str = "n",
    title: str | None = None,
    subtitle: str | None = None,
    xlab: str = "Percent of respondents",
    ylab: str = "",
    n_total: int | None = None,
    category_order: list[str] | None = None,
    fill_map: dict[str, str] | None = None,
):
    """Build a horizontal bar chart with percent (0–100) on the x-axis.

    Bar ends are annotated with ``(n=…)``. When ``n_total`` is set, it is
    appended to the title as ``(N=…)``. Categories with ``n=0`` are omitted.

    Pass ``fill_map`` (category → color) to keep colors aligned across plots
    (e.g. one chart per country).
    """
    if summary.empty:
        raise ValueError("Cannot plot an empty summary table")
    needed = {category_col, pct_col, n_col}
    missing = needed - set(summary.columns)
    if missing:
        raise KeyError(f"summary missing columns: {sorted(missing)}")

    df = _drop_zero_n(summary[[category_col, pct_col, n_col]].copy(), n_col)
    if df.empty:
        raise ValueError("Cannot plot: all categories have n=0")
    df[category_col] = df[category_col].astype(str)
    df[pct_col] = pd.to_numeric(df[pct_col], errors="coerce").fillna(0.0).clip(0, 100)
    by_pct = df.sort_values(pct_col, ascending=True, kind="mergesort")[
        category_col
    ].tolist()
    levels = _category_levels_for_plot(
        df[category_col].tolist(),
        pct_order_ascending=by_pct,
        category_order=category_order,
    )
    df[category_col] = pd.Categorical(df[category_col], categories=levels, ordered=True)
    df["n_label"] = df[n_col].map(lambda n: f"(n={int(n)})")
    if fill_map is None:
        fills = category_fill_map(levels)
    else:
        fills = {c: fill_map[c] for c in levels if c in fill_map}
        missing_fills = [c for c in levels if c not in fills]
        if missing_fills:
            fills.update(category_fill_map(missing_fills))
    n_cat = len(levels)
    height = max(3.5, min(0.35 * n_cat + 1.5, 14))

    plot_title = title
    if title is not None and n_total is not None:
        plot_title = f"{title} (N={int(n_total)})"

    return (
        ggplot(df, aes(x=category_col, y=pct_col, fill=category_col))
        + geom_col(width=0.7)
        + geom_text(
            aes(label="n_label"),
            ha="left",
            va="center",
            nudge_y=1.5,
            size=8,
            color="#212121",
        )
        + coord_flip()
        + scale_fill_manual(values=fills)
        + _pct_axis()
        + labs(title=plot_title, subtitle=subtitle, x=ylab, y=xlab)
        + theme_rse()
        + theme(figure_size=(8, height))
    )


def horizontal_bar_chart_grouped(
    summary: pd.DataFrame,
    *,
    group_col: str = "age_group",
    category_col: str = "category",
    pct_col: str = "pct",
    n_col: str = "n",
    title: str | None = None,
    subtitle: str | None = None,
    xlab: str = "Percent of respondents",
    ylab: str = "",
    n_total: int | None = None,
    group_levels: list[str] | None = None,
    category_order: list[str] | None = None,
):
    """Horizontal percent bars faceted by a grouping variable (e.g. age_group).

    Each facet mirrors ``horizontal_bar_chart``; answer colors stay consistent
    across facets via shared semantic/palette fills. Categories with ``n=0``
    are omitted from the data and from each facet axis (``scales='free_y'``).
    """
    if summary.empty:
        raise ValueError("Cannot plot an empty summary table")
    needed = {group_col, category_col, pct_col, n_col}
    missing = needed - set(summary.columns)
    if missing:
        raise KeyError(f"summary missing columns: {sorted(missing)}")

    df = _drop_zero_n(summary[[group_col, category_col, pct_col, n_col]].copy(), n_col)
    if df.empty:
        raise ValueError("Cannot plot: all categories have n=0")
    df[group_col] = df[group_col].astype(str)
    df[category_col] = df[category_col].astype(str)
    df[pct_col] = pd.to_numeric(df[pct_col], errors="coerce").fillna(0.0).clip(0, 100)
    df["n_label"] = df[n_col].map(lambda n: f"(n={int(n)})")

    if group_levels is None:
        group_levels = list(dict.fromkeys(df[group_col].tolist()))
    else:
        group_levels = [str(g) for g in group_levels]
    present = [g for g in group_levels if g in set(df[group_col])]
    if not present:
        present = list(dict.fromkeys(df[group_col].tolist()))
    df[group_col] = pd.Categorical(df[group_col], categories=present, ordered=True)

    by_pct = (
        df.groupby(category_col, observed=True)[pct_col]
        .mean()
        .sort_values(ascending=True)
        .index.astype(str)
        .tolist()
    )
    cat_order = _category_levels_for_plot(
        df[category_col].astype(str).unique().tolist(),
        pct_order_ascending=by_pct,
        category_order=category_order,
    )
    df[category_col] = pd.Categorical(
        df[category_col], categories=cat_order, ordered=True
    )
    fills = category_fill_map(cat_order)

    n_cat = max(len(cat_order), 1)
    n_groups = len(present)
    height = max(4.0, min(0.32 * n_cat * n_groups + 1.8, 22))

    plot_title = title
    if title is not None and n_total is not None:
        plot_title = f"{title} (N={int(n_total)})"

    return (
        ggplot(df, aes(x=category_col, y=pct_col, fill=category_col))
        + geom_col(width=0.7)
        + geom_text(
            aes(label="n_label"),
            ha="left",
            va="center",
            nudge_y=1.5,
            size=7,
            color="#212121",
        )
        + coord_flip()
        # Free the category axis per facet so unused labels (n=0) are not shown.
        # After coord_flip the discrete axis is y.
        + facet_wrap(f"~{group_col}", ncol=1, scales="free_y")
        + scale_fill_manual(values=fills)
        + _pct_axis()
        + labs(title=plot_title, subtitle=subtitle, x=ylab, y=xlab)
        + theme_rse()
        + theme(
            figure_size=(8, height),
            strip_text=element_text(weight="bold", size=10),
        )
    )


def save_horizontal_bar(
    summary: pd.DataFrame,
    path: Path | str,
    *,
    category_col: str = "category",
    pct_col: str = "pct",
    n_col: str = "n",
    title: str | None = None,
    subtitle: str | None = None,
    xlab: str = "Percent of respondents",
    ylab: str = "",
    n_total: int | None = None,
    category_order: list[str] | None = None,
    fill_map: dict[str, str] | None = None,
    dpi: int = 150,
) -> Path:
    """Render and save a horizontal percent bar chart; return the output path."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if n_total is None and hasattr(summary, "attrs"):
        n_total = summary.attrs.get("N")
    plot = horizontal_bar_chart(
        summary,
        category_col=category_col,
        pct_col=pct_col,
        n_col=n_col,
        title=title,
        subtitle=subtitle,
        xlab=xlab,
        ylab=ylab,
        n_total=n_total,
        category_order=category_order,
        fill_map=fill_map,
    )
    plot.save(out, dpi=dpi, verbose=False)
    return out


def save_horizontal_bar_grouped(
    summary: pd.DataFrame,
    path: Path | str,
    *,
    group_col: str = "age_group",
    category_col: str = "category",
    pct_col: str = "pct",
    n_col: str = "n",
    title: str | None = None,
    subtitle: str | None = None,
    xlab: str = "Percent of respondents",
    ylab: str = "",
    n_total: int | None = None,
    group_levels: list[str] | None = None,
    category_order: list[str] | None = None,
    dpi: int = 150,
) -> Path:
    """Render and save a grouped (faceted) horizontal percent bar chart."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if n_total is None and hasattr(summary, "attrs"):
        n_total = summary.attrs.get("N")
    plot = horizontal_bar_chart_grouped(
        summary,
        group_col=group_col,
        category_col=category_col,
        pct_col=pct_col,
        n_col=n_col,
        title=title,
        subtitle=subtitle,
        xlab=xlab,
        ylab=ylab,
        n_total=n_total,
        group_levels=group_levels,
        category_order=category_order,
    )
    plot.save(out, dpi=dpi, verbose=False)
    return out
