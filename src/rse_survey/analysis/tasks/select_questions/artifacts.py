"""Write the files a select-question chapter includes.

Three shapes, picked by the task: one pooled table+chart, one per sub-item
(likert arrays), or one per country (categorical_with_other comparisons).
Each writes a CSV always, and a markdown include that honours ``presentation``.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pandas as pd

from rse_survey.analysis.tasks.select_questions.grouping import (
    GroupingSpec,
    filter_item,
    item_slug,
    resolve_grouping,
)
from rse_survey.analysis.tasks.select_questions.summary import (
    build_summary_table,
    total_respondents,
)
from rse_survey.artifacts.plots import (
    save_horizontal_bar,
    save_horizontal_bar_grouped,
)
from rse_survey.artifacts.plots.style import category_fill_map
from rse_survey.artifacts.tables import df_to_markdown
from rse_survey.config.book_config import resolve_presentation


def write_other_by_country_artifacts(
    out_dir: Path,
    by_country: dict[str, list[str]],
    *,
    country_order: list[str] | None = None,
) -> dict[str, Path]:
    """Write ``other_by_country.json`` and ``.md`` (lists only, no counts)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    order = list(country_order or [])
    keys = [c for c in order if c in by_country] + [
        c for c in by_country if c not in order
    ]
    payload = {c: by_country[c] for c in keys}
    files: dict[str, Path] = {}
    json_path = out_dir / "other_by_country.json"
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    files["json"] = json_path

    # Heading comes from the Quarto chapter ("### Other answers"); this
    # include only has per-country lists.
    md_parts: list[str] = []
    if not payload:
        md_parts.append("_No free-text Other answers._\n")
    else:
        for country in keys:
            labels = payload[country]
            md_parts.append(f"#### {country}\n")
            for label in labels:
                md_parts.append(f"- {label}")
            md_parts.append("")
    md_path = out_dir / "other_by_country.md"
    md_path.write_text("\n".join(md_parts).rstrip() + "\n", encoding="utf-8")
    files["md"] = md_path
    return files


def _country_slug(name: str) -> str:
    slug = re.sub(r"[^\w]+", "_", str(name).strip(), flags=re.UNICODE)
    return slug.strip("_") or "country"


def write_artifacts(
    *,
    summary: pd.DataFrame,
    out_dir: Path,
    question_id: str,
    title: str,
    focus_label: str,
    grouping_variable: str | None = None,
    group_levels: list[str] | None = None,
    presentation: str = "both",
    category_order: list[str] | None = None,
    facet_col: str | None = None,
) -> dict[str, Path]:
    """Write select-question artifacts according to ``presentation``.

    ``presentation``: ``table`` | ``graphic`` | ``both`` (from book.yml).
    CSV is always written. The markdown include follows presentation.
    ``facet_col`` overrides the grouping's own column when the chart is
    faceted by something else (sub-item rather than age/country).
    """
    mode = resolve_presentation(presentation)
    spec = resolve_grouping(grouping_variable)
    facet = spec.group_col if facet_col is None else facet_col
    file_stem = spec.stem
    n_total = total_respondents(summary, facet)

    heading = (
        f"{title} ({focus_label}, N={n_total})"
        if spec.scope == "focus"
        else f"{title} (N={n_total})"
    )
    if spec.group_col is None:
        subtitle = f"Focus: {focus_label}"
    elif spec.key == "by_age":
        subtitle = "by age group"
    else:
        subtitle = "between countries"

    out_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, Path] = {}
    csv_path = out_dir / f"{file_stem}.csv"
    summary.to_csv(csv_path, index=False)
    files["csv"] = csv_path

    md_parts: list[str] = [f"### {heading}\n"]
    if mode in {"table", "both"}:
        md_parts.append(df_to_markdown(summary))

    png_path = out_dir / f"{file_stem}.png"
    if mode in {"graphic", "both"}:
        if facet is None:
            save_horizontal_bar(
                summary,
                png_path,
                title=title,
                subtitle=subtitle,
                xlab="Percent of respondents",
                n_total=n_total,
                category_order=category_order,
            )
        else:
            save_horizontal_bar_grouped(
                summary,
                png_path,
                group_col=facet,
                title=title,
                subtitle=subtitle,
                xlab="Percent of respondents",
                n_total=n_total,
                group_levels=group_levels,
                category_order=category_order,
            )
        files["png"] = png_path
        digest = hashlib.md5(png_path.read_bytes()).hexdigest()[:10]
        rel_img = f"../_artifacts/{question_id}/{file_stem}.png?v={digest}"
        md_parts.append(f"![{title} (N={n_total})]({rel_img})\n")
    elif png_path.exists():
        png_path.unlink()

    md_path = out_dir / f"{file_stem}.md"
    md_path.write_text("\n".join(md_parts).rstrip() + "\n", encoding="utf-8")
    files["md"] = md_path
    return files


