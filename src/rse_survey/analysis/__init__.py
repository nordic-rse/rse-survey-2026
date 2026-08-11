"""Analysis layer: the clean long table → summary tables and artifacts.

Stage 4 of the pipeline. ``tasks/`` holds one module (or subpackage) per
conceptual analysis; ``summarize/`` holds what those tasks share; ``build``
runs whatever a question configures.
"""

from rse_survey.analysis.build import build_question_artifacts
from rse_survey.analysis.context import (
    AnalysisContext,
    TaskResult,
    build_context,
    load_frames,
)
from rse_survey.analysis.registry import (
    ensure_builtin_tasks_loaded,
    get_task,
    list_tasks,
    register,
)

__all__ = [
    "AnalysisContext",
    "TaskResult",
    "build_context",
    "build_question_artifacts",
    "ensure_builtin_tasks_loaded",
    "get_task",
    "list_tasks",
    "load_frames",
    "register",
]
