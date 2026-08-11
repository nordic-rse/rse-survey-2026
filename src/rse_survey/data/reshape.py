"""Melt the wide respondent table into the clean long-format answer schema.

One row per respondent × question × selected option, with sub-item labels
recovered from the survey column metadata.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from rse_survey.config.book_config import BookConfig
from rse_survey.data.columns import question_columns

CLEAN_LONG_COLUMNS = [
    "row_id",
    "country",
    "country_group",
    "year",
    "age_group",
    "question_id",
    "option_code",
    "item",
    "value",
]

_BRACKET_RE = re.compile(r"^(.+)\[([^\]]+)\](?:_0)?$")
_SELECTED = {"true", "yes", "y", "1"}
_UNSELECTED = {"false", "no", "n", "0", ""}


_TRAILING_BRACKET_RE = re.compile(r"\[([^\[\]]+)\]\s*$")


def _label_from_question_text(row: pd.Series) -> str:
    """Recover an array row's label from the trailing ``[...]`` in its wording.

    ``Option`` is normally the pre-extracted bracket contents, but extraction
    fails for some rows (e.g. labels containing their own punctuation), which
    would otherwise leave that sub-question unlabelled.
    """
    for field in ("Question", "Old_name"):
        text = row.get(field)
        if text is None or pd.isna(text):
            continue
        match = _TRAILING_BRACKET_RE.search(str(text).strip())
        if match:
            label = match.group(1).strip()
            if label:
                return label
    return ""


def _option_label_lookup(all_cols: pd.DataFrame) -> dict[str, str]:
    if "New_name" not in all_cols.columns:
        return {}
    lookup: dict[str, str] = {}
    for _, row in all_cols.iterrows():
        name = str(row["New_name"]).strip()
        if not name:
            continue
        opt = row.get("Option")
        label = "" if opt is None or pd.isna(opt) else str(opt).strip()
        if not label:
            label = _label_from_question_text(row)
        if label:
            lookup[name] = label
    return lookup


def _is_nonempty(val: object) -> bool:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return False
    s = str(val).strip()
    return bool(s) and s.lower() != "nan"


def _is_selected_flag(val: object) -> bool | None:
    """Return True/False for checkbox-like cells; None if free-text-ish."""
    if not _is_nonempty(val):
        return False
    s = str(val).strip().lower()
    if s in _SELECTED:
        return True
    if s in _UNSELECTED:
        return False
    return None


def _column_question_map(columns: list[str], question_ids: list[str]) -> dict[str, str]:
    """Map wide column name → configured question_id."""
    mapping: dict[str, str] = {}
    for qid in question_ids:
        for col in question_columns(qid, columns):
            # Prefer the first matching question id if overlaps occur
            mapping.setdefault(col, qid)
    return mapping


def _option_code(column: str) -> str:
    m = _BRACKET_RE.match(column)
    if m:
        return m.group(2)
    return ""


def _column_stem(column: str) -> str:
    """Raw stem of a bracketed column: ``likert0[1]_0`` → ``likert0``."""
    m = _BRACKET_RE.match(column)
    if m:
        return m.group(1)
    return re.sub(r"_0$", "", column)


def _clean_item_label(text: str) -> str:
    """Tidy a survey sub-item label for display.

    Option text arrives as the array row wording (``developing software?``);
    drop the trailing question mark and sentence-case it.
    """
    label = str(text).strip().rstrip("?").strip()
    if not label:
        return ""
    return label[0].upper() + label[1:]


def _item_label(
    column: str,
    labels: dict[str, str],
    conditions: dict[str, str] | None,
) -> str:
    """Sub-item label for an array row, suffixed with its condition if paired.

    Falls back to an empty label rather than the raw option code, so opaque
    codes like ``SQ001`` never reach a table or axis.
    """
    base = _clean_item_label(labels.get(column, ""))
    condition = (conditions or {}).get(_column_stem(column))
    if not condition:
        return base
    return f"{base} ({condition})" if base else condition


def book_item_conditions(book: BookConfig) -> dict[str, dict[str, str]]:
    """Per-question ``{raw stem: condition label}`` map for ``to_long``."""
    return {
        qid: q.item_conditions for qid, q in book.questions.items() if q.item_conditions
    }


def book_item_questions(book: BookConfig) -> set[str]:
    """Questions whose bracketed columns are sub-questions, not options.

    Likert arrays ask the same scale about several items; a checkbox grid's
    brackets are answer options and its ``[other]`` slot is free text, so
    neither carries a sub-question label.
    """
    return {
        qid
        for qid, q in book.questions.items()
        if q.response_kind == "likert" or q.item_conditions
    }


def to_long(
    tf: pd.DataFrame,
    all_cols: pd.DataFrame,
    question_ids: list[str],
    *,
    country_column: str = "socio1_0",
    year_column: str = "Year_0",
    item_conditions: dict[str, dict[str, str]] | None = None,
    item_questions: set[str] | None = None,
) -> pd.DataFrame:
    """Melt question columns into the clean long schema.

    ``item_conditions`` maps question_id → {raw column stem → condition label}
    for questions assembled from paired arrays; see ``_item_label``.
    ``item_questions`` limits sub-item labelling to those question ids; when
    ``None`` every array-style column is labelled.
    """
    col_to_qid = _column_question_map(list(tf.columns), question_ids)
    q_cols = [c for c in tf.columns if c in col_to_qid]
    if not q_cols:
        return pd.DataFrame(columns=CLEAN_LONG_COLUMNS)

    id_vars = ["row_id", country_column, "country_group", "age_group"]
    if year_column in tf.columns:
        id_vars.append(year_column)
    id_vars = [c for c in id_vars if c in tf.columns]

    melted = tf.melt(
        id_vars=id_vars,
        value_vars=q_cols,
        var_name="column_name",
        value_name="raw_value",
    )
    labels = _option_label_lookup(all_cols)

    rows: list[dict[str, Any]] = []
    for rec in melted.to_dict(orient="records"):
        col = str(rec["column_name"])
        raw = rec["raw_value"]
        opt = _option_code(col)
        qid = col_to_qid[col]

        item = ""
        if opt:
            flag = _is_selected_flag(raw)
            if flag is False:
                continue
            if flag is True:
                # Checkbox grid: the bracket names the option, not a sub-question
                value = labels.get(col) or opt
            else:
                # Array row / free-text slot: the bracket names a sub-question
                # and the cell holds that row's answer.
                if not _is_nonempty(raw):
                    continue
                value = str(raw).strip()
                if item_questions is None or qid in item_questions:
                    item = _item_label(col, labels, (item_conditions or {}).get(qid))
        else:
            if not _is_nonempty(raw):
                continue
            value = str(raw).strip()

        year_val = rec.get(year_column)
        year_missing = year_val is None or (
            isinstance(year_val, float) and pd.isna(year_val)
        )
        if not year_missing:
            if isinstance(year_val, float) and year_val == int(year_val):
                year_out: Any = int(year_val)
            else:
                try:
                    year_out = int(year_val)  # type: ignore[arg-type]
                except (TypeError, ValueError):
                    year_out = year_val
        else:
            year_out = pd.NA

        age = rec.get("age_group")
        if age is not None and isinstance(age, float) and pd.isna(age):
            age = pd.NA

        rows.append(
            {
                "row_id": rec["row_id"],
                "country": rec.get(country_column),
                "country_group": rec.get("country_group"),
                "year": year_out,
                "age_group": age,
                "question_id": qid,
                "option_code": opt,
                "item": item,
                "value": value,
            }
        )

    if not rows:
        return pd.DataFrame(columns=CLEAN_LONG_COLUMNS)
    out = pd.DataFrame(rows)
    return out.loc[:, CLEAN_LONG_COLUMNS]