def write_per_item_artifacts(
    *,
    frame: pd.DataFrame,
    out_dir: Path,
    question_id: str,
    title: str,
    items: list[str],
    spec: GroupingSpec,
    group_levels: list[str] | None,
    presentation: str = "both",
    category_order: list[str] | None = None,
) -> dict[str, Path]:
    """One table + chart per sub-item, faceted by age/country; one md.

    Used for multi-item likert arrays under ``by_age`` /
    ``between_countries``, where item × group × answer is one dimension too
    many for a single chart.
    """
    mode = resolve_presentation(presentation)
    out_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, Path] = {}
    label = "by age group" if spec.key == "by_age" else "between countries"
    md_parts: list[str] = [f"### {title} — {label}\n"]
    combined_rows: list[pd.DataFrame] = []

    # Drop the stale pooled chart written before items were split out.
    legacy_png = out_dir / f"{spec.stem}.png"
    if legacy_png.exists():
        legacy_png.unlink()

    for index, item in enumerate(items):
        item_frame = filter_item(frame, item)
        if item_frame.empty:
            continue
        summary = build_summary_table(
            item_frame,
            question_id,
            grouping_variable=spec.key,
            group_levels=group_levels,
            category_order=category_order,
        )
        if summary.empty:
            continue
        n_total = total_respondents(summary, spec.group_col)
        slug = item_slug(item, index)
        stem = f"{spec.stem}_{slug}"

        summary_out = summary.copy()
        summary_out.insert(0, "item", item)
        combined_rows.append(summary_out)

        csv_path = out_dir / f"{stem}.csv"
        summary.to_csv(csv_path, index=False)
        files[f"csv_{slug}"] = csv_path

        md_parts.append(f"#### {item} (N={n_total})\n")
        if mode in {"table", "both"}:
            md_parts.append(df_to_markdown(summary))

        png_path = out_dir / f"{stem}.png"
        if mode in {"graphic", "both"}:
            save_horizontal_bar_grouped(
                summary,
                png_path,
                group_col=spec.group_col or "item",
                title=item,
                subtitle=f"{title} — {label}",
                xlab="Percent of respondents",
                n_total=n_total,
                group_levels=group_levels,
                category_order=category_order,
            )
            files[f"png_{slug}"] = png_path
            digest = hashlib.md5(png_path.read_bytes()).hexdigest()[:10]
            rel_img = f"../_artifacts/{question_id}/{stem}.png?v={digest}"
            md_parts.append(f"![{item} (N={n_total})]({rel_img})\n")
        elif png_path.exists():
            png_path.unlink()

    if not combined_rows:
        return {}

    combined = pd.concat(combined_rows, ignore_index=True)
    combined_path = out_dir / f"{spec.stem}.csv"
    combined.to_csv(combined_path, index=False)
    files["csv"] = combined_path

    md_path = out_dir / f"{spec.stem}.md"
    md_path.write_text("\n".join(md_parts).rstrip() + "\n", encoding="utf-8")
    files["md"] = md_path
    return files


def write_between_countries_separate_artifacts(
    *,
    frame: pd.DataFrame,
    out_dir: Path,
    question_id: str,
    title: str,
    country_levels: list[str],
    presentation: str = "both",
    category_order: list[str] | None = None,
) -> dict[str, Path]:
    """One closed-category table + bar chart per country; assemble one md."""
    mode = resolve_presentation(presentation)
    out_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, Path] = {}
    md_parts: list[str] = [f"### {title} — between countries\n"]
    combined_rows: list[pd.DataFrame] = []
    any_data = False

    # Drop stale grouped PNG from older builds
    legacy_png = out_dir / "between_countries.png"
    if legacy_png.exists():
        legacy_png.unlink()

    # Shared category → color map so the same answer keeps one color in every
    # country chart (palette assignment must not depend on which subset appears).
    if "value" in frame.columns and not frame.empty:
        freq = (
            frame["value"]
            .astype(str)
            .str.strip()
            .value_counts()
            .index.astype(str)
            .tolist()
        )
    else:
        freq = []
    if category_order:
        order = [str(c) for c in category_order]
        present = set(freq)
        shared_cats = [c for c in order if c in present] + [
            c for c in freq if c not in set(order)
        ]
    else:
        shared_cats = freq
    shared_fill_map = category_fill_map(shared_cats) if shared_cats else None

    for country in country_levels:
        country_frame = frame.loc[
            frame["country_group"].astype(str) == str(country)
        ].copy()
        if country_frame.empty:
            continue
        summary = build_summary_table(
            country_frame,
            question_id,
            grouping_variable="focus",
            category_order=category_order,
        )
        if summary.empty:
            continue
        any_data = True
        n_total = total_respondents(summary, None)
        slug = _country_slug(country)
        stem = f"between_countries_{slug}"

        summary_out = summary.copy()
        summary_out.insert(0, "country_group", country)
        combined_rows.append(summary_out)

        csv_path = out_dir / f"{stem}.csv"
        summary.to_csv(csv_path, index=False)
        files[f"csv_{slug}"] = csv_path

        md_parts.append(f"#### {country} (N={n_total})\n")
        if mode in {"table", "both"}:
            md_parts.append(df_to_markdown(summary))

        png_path = out_dir / f"{stem}.png"
        if mode in {"graphic", "both"}:
            save_horizontal_bar(
                summary,
                png_path,
                title=title,
                subtitle=country,
                xlab="Percent of respondents",
                n_total=n_total,
                category_order=category_order,
                fill_map=shared_fill_map,
            )
            files[f"png_{slug}"] = png_path
            digest = hashlib.md5(png_path.read_bytes()).hexdigest()[:10]
            rel_img = f"../_artifacts/{question_id}/{stem}.png?v={digest}"
            md_parts.append(f"![{title} — {country} (N={n_total})]({rel_img})\n")
        elif png_path.exists():
            png_path.unlink()

    if not any_data:
        return {}

    if combined_rows:
        combined = pd.concat(combined_rows, ignore_index=True)
        combined_path = out_dir / "between_countries.csv"
        combined.to_csv(combined_path, index=False)
        files["csv"] = combined_path

    md_path = out_dir / "between_countries.md"
    md_path.write_text("\n".join(md_parts).rstrip() + "\n", encoding="utf-8")
    files["md"] = md_path
    return files
