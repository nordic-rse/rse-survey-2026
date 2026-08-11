"""Generate the Quarto pages: one thin chapter per question, plus front/back matter.

Chapters only ``{{< include >}}`` committed artifacts — no analysis runs during
``quarto render``.
"""

from __future__ import annotations

from pathlib import Path

VIEW_FILES = (
    ("focus", "Focus"),
    ("by_age", "By age group"),
    ("between_countries", "Between countries"),
    ("across_waves", "Across survey waves"),
)


def chapter_body(
    question_id: str,
    title: str,
    *,
    has_other_by_country: bool,
    artifact_stems: set[str],
) -> str:
    safe_title = title.replace('"', "'")
    lines = [
        "---",
        f'title: "{safe_title}"',
        f"question_id: {question_id}",
        "---",
        "",
        f"## {safe_title}",
        "",
        f"Artifacts for `{question_id}` (from `rse-survey build-artifacts`).",
        "",
    ]
    for stem, heading in VIEW_FILES:
        if stem not in artifact_stems:
            continue
        lines.append(f"### {heading}")
        lines.append("")
        lines.append(f"{{{{< include ../_artifacts/{question_id}/{stem}.md >}}}}")
        lines.append("")
    if has_other_by_country:
        lines.append("### Other answers")
        lines.append("")
        lines.append(
            f"{{{{< include ../_artifacts/{question_id}/other_by_country.md >}}}}"
        )
        lines.append("")
    return "\n".join(lines)


def recoding_appendix(question_ids: list[str], root: Path) -> str:
    lines = [
        "# Recoding {#sec-appendix-recoding}",
        "",
        "Token → category tables for free-text questions with `appendix: true`.",
        "",
    ]
    for qid in question_ids:
        path = root / "rse-book" / "_artifacts" / qid / "token_allocation.md"
        if not path.exists():
            continue
        lines.append(f"## `{qid}`")
        lines.append("")
        lines.append(f"{{{{< include ../_artifacts/{qid}/token_allocation.md >}}}}")
        lines.append("")
    return "\n".join(lines)


def germany_index() -> str:
    return """---
title: "International RSE Survey 2026 — Germany focus"
---

# Germany focus {.unnumbered}

This book presents analysis artifacts for the **Germany** focus in
`config/book.yml`, with between-country comparisons to the Netherlands,
United Kingdom, and United States (local 2026 data).

```bash
rse-survey validate --config config/book.yml
rse-survey build-artifacts --config config/book.yml
rse-survey sync-quarto --config config/book.yml
quarto render
```

Wave / longitudinal views are disabled in this first test build.
"""
