"""Reusable summarisation shared by analysis tasks.

``categorical`` turns long answer rows into count/percentage tables;
``categories`` remaps answer values first (display labels, aggregate groups,
closed-option filtering, HF-coded free text).
"""

from rse_survey.analysis.summarize.categorical import (
    apply_category_order,
    is_true_false_categories,
    summarize_by_group,
    summarize_categorical_focus,
)
from rse_survey.analysis.summarize.categories import (
    apply_category_groups,
    apply_category_labels,
    apply_hf_coded_categories,
    category_groups_to_mapping,
    filter_closed_answers,
    other_labels_by_country,
    token_labels_csv_path,
)

__all__ = [
    "apply_category_groups",
    "apply_category_labels",
    "apply_category_order",
    "apply_hf_coded_categories",
    "category_groups_to_mapping",
    "filter_closed_answers",
    "is_true_false_categories",
    "other_labels_by_country",
    "summarize_by_group",
    "summarize_categorical_focus",
    "token_labels_csv_path",
]
