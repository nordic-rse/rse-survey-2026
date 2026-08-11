"""Book layer: artifacts → the Quarto site under ``rse-book/``.

Stage 6 of the pipeline. Writes chapters and front/back matter, prunes pages
for questions no longer in ``book.yml``, and republishes artifacts into the
rendered output so stale images cannot survive a rebuild.
"""

from rse_survey.book.chapters import chapter_body, germany_index, recoding_appendix
from rse_survey.book.quarto_yml import prune_quarto_yml, remove_orphan_chapters
from rse_survey.book.sync import publish_artifacts_to_book, sync_quarto_book

__all__ = [
    "chapter_body",
    "germany_index",
    "prune_quarto_yml",
    "publish_artifacts_to_book",
    "recoding_appendix",
    "remove_orphan_chapters",
    "sync_quarto_book",
]
