"""Registry of analysis tasks.

A task is anything with ``name`` and ``run(ctx) -> TaskResult``. Register it
with ``@register`` and import it from ``ensure_builtin_tasks_loaded`` so the
decorator actually runs.
"""

from __future__ import annotations

from typing import Protocol

from rse_survey.analysis.context import AnalysisContext, TaskResult


class AnalysisTask(Protocol):
    name: str

    def run(self, ctx: AnalysisContext) -> TaskResult: ...


_REGISTRY: dict[str, AnalysisTask] = {}


def register(task: AnalysisTask | type) -> AnalysisTask | type:
    """Register a task instance, or a class (instantiated with no args)."""
    obj: AnalysisTask
    if isinstance(task, type):
        obj = task()  # type: ignore[call-arg]
    else:
        obj = task
    _REGISTRY[obj.name] = obj
    return task


def get_task(name: str) -> AnalysisTask:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown analysis task {name!r}. Known: {sorted(_REGISTRY)}")
    return _REGISTRY[name]


def list_tasks() -> list[str]:
    return sorted(_REGISTRY)


def ensure_builtin_tasks_loaded() -> None:
    """Import task modules so @register side effects run."""
    from rse_survey.analysis.tasks import (  # noqa: F401
        across_waves,
        select_questions,
        validate_inputs,
    )
