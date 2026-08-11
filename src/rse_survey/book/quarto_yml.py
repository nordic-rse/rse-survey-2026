"""Keep ``_quarto.yml`` and ``chapters/`` in step with ``book.yml``.

Questions removed from the config must lose their chapter file *and* their
listing, or Quarto fails the render on a missing input.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_CHAPTER_QMD_LINE = re.compile(r"^(\s*-\s+)chapters/([^/\s]+)\.qmd\s*$")


def prune_quarto_yml(quarto_yml: Path, book_ids: set[str]) -> list[str]:
    """Keep only ``chapters/<qid>.qmd`` entries present in ``book.yml``.

    Edits the file in place (preserves comments / layout). Drops empty
    parts. Returns removed question ids.
    """
    lines = quarto_yml.read_text(encoding="utf-8").splitlines(keepends=True)
    removed: list[str] = []
    filtered: list[str] = []
    for line in lines:
        m = _CHAPTER_QMD_LINE.match(line.rstrip("\n"))
        if m and m.group(2) not in book_ids:
            removed.append(m.group(2))
            continue
        filtered.append(line)

    # Drop `- part:` blocks whose nested chapter list has no remaining entries.
    data = yaml.safe_load("".join(filtered))
    empty_parts: set[str] = set()
    for entry in data.get("book", {}).get("chapters", []) or []:
        if not isinstance(entry, dict) or "part" not in entry:
            continue
        chs = entry.get("chapters") or []
        if not chs:
            empty_parts.add(str(entry["part"]))

    if empty_parts:
        final: list[str] = []
        i = 0
        part_re = re.compile(r'^(\s*)-\s+part:\s*[\'"]?(.*?)[\'"]?\s*$')
        while i < len(filtered):
            m = part_re.match(filtered[i].rstrip("\n"))
            if not m:
                final.append(filtered[i])
                i += 1
                continue
            part_name = m.group(2)
            block = [filtered[i]]
            i += 1
            while i < len(filtered):
                nxt = filtered[i]
                # Next sibling part or a book-level key (appendices, …)
                if part_re.match(nxt.rstrip("\n")):
                    break
                if re.match(r"^  [A-Za-z]", nxt) and not nxt.lstrip().startswith("-"):
                    break
                block.append(nxt)
                i += 1
            if part_name not in empty_parts:
                final.extend(block)
        filtered = final

    quarto_yml.write_text("".join(filtered), encoding="utf-8")
    return removed


def remove_orphan_chapters(chapters_dir: Path, book_ids: set[str]) -> list[str]:
    """Delete ``chapters/<qid>.qmd`` files not listed in ``book.yml``."""
    removed: list[str] = []
    for path in sorted(chapters_dir.glob("*.qmd")):
        if path.stem in book_ids:
            continue
        path.unlink()
        removed.append(path.stem)
    return removed
