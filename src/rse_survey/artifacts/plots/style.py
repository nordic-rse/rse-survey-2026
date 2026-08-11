"""Shared plotting style for survey analysis figures."""

from __future__ import annotations

from plotnine import (
    element_blank,
    element_line,
    element_rect,
    element_text,
    theme,
    theme_minimal,
)

# Semantic fills for common select / yes-no labels (case-sensitive keys as in data)
SEMANTIC_CATEGORY_COLORS: dict[str, str] = {
    "True": "#2E7D32",
    "False": "#C62828",
    "Yes": "#2E7D32",
    "No": "#C62828",
    "YES": "#2E7D32",
    "NO": "#C62828",
    "true": "#2E7D32",
    "false": "#C62828",
    "yes": "#2E7D32",
    "no": "#C62828",
    "I do not know": "#757575",
    "I don't know": "#757575",
    "Don't know": "#757575",
    "Do not know": "#757575",
    "Prefer not to say": "#9E9E9E",
    "Not applicable": "#BDBDBD",
    "N/A": "#BDBDBD",
}

# Fallback palette when a category has no semantic color
DEFAULT_CATEGORY_PALETTE: tuple[str, ...] = (
    "#1565C0",
    "#6A1B9A",
    "#00838F",
    "#EF6C00",
    "#4527A0",
    "#00695C",
    "#AD1457",
    "#37474F",
)

DEFAULT_SINGLE_FILL = "#1565C0"
PLOT_BACKGROUND = "#FFFFFF"
GRID_COLOR = "#E0E0E0"
TEXT_COLOR = "#212121"


def category_fill_map(categories: list[str]) -> dict[str, str]:
    """Map category labels → fill colors (semantic first, then palette)."""
    mapping: dict[str, str] = {}
    palette_i = 0
    for raw in categories:
        label = str(raw)
        if label in SEMANTIC_CATEGORY_COLORS:
            mapping[label] = SEMANTIC_CATEGORY_COLORS[label]
            continue
        # case-insensitive semantic match
        matched = next(
            (
                SEMANTIC_CATEGORY_COLORS[k]
                for k in SEMANTIC_CATEGORY_COLORS
                if k.lower() == label.lower()
            ),
            None,
        )
        if matched is not None:
            mapping[label] = matched
            continue
        mapping[label] = DEFAULT_CATEGORY_PALETTE[
            palette_i % len(DEFAULT_CATEGORY_PALETTE)
        ]
        palette_i += 1
    return mapping


def theme_rse():
    """Base theme for RSE survey figures."""
    return theme_minimal(base_size=11) + theme(
        plot_background=element_rect(fill=PLOT_BACKGROUND, color=PLOT_BACKGROUND),
        panel_background=element_rect(fill=PLOT_BACKGROUND, color=PLOT_BACKGROUND),
        panel_grid_major_y=element_blank(),
        panel_grid_minor=element_blank(),
        panel_grid_major_x=element_line(color=GRID_COLOR, size=0.4),
        axis_title=element_text(color=TEXT_COLOR),
        axis_text=element_text(color=TEXT_COLOR),
        plot_title=element_text(color=TEXT_COLOR, weight="bold", size=12),
        plot_subtitle=element_text(color=TEXT_COLOR, size=10),
        legend_position="none",
        figure_size=(8, 4.5),
    )
