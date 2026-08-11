"""Raw survey CSV readers.

The only place that touches the files under ``RSE_survey_2026_data/``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from rse_survey.config.book_config import BookConfig


def read_tf(data_dir: Path) -> pd.DataFrame:
    path = Path(data_dir) / "2026_tf.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing respondent table: {path}")
    tf = pd.read_csv(path, low_memory=False)
    # Fix empty column names like R does
    cols = []
    n_unnamed = 0
    for c in tf.columns:
        if not str(c).strip() or str(c).startswith("Unnamed"):
            n_unnamed += 1
            cols.append(f".unnamed{n_unnamed}")
        else:
            cols.append(str(c))
    tf.columns = cols
    return tf


def read_all_cols(data_dir: Path) -> pd.DataFrame:
    path = Path(data_dir) / "2026_all_cols.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing column metadata: {path}")
    return pd.read_csv(path)


def load_raw(book: BookConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    return read_tf(book.data_dir), read_all_cols(book.data_dir)
