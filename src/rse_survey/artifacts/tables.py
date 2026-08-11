"""Helpers for writing markdown/CSV artifacts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def df_to_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._\n"
    cols = [str(c) for c in df.columns]
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in df.iterrows():
        cells = [str(row[c]).replace("|", "\\|") for c in df.columns]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def write_table_artifact(
    directory: Path,
    stem: str,
    df: pd.DataFrame,
    *,
    heading: str | None = None,
) -> dict[str, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    md_path = directory / f"{stem}.md"
    csv_path = directory / f"{stem}.csv"
    body = df_to_markdown(df)
    if heading:
        body = f"### {heading}\n\n{body}"
    md_path.write_text(body, encoding="utf-8")
    df.to_csv(csv_path, index=False)
    return {"md": md_path, "csv": csv_path}
