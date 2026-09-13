"""Helpers for the survey analysis."""

from pathlib import Path


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
