"""Codebook with the question text and allowed answers per response column."""

import re

import pandas as pd

from rse_survey_report.config import AGREEMENT_LEVELS, CATEGORIES
from rse_survey_report.utils import parse_questions


def _answer_key(answer: object) -> tuple[int, float, str]:
    """Sort key: answers that start with a number by that number, others by text.

    Agreement answers follow AGREEMENT_LEVELS. The answer "Other" always
    comes last.
    """
    text = str(answer)
    scale = [level.lower() for level in AGREEMENT_LEVELS]
    if text.strip().lower() in scale:
        return (0, float(scale.index(text.strip().lower())), text)
    if text.strip().lower() == "other":
        return (2, 0.0, text)
    match = re.match(r"\s*(\d+(?:\.\d+)?)", text)
    return (0, float(match[1]), text) if match else (1, 0.0, text)


def build_codebook(
    df_cols: pd.DataFrame,
    df: pd.DataFrame,
    max_answers: int = 20,
    question_col: str = "Question",
    id_col: str = "New_name",
    categories: dict[str, list[str]] = CATEGORIES,
) -> pd.DataFrame:
    """Build a codebook with one row per response column and answer.

    Parameters
    ----------
    df_cols : pd.DataFrame
        Raw data frame with question text and ids (2026_all_cols.csv)
    df : pd.DataFrame
        Survey responses
    max_answers : int, optional
        Columns with more unique answers are free text, by default 20
    question_col : str
        Name of the column with question text
    id_col : str
        Name of the column with question id information
    categories : dict[str, list[str]]
        Mapping from category name to question ids, by default CATEGORIES

    Returns
    -------
    pd.DataFrame
        Codebook with the columns col, id, question, category, type,
        answer, and order. Columns with only True/False answers get type
        "bool". Columns with a "%" in an answer get type "likert".
        Columns with "agree" in an answer get type "agreement".
        A multiple-choice option with True/False answers gets one row
        of type "choice" with the option text as answer and its position
        within the question as order. For all other columns, the option text
        (e.g. the item of a Likert grid) completes the question.
        Free-text "Other" columns (type "text_other"), other free-text
        columns (type "text"), and columns
        without answers (type "empty") get one row with answer NaN.
        Answers that start with a number come first in numeric order, the
        other answers follow in alphabetical order, and "Other" comes last;
        set the order of other
        ordinal answers by hand.
    """
    df_questions = parse_questions(df_cols, question_col, id_col, categories)
    df_questions = df_questions[df_questions["col"].isin(df.columns)]
    is_mc = df_questions["mc_answer"].notna() & (df_questions["mc_answer"] != "Other")

    # the survey order is the column order of the responses
    position = {col: i for i, col in enumerate(df.columns)}
    mc = df_questions[is_mc]
    pos = mc["col"].map(position)
    mc_order = dict(
        zip(mc["col"], pos.groupby(mc["id"]).rank().astype(int), strict=True)
    )
    mc_text = dict(zip(mc["col"], mc["mc_answer"], strict=True))

    rows = []
    options = []
    for col in df_questions["col"]:
        answers = sorted(df[col].dropna().unique(), key=_answer_key)
        all_bool = all(pd.api.types.is_bool(a) for a in answers)
        if "[other]" in col.lower():
            rows.append(
                {"col": col, "type": "text_other", "answer": pd.NA, "order": pd.NA}
            )
        elif not answers:
            rows.append({"col": col, "type": "empty", "answer": pd.NA, "order": pd.NA})
        elif col in mc_order and all_bool:
            # one row per option: the option text is the answer
            options.append(col)
            rows.append(
                {
                    "col": col,
                    "type": "choice",
                    "answer": mc_text[col],
                    "order": mc_order[col],
                }
            )
        elif len(answers) > max_answers:
            rows.append({"col": col, "type": "text", "answer": pd.NA, "order": pd.NA})
        else:
            if all_bool:
                kind = "bool"
            elif any("%" in str(answer) for answer in answers):
                kind = "likert"
            elif any("agree" in str(answer).lower() for answer in answers):
                kind = "agreement"
            else:
                kind = "choice"
            rows.extend(
                {"col": col, "type": kind, "answer": answer, "order": i}
                for i, answer in enumerate(answers, start=1)
            )

    codebook = df_questions.merge(pd.DataFrame(rows), on="col", how="left")
    # the item text completes the question, e.g. the items of a Likert grid
    has_item = (
        codebook["mc_answer"].notna()
        & ~codebook["col"].isin(options)
        & (codebook["question"] != codebook["mc_answer"])
    )
    codebook["question"] = codebook["question"].mask(
        has_item, codebook["question"] + " " + codebook["mc_answer"]
    )
    codebook = codebook.drop(columns=["mc_id", "mc_answer"])

    # sort the rows in survey order
    return (
        codebook.assign(position=codebook["col"].map(position))
        .sort_values(["position", "order"])
        .drop(columns="position")
        .reset_index(drop=True)
    )
