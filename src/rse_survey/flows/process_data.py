"""Prefect flow: raw survey CSV → clean long-format dataset."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from prefect import flow, task

from rse_survey.config.book_config import load_book_config
from rse_survey.config.coding_config import load_free_text_coding
from rse_survey.config.paths import (
    clean_long_path,
    processed_dir_for,
    resolve_repo_path,
)
from rse_survey.data.clean_dataset import save_clean_long
from rse_survey.data.columns import interest_question_ids, select_interest_columns
from rse_survey.data.filters import add_group_columns, filter_countries, filter_years
from rse_survey.data.readers import load_raw
from rse_survey.data.reshape import book_item_conditions, book_item_questions, to_long
from rse_survey.logging_config import flow_result, get_logger

log = get_logger("process_data")


@task(name="load_raw")
def task_load_raw(book_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    return load_raw(load_book_config(book_path))


@task(name="select_variables")
def task_select_variables(
    tf: pd.DataFrame,
    book_path: str,
    question_ids: list[str],
) -> pd.DataFrame:
    return select_interest_columns(tf, load_book_config(book_path), question_ids)


@task(name="filter_countries")
def task_filter_countries(tf: pd.DataFrame, book_path: str) -> pd.DataFrame:
    return filter_countries(tf, load_book_config(book_path))


@task(name="filter_years")
def task_filter_years(tf: pd.DataFrame, book_path: str) -> pd.DataFrame:
    return filter_years(tf, load_book_config(book_path))


@task(name="create_age_groups")
def task_create_age_groups(tf: pd.DataFrame, book_path: str) -> pd.DataFrame:
    return add_group_columns(tf, load_book_config(book_path))


@task(name="save_clean_dataset")
def task_save_clean_dataset(
    tf: pd.DataFrame,
    all_cols: pd.DataFrame,
    book_path: str,
    question_ids: list[str],
) -> dict[str, Any]:
    book = load_book_config(book_path)
    long_df = to_long(
        tf,
        all_cols,
        question_ids,
        country_column=book.country_column,
        year_column=book.year_column,
        item_conditions=book_item_conditions(book),
        item_questions=book_item_questions(book),
    )
    path = save_clean_long(
        long_df,
        processed_dir_for(book),
        meta_extra={
            "focus_countries": list(book.focus_countries),
            "compare_groups": {k: list(v) for k, v in book.compare_groups.items()},
            "waves": book.waves,
        },
    )
    return {
        "path": str(path),
        "n_rows": int(len(long_df)),
        "n_respondents": int(long_df["row_id"].nunique()) if len(long_df) else 0,
        "n_questions": int(long_df["question_id"].nunique()) if len(long_df) else 0,
    }


@flow(name="process_data")
def process_data_flow(
    book_config: str | Path = "config/book.yml",
    coding_config: str | Path = "config/free_text_coding.yml",
) -> dict[str, Any] | None:
    """Process raw survey data into a clean long-format dataset."""
    book_path = str(resolve_repo_path(book_config))
    coding_path = str(resolve_repo_path(coding_config))
    book = load_book_config(book_path)
    coding = load_free_text_coding(coding_path)
    question_ids = interest_question_ids(book, coding)

    tf, all_cols = task_load_raw(book_path)
    tf = task_select_variables(tf, book_path, question_ids)
    tf = task_filter_countries(tf, book_path)
    tf = task_filter_years(tf, book_path)
    tf = task_create_age_groups(tf, book_path)
    save_info = task_save_clean_dataset(tf, all_cols, book_path, question_ids)

    log.info(
        "wrote %s (%s respondents)",
        clean_long_path(book),
        save_info.get("n_respondents"),
    )
    return flow_result(
        {
            "clean_long": str(clean_long_path(book)),
            "question_ids": question_ids,
            "save": save_info,
        }
    )
