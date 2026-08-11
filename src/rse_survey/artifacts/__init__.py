"""Artifact layer: generic writers for the files the Quarto book includes.

Stage 5 of the pipeline. Deliberately question-agnostic — these are output
primitives (a directory, a markdown table, a bar chart). Anything that knows
what a *select question* is belongs with its analysis task instead.
"""

from rse_survey.artifacts.layout import question_artifact_dir, write_meta
from rse_survey.artifacts.tables import df_to_markdown, write_table_artifact

__all__ = [
    "df_to_markdown",
    "question_artifact_dir",
    "write_meta",
    "write_table_artifact",
]
