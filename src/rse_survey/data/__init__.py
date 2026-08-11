"""Data layer: raw survey CSVs → the clean long-format answers table.

Stage 2 of the pipeline. Reads :mod:`rse_survey.config`; knows nothing about
analysis, plots or the book.

The clean long schema is one row per respondent × question × answer:
``row_id, country, country_group, year, age_group, question_id, option_code,
item, value``.
"""

from rse_survey.data.clean_dataset import (
    build_clean_dataset,
    compare_long,
    focus_long,
    load_clean_long,
    load_compare_frame,
    load_focus_frame,
    save_clean_long,
)
from rse_survey.data.columns import (
    QUESTION_ALIASES,
    coding_question_ids,
    interest_question_ids,
    question_columns,
    select_interest_columns,
)
from rse_survey.data.filters import (
    add_group_columns,
    assign_age_groups,
    filter_countries,
    filter_survey_respondents,
    filter_years,
    is_submitted_response,
    target_countries,
)
from rse_survey.data.readers import load_raw, read_all_cols, read_tf
from rse_survey.data.reshape import (
    CLEAN_LONG_COLUMNS,
    book_item_conditions,
    book_item_questions,
    to_long,
)
from rse_survey.data.validation import (
    InputValidationError,
    ValidationIssue,
    ValidationResult,
    validate_inputs,
)

__all__ = [
    "CLEAN_LONG_COLUMNS",
    "QUESTION_ALIASES",
    "InputValidationError",
    "ValidationIssue",
    "ValidationResult",
    "add_group_columns",
    "assign_age_groups",
    "book_item_conditions",
    "book_item_questions",
    "build_clean_dataset",
    "coding_question_ids",
    "compare_long",
    "filter_countries",
    "filter_survey_respondents",
    "filter_years",
    "focus_long",
    "interest_question_ids",
    "is_submitted_response",
    "load_clean_long",
    "load_compare_frame",
    "load_focus_frame",
    "load_raw",
    "question_columns",
    "read_all_cols",
    "read_tf",
    "save_clean_long",
    "select_interest_columns",
    "target_countries",
    "to_long",
    "validate_inputs",
]
