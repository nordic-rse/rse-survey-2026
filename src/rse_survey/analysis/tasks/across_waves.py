"""Across-waves view (stub for first test — skipped when waves unset)."""

from __future__ import annotations

from rse_survey.analysis.context import AnalysisContext, TaskResult
from rse_survey.analysis.registry import register


@register
class AcrossWavesTask:
    name = "across_waves"

    def run(self, ctx: AnalysisContext) -> TaskResult:
        if not ctx.book.waves:
            return TaskResult(
                task_name=self.name,
                question_id=ctx.question.question_id,
                skipped=True,
                skip_reason="waves not configured in book.yml (first test: single year)",
            )
        return TaskResult(
            task_name=self.name,
            question_id=ctx.question.question_id,
            skipped=True,
            skip_reason="across_waves not implemented yet",
        )
