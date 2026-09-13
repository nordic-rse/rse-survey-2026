"""Helpers for the survey analysis."""

from pathlib import Path

import pandas as pd

from rse_survey_report.config import CATEGORIES


def get_data_path(file: str, year: int, data_dir: str = "data") -> Path:
    """Resolve the path to a data file.

    Parameters
    ----------
    file : str
        Name of the data file
    year : int
        Year of the survey data; related to subdirectory of data_dir
    data_dir : str, optional
        Name of the folder where data is stored, by default "data"

    Returns
    -------
    Path
        path to data file

    Raises
    ------
    TypeError
        Raises if file or data_dir are not strings.
    FileNotFoundError
        Raises if no file can be found in the resolved path.
    """
    root = Path(__file__).resolve().parents[2]
    path = root / data_dir / str(year) / file

    if not path.is_file():
        raise FileNotFoundError(f"No file at {path}")

    return path


def load_data(path: Path) -> pd.DataFrame:
    """Load data from path into data frame.

    Parameters
    ----------
    path : Path
        Path to data file

    Returns
    -------
    pd.DataFrame
        Survey responses as data frame

    Raises
    ------
    ValueError
        Raises if the data frame has no rows
    """
    df = pd.read_csv(path)
    if len(df) == 0:
        raise ValueError("The data frame has no rows.")

    if "Unnamed: 0" in df:
        df = df.drop(columns="Unnamed: 0")

    return df


def preprocess_data(
    df: pd.DataFrame, excl_var: str | None = "submitdate_0"
) -> pd.DataFrame:
    """Preprocessing of raw data frame.

    Including rename columns, add variable that detects partial completion

    Parameters
    ----------
    df : pd.DataFrame
        Raw survey responses
    excl_var : str | None, optional
        Exclude responses when this variable has no entry, by default "submitdate_0"

    Returns
    -------
    pd.DataFrame
        Clean survey responses

    Raises
    ------
    ValueError
        Raises if the clean data frame has no rows
        Raises if the column 'socio1_0' is missing
        Raises if the column 'submitdate_0' is missing
    """
    if "socio1_0" not in df:
        raise ValueError(
            "Column 'socio1_0' not found but is required. "
            "'socio1_0' encodes the country names."
        )
    if "submitdate_0" not in df:
        raise ValueError(
            "Column 'submitdate_0' not found but is required. "
            "'submitdate_0' encodes the survey submission time."
        )

    df_clean = (
        df.rename(columns={"socio1_0": "country"})
        .assign(complete=df["submitdate_0"].notna())
        .drop(columns=["submitdate_0"])
    )

    if len(df_clean) == 0:
        raise ValueError("Data frame has no rows after preprocessing.")

    return df_clean


def prepare_questions(
    df: pd.DataFrame,
    df_counts: pd.DataFrame,
    question_col: str = "Question",
    id_col: str = "New_name",
    categories: dict[str, list[str]] = CATEGORIES,
) -> pd.DataFrame:
    """Extract and clean up questions and ids from raw dataframe.

    Raw data frame is called 2026: 2026_all_cols.csv

    Parameters
    ----------
    df : pd.DataFrame
        Raw data frame with question text and ids
    df_counts: pd.DataFrame
        Data frame with response counts per question and country
    question_col : str
        Name of the column with question text
    id_col : str
        Name of the column with question id information
    categories : dict[str, list[str]]
        Mapping from category name to question ids, by default CATEGORIES

    Returns
    -------
    pd.DataFrame
        Clean data frame with question text, multiple-choice answers, ids,
        category, and country information. Questions without a category get NaN.
    """
    questions = (
        df[question_col]
        .str.replace(r"\t.*", "", regex=True)
        .str.extract(
            r"^\s*(?P<question>.*?)\s*(?:\([^()]*\))?\s*(?:\[(?P<mc_answer>[^\]]*)\])?\s*$"
        )
    )
    # questions likert5a and likert5b have no stem, copying therefore the item text
    no_stem = questions["question"] == ""
    questions["question"] = questions["question"].mask(no_stem, questions["mc_answer"])
    ids = df[id_col].str.extract(r"^(?P<id>[^\[]+?)(?:\[(?P<mc_id>[^\]]*)\])?(?:_0)?$")
    # map categories before likert5a, likert5b get their item suffix
    id_to_category = {i: cat for cat, id_list in categories.items() for i in id_list}
    category = ids["id"].map(id_to_category)
    # ensure that the special questions likert5a, liker5b get unique ids
    item_number = ids.groupby("id").cumcount() + 1
    ids["id"] = ids["id"].mask(no_stem, ids["id"] + "_" + item_number.astype(str))

    df_questions = pd.concat([ids, questions], axis=1).assign(
        col=df[id_col], category=category
    )

    df_long = (
        df_counts.rename_axis("country")
        .reset_index()
        .melt(id_vars="country", var_name="col", value_name="n_responses")
        .merge(df_questions, on="col", how="inner")
    )

    return df_long


def get_counts_question_country(df: pd.DataFrame) -> pd.DataFrame:
    """Count responses per question and country.

    Parameters
    ----------
    df : pd.DataFrame
        Clean data frame that has already been passed through preprocess_data

    Returns
    -------
    pd.DataFrame
        Data frame with countries in index and questions in columns
    """
    if "country" not in df:
        raise ValueError(
            "Column 'country' not found. Pass the data frame from preprocess_data()."
        )

    all_countries = sorted(df["country"].dropna().unique())

    return (
        df.drop(columns=["country", "complete"])
        .notna()
        .groupby(df["country"])
        .sum()
        .reindex(all_countries, fill_value=0)
    )
