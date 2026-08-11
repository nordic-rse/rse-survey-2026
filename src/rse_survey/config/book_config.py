"""Typed view of ``config/book.yml`` (what the report covers, per question)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rse_survey.config.paths import REPO_ROOT, resolve_repo_path
from rse_survey.config.yaml_io import read_yaml

PRESENTATION_MODES = frozenset({"table", "graphic", "both"})


def resolve_presentation(value: str | None, *, default: str = "both") -> str:
    mode = str(value or default).strip().lower()
    if mode not in PRESENTATION_MODES:
        known = ", ".join(sorted(PRESENTATION_MODES))
        raise ValueError(f"Unknown presentation={value!r}; expected one of: {known}")
    return mode


@dataclass
class QuestionConfig:
    question_id: str
    title: str = ""
    response_kind: str = "categorical"
    tasks: list[str] = field(default_factory=list)
    appendix: bool = False
    # Explicit answer-label order; None → sort by frequency (default)
    category_order: list[str] | None = None
    # Fixed options for categorical_with_other; anything else is Other
    closed_categories: list[str] | None = None
    # Raw survey label → display label (tables/plots); keys match data values
    category_labels: dict[str, str] | None = None
    # New display category → list of raw survey values to aggregate
    category_groups: dict[str, list[str]] | None = None
    # Raw column stem → condition label, for questions built from paired
    # arrays (e.g. likert0 = "Actual", likert1 = "Desired"). Sub-item labels
    # become "<item> (<condition>)" so the pair stays adjacent in output.
    item_conditions: dict[str, str] | None = None
    # Display order for sub-item labels; None → order of first appearance
    item_order: list[str] | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class BookConfig:
    path: Path
    data_dir: Path
    focus_label: str
    focus_countries: list[str]
    age_column: str
    age_groups: dict[str, list[str]]
    compare_groups: dict[str, list[str]]
    questions: dict[str, QuestionConfig]
    waves: dict[str, Any] | None = None
    country_column: str = "socio1_0"
    submit_column: str = "submitdate_0"
    year_column: str = "Year_0"
    processed_dir: str = "rse-book/_data"
    empty_question_policy: str = "skip_with_warning"
    # What select-question chapters include: table | graphic | both
    presentation: str = "both"
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def question_ids(self) -> list[str]:
        return list(self.questions.keys())


def load_defaults(path: Path | None = None) -> dict[str, Any]:
    defaults_path = path or (REPO_ROOT / "config" / "defaults.yml")
    if not defaults_path.exists():
        return {}
    return read_yaml(defaults_path)


def load_book_config(
    path: str | Path | None = None,
    *,
    repo_root: Path | None = None,
) -> BookConfig:
    root = repo_root or REPO_ROOT
    book_path = resolve_repo_path(path or "config/book.yml", root)
    defaults = load_defaults(root / "config" / "defaults.yml")
    raw = read_yaml(book_path)

    focus = raw.get("focus") or {}
    questions_raw = raw.get("questions") or {}
    default_tasks = list(defaults.get("default_tasks") or [])

    questions: dict[str, QuestionConfig] = {}
    for qid, spec in questions_raw.items():
        spec = spec or {}
        tasks = list(spec.get("tasks") or default_tasks)
        raw_order = spec.get("category_order", None)
        if raw_order is None:
            category_order = None
        elif isinstance(raw_order, list):
            category_order = [str(x) for x in raw_order]
        else:
            raise ValueError(
                f"questions.{qid}.category_order must be a list or null, "
                f"got {type(raw_order).__name__}"
            )
        response_kind = str(spec.get("response_kind") or "categorical")
        raw_closed = spec.get("closed_categories", None)
        if raw_closed is None:
            closed_categories = None
        elif isinstance(raw_closed, list):
            closed_categories = [str(x) for x in raw_closed]
        else:
            raise ValueError(
                f"questions.{qid}.closed_categories must be a list or null, "
                f"got {type(raw_closed).__name__}"
            )
        if response_kind == "categorical_with_other" and not closed_categories:
            raise ValueError(
                f"questions.{qid}: response_kind categorical_with_other "
                "requires a non-empty closed_categories list"
            )
        raw_labels = spec.get("category_labels", None)
        if raw_labels is None:
            category_labels = None
        elif isinstance(raw_labels, dict):
            category_labels = {str(k): str(v) for k, v in raw_labels.items()}
        else:
            raise ValueError(
                f"questions.{qid}.category_labels must be a mapping or null, "
                f"got {type(raw_labels).__name__}"
            )
        raw_groups = spec.get("category_groups", None)
        if raw_groups is None:
            category_groups = None
        elif isinstance(raw_groups, dict):
            category_groups = {}
            seen_members: dict[str, str] = {}
            for group_label, members in raw_groups.items():
                if not isinstance(members, list):
                    raise ValueError(
                        f"questions.{qid}.category_groups.{group_label} "
                        f"must be a list, got {type(members).__name__}"
                    )
                group_name = str(group_label)
                member_list = [str(m) for m in members]
                for member in member_list:
                    key = member.strip()
                    if key in seen_members and seen_members[key] != group_name:
                        raise ValueError(
                            f"questions.{qid}.category_groups: value {key!r} "
                            f"appears in both {seen_members[key]!r} and "
                            f"{group_name!r}"
                        )
                    seen_members[key] = group_name
                category_groups[group_name] = member_list
        else:
            raise ValueError(
                f"questions.{qid}.category_groups must be a mapping or null, "
                f"got {type(raw_groups).__name__}"
            )
        raw_conditions = spec.get("item_conditions", None)
        if raw_conditions is None:
            item_conditions = None
        elif isinstance(raw_conditions, dict):
            item_conditions = {str(k): str(v) for k, v in raw_conditions.items()}
        else:
            raise ValueError(
                f"questions.{qid}.item_conditions must be a mapping or null, "
                f"got {type(raw_conditions).__name__}"
            )
        raw_item_order = spec.get("item_order", None)
        if raw_item_order is None:
            item_order = None
        elif isinstance(raw_item_order, list):
            item_order = [str(x) for x in raw_item_order]
        else:
            raise ValueError(
                f"questions.{qid}.item_order must be a list or null, "
                f"got {type(raw_item_order).__name__}"
            )
        questions[qid] = QuestionConfig(
            question_id=qid,
            title=str(spec.get("title") or qid),
            response_kind=response_kind,
            tasks=tasks,
            appendix=bool(spec.get("appendix", False)),
            category_order=category_order,
            closed_categories=closed_categories,
            category_labels=category_labels,
            category_groups=category_groups,
            item_conditions=item_conditions,
            item_order=item_order,
            extra={
                k: v
                for k, v in spec.items()
                if k
                not in {
                    "title",
                    "response_kind",
                    "tasks",
                    "appendix",
                    "category_order",
                    "closed_categories",
                    "category_labels",
                    "category_groups",
                    "item_conditions",
                    "item_order",
                }
            },
        )

    age_groups = raw.get("age_groups") or {}
    # Normalize values to list[str]
    age_groups_norm: dict[str, list[str]] = {}
    for name, labels in age_groups.items():
        if isinstance(labels, dict) and "min" in labels:
            # numeric bands not used for 2026 socio3_0; keep empty mapping
            age_groups_norm[str(name)] = []
        elif isinstance(labels, list):
            age_groups_norm[str(name)] = [str(x) for x in labels]
        else:
            age_groups_norm[str(name)] = [str(labels)]

    compare = raw.get("compare_groups") or {}
    compare_norm = {
        str(k): [str(c) for c in (v if isinstance(v, list) else [v])]
        for k, v in compare.items()
    }

    data_dir = resolve_repo_path(raw.get("data_dir") or "RSE_survey_2026_data", root)

    presentation = resolve_presentation(
        raw.get("presentation") or defaults.get("presentation") or "both"
    )

    return BookConfig(
        path=book_path,
        data_dir=data_dir,
        focus_label=str(focus.get("label") or "Focus"),
        focus_countries=[str(c) for c in (focus.get("countries") or [])],
        age_column=str(
            raw.get("age_column") or defaults.get("age_column") or "socio3_0"
        ),
        age_groups=age_groups_norm,
        compare_groups=compare_norm,
        questions=questions,
        waves=raw.get("waves"),
        country_column=str(defaults.get("country_column") or "socio1_0"),
        submit_column=str(defaults.get("submit_column") or "submitdate_0"),
        year_column=str(
            (raw.get("waves") or {}).get("year_column")
            or defaults.get("year_column")
            or "Year_0"
        ),
        processed_dir=str(
            raw.get("processed_dir")
            or defaults.get("processed_dir")
            or "rse-book/_data"
        ),
        empty_question_policy=str(
            defaults.get("empty_question_policy") or "skip_with_warning"
        ),
        presentation=presentation,
        raw=raw,
    )
