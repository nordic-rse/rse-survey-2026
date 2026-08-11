from rse_survey.analysis.registry import ensure_builtin_tasks_loaded, list_tasks


def test_builtin_tasks_registered():
    ensure_builtin_tasks_loaded()
    names = list_tasks()
    for expected in (
        "focus",
        "by_age",
        "between_countries",
        "across_waves",
        "validate_inputs",
    ):
        assert expected in names
