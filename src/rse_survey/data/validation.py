"""Validate survey inputs and book configuration before analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rse_survey.config.book_config import BookConfig, load_book_config
from rse_survey.config.coding_config import load_free_text_coding
from rse_survey.data.columns import question_columns
from rse_survey.data.readers import read_all_cols, read_tf


@dataclass
class ValidationIssue:
    code: str
    message: str
    level: str = "error"  # error | warning


@dataclass
class ValidationResult:
    ok: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "warning"]


class InputValidationError(Exception):
    def __init__(self, result: ValidationResult):
        self.result = result
        msgs = "; ".join(f"[{i.code}] {i.message}" for i in result.errors)
        super().__init__(msgs or "Input validation failed")


def validate_inputs(
    book: BookConfig | None = None,
    *,
    book_path: str | Path | None = None,
    coding_path: str | Path | None = None,
    raise_on_error: bool = True,
) -> ValidationResult:
    issues: list[ValidationIssue] = []
    if book is None:
        try:
            book = load_book_config(book_path)
        except Exception as exc:  # noqa: BLE001 — collect as validation issue
            issues.append(
                ValidationIssue("book_config", f"Cannot load book config: {exc}")
            )
            result = ValidationResult(ok=False, issues=issues)
            if raise_on_error:
                raise InputValidationError(result) from exc
            return result

    if not book.focus_countries:
        issues.append(ValidationIssue("focus_empty", "focus.countries is empty"))

    if not book.data_dir.exists():
        issues.append(
            ValidationIssue("data_dir_missing", f"data_dir not found: {book.data_dir}")
        )
    else:
        tf_path = book.data_dir / "2026_tf.csv"
        cols_path = book.data_dir / "2026_all_cols.csv"
        if not tf_path.exists():
            issues.append(
                ValidationIssue("tf_missing", f"Missing {tf_path.name} in data_dir")
            )
        if not cols_path.exists():
            issues.append(
                ValidationIssue(
                    "all_cols_missing", f"Missing {cols_path.name} in data_dir"
                )
            )

        if tf_path.exists():
            try:
                tf = read_tf(book.data_dir)
            except Exception as exc:  # noqa: BLE001
                issues.append(ValidationIssue("tf_unreadable", str(exc)))
                tf = None

            if tf is not None:
                for col in (
                    book.country_column,
                    book.submit_column,
                    book.age_column,
                ):
                    if col not in tf.columns:
                        issues.append(
                            ValidationIssue(
                                "missing_column",
                                f"Required column {col!r} not in 2026_tf.csv",
                            )
                        )

                # Focus row count
                if (
                    book.country_column in tf.columns
                    and book.submit_column in tf.columns
                ):
                    from rse_survey.data.filters import filter_survey_respondents

                    focus = filter_survey_respondents(
                        tf,
                        book.focus_countries,
                        country_column=book.country_column,
                        submit_column=book.submit_column,
                    )
                    if len(focus) == 0:
                        issues.append(
                            ValidationIssue(
                                "focus_zero_rows",
                                "No submitted respondents match focus.countries",
                            )
                        )

                for qid, q in book.questions.items():
                    cols = question_columns(qid, list(tf.columns))
                    if not cols:
                        issues.append(
                            ValidationIssue(
                                "question_columns_missing",
                                f"No columns match question {qid!r}",
                                level="warning",
                            )
                        )
                    if "across_waves" in q.tasks and not book.waves:
                        issues.append(
                            ValidationIssue(
                                "waves_not_configured",
                                f"{qid} requests across_waves but waves: is not set",
                                level="warning",
                            )
                        )
                    if q.response_kind == "free_text" and q.appendix:
                        coding = load_free_text_coding(coding_path)
                        if qid not in coding:
                            issues.append(
                                ValidationIssue(
                                    "coding_config_missing",
                                    f"free_text question {qid} has appendix: true "
                                    "but no entry in free_text_coding.yml",
                                    level="warning",
                                )
                            )

        if cols_path.exists():
            try:
                read_all_cols(book.data_dir)
            except Exception as exc:  # noqa: BLE001
                issues.append(ValidationIssue("all_cols_unreadable", str(exc)))

    if not book.questions:
        issues.append(
            ValidationIssue("no_questions", "book.yml questions map is empty")
        )

    # Age group labels configured
    if not book.age_groups:
        issues.append(
            ValidationIssue(
                "age_groups_empty",
                "age_groups is empty; by_age tasks will yield no rows",
                level="warning",
            )
        )

    ok = not any(i.level == "error" for i in issues)
    result = ValidationResult(ok=ok, issues=issues)
    if raise_on_error and not ok:
        raise InputValidationError(result)
    return result
