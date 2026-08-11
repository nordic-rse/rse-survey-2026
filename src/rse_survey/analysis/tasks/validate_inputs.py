"""Pipeline input validation task."""

from __future__ import annotations

from rse_survey.analysis.context import AnalysisContext, TaskResult
from rse_survey.analysis.registry import register
from rse_survey.data.validation import validate_inputs as _validate


@register
class ValidateInputsTask:
    name = "validate_inputs"

    def run(self, ctx: AnalysisContext) -> TaskResult:
        # Prefer book-level validation without requiring a question
        result = _validate(ctx.book, raise_on_error=True)
        return TaskResult(
            task_name=self.name,
            question_id=ctx.question.question_id,
            meta={"n_warnings": len(result.warnings)},
        )


def run_book_validation(book) -> None:
    _validate(book, raise_on_error=True)
