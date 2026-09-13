"""Helpers for the survey analysis."""

from pathlib import Path

import pandas as pd


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
    return df
