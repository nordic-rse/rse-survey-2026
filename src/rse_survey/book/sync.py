"""Write the whole book skeleton from ``book.yml`` and the artifact tree."""

from __future__ import annotations

import shutil
from pathlib import Path

from rse_survey.book.chapters import chapter_body, germany_index, recoding_appendix
from rse_survey.book.quarto_yml import prune_quarto_yml, remove_orphan_chapters
from rse_survey.config.book_config import load_book_config
from rse_survey.config.paths import REPO_ROOT, artifacts_root


def publish_artifacts_to_book(root: Path) -> int:
    """Overwrite ``_book/_artifacts`` from source ``_artifacts``.

    Quarto often leaves stale PNGs in the book output when files already
    exist; this copies source artifacts so rendered pages pick up updates.
    """
    src = artifacts_root(root)
    dest = root / "rse-book" / "_book" / "_artifacts"
    if not src.is_dir():
        return 0
    n = 0
    for path in src.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(src)
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, out)
        n += 1
    return n


def sync_quarto_book(
    book_path: str | None = None, *, repo_root: Path | None = None
) -> dict:
    root = repo_root or REPO_ROOT
    book = load_book_config(book_path, repo_root=root)
    chapters_dir = root / "rse-book" / "chapters"
    artifacts_dir = artifacts_root(root)
    chapters_dir.mkdir(parents=True, exist_ok=True)
    book_ids = set(book.questions)

    written = []
    appendix_ids = []
    for qid, q in book.questions.items():
        art_dir = artifacts_dir / qid
        stems = {
            p.stem for p in art_dir.glob("*.md") if p.is_file() and p.stem != "heading"
        }
        has_other = (art_dir / "other_by_country.md").exists()
        path = chapters_dir / f"{qid}.qmd"
        path.write_text(
            chapter_body(
                qid,
                q.title or qid,
                has_other_by_country=has_other,
                artifact_stems=stems,
            ),
            encoding="utf-8",
        )
        written.append(str(path.relative_to(root)))
        if q.appendix:
            appendix_ids.append(qid)

    orphans = remove_orphan_chapters(chapters_dir, book_ids)
    quarto_yml = root / "rse-book" / "_quarto.yml"
    pruned = prune_quarto_yml(quarto_yml, book_ids) if quarto_yml.exists() else []

    (root / "rse-book" / "index.qmd").write_text(germany_index(), encoding="utf-8")

    recoding_path = root / "rse-book" / "appendices" / "recoding.qmd"
    recoding_path.parent.mkdir(parents=True, exist_ok=True)
    recoding_path.write_text(recoding_appendix(appendix_ids, root), encoding="utf-8")

    user_guide = root / "rse-book" / "about" / "user-guide.qmd"
    user_guide.parent.mkdir(parents=True, exist_ok=True)
    user_guide.write_text(
        '---\ntitle: "User guide"\n---\n\n'
        "Configure the report in `config/book.yml`, then run "
        "`rse-survey build-artifacts`, `rse-survey sync-quarto`, "
        "and `quarto render`.\n"
        "See the repository [README](../../README.md) for install steps.\n",
        encoding="utf-8",
    )

    # Methodology: strip R chunks if present — short Python-era note
    methodology = root / "rse-book" / "appendices" / "methodology.qmd"
    methodology.write_text(
        '---\ntitle: "Methodology"\n---\n\n'
        "# Methodology\n\n"
        "Analyses are produced by the `rse-survey` Python package "
        "(`focus`, `by_age`, `between_countries`). "
        "Free-text coding uses offline Hugging Face freezes under "
        "`_hf_freetext_cache/` when available. "
        "Quarto chapters include committed artifacts and do not re-run analysis.\n",
        encoding="utf-8",
    )

    n_published = publish_artifacts_to_book(root)

    return {
        "chapters_written": len(written),
        "chapters_removed": orphans,
        "quarto_yml_pruned": pruned,
        "appendix_questions": appendix_ids,
        "artifacts_published": n_published,
    }
