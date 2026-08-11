"""Select-question analysis: focus / by age / between countries.

One conceptual task, split into its subtasks:

* ``grouping`` — which rows and which facet a view uses
* ``summary``  — count/percentage table for those rows
* ``artifacts``— the CSV / markdown / PNG a chapter includes
* ``run``      — the ordered pipeline, plus the three registered tasks
"""

from rse_survey.analysis.tasks.select_questions.artifacts import (
    write_artifacts,
    write_between_countries_separate_artifacts,
    write_other_by_country_artifacts,
    write_per_item_artifacts,
)
from rse_survey.analysis.tasks.select_questions.grouping import (
    SELECT_KINDS,
    GroupingSpec,
    analysis_frame,
    filter_focus_country,
    filter_item,
    group_levels_for,
    question_items,
    resolve_grouping,
)
from rse_survey.analysis.tasks.select_questions.run import (
    BetweenCountriesTask,
    ByAgeTask,
    FocusTask,
    run_select_question,
)
from rse_survey.analysis.tasks.select_questions.summary import (
    build_summary_table,
    total_respondents,
)

# Re-exported for convenience: tasks and tests treat value recoding as part of
# the select-question surface, though it is shared with other analyses.
from rse_survey.analysis.summarize.categories import (  # isort: skip
    apply_category_groups,
    apply_category_labels,
    apply_hf_coded_categories,
    filter_closed_answers,
    other_labels_by_country,
    token_labels_csv_path,
)

__all__ = [
    "SELECT_KINDS",
    "BetweenCountriesTask",
    "ByAgeTask",
    "FocusTask",
    "GroupingSpec",
    "analysis_frame",
    "apply_category_groups",
    "apply_category_labels",
    "apply_hf_coded_categories",
    "build_summary_table",
    "filter_closed_answers",
    "filter_focus_country",
    "filter_item",
    "group_levels_for",
    "total_respondents",
    "other_labels_by_country",
    "question_items",
    "resolve_grouping",
    "run_select_question",
    "token_labels_csv_path",
    "write_artifacts",
    "write_between_countries_separate_artifacts",
    "write_other_by_country_artifacts",
    "write_per_item_artifacts",
]
