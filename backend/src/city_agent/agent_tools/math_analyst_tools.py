import os
from pathlib import Path
import pandas as pd

# TODO: We should be pulling from the DB and not from data.
BACKEND_DIR = str(
    next(p for p in Path(__file__).resolve().parents if p.name == "backend")
)
DATA_DIR = f"{BACKEND_DIR}/data"

def _get_spreadsheet(filename: str) -> pd.DataFrame:
    """
    Helper function to read a spreadsheet file (CSV or XLSX) into a pandas DataFrame.
    Args:
        filename (str): The name of the spreadsheet file to read.
    Returns:
        pd.DataFrame: The contents of the spreadsheet as a DataFrame.
    """
    if filename.endswith('.csv'):
        return pd.read_csv(os.path.join(DATA_DIR, filename), encoding="cp1252")
    elif filename.endswith('.xlsx'):
        return pd.read_excel(os.path.join(DATA_DIR, filename))
    else:
        raise ValueError(f"Unsupported file format for file: {filename}")

def get_spreadsheet_info_impl(filename: str) -> str:
    """
    Tool for retrieving basic information about a spreadsheet
    Args:
        filename (str): The name of the spreadsheet file.

    Returns:
        str: A string representation of the head and first 5 rows of the spreadsheet.
    """
    if(filename not in os.listdir(DATA_DIR)):
        return "File not found: " + filename
    df = _get_spreadsheet(filename)
    return df.head().to_string()
    
def get_mean_impl(filename: str, column_name: str) -> float:
    """
    Tool for calculating the mean of a specified column in a given spreadsheet.
    Args:
        filename (str): The name of the spreadsheet file.
        column_name (str): The name of the column for which to calculate the mean.
    Returns:
        float: The mean value of the specified column.
    """
    df = _get_spreadsheet(filename)
    return df[column_name].mean()

def filter_values_impl(filename: str, column_name: str, keyword: str) -> str:
    """
    Tool for filtering rows in a specified column of a given spreadsheet based on a keyword.
    Args:
        filename (str): The name of the spreadsheet file.
        column_name (str): The name of the column to filter.
        keyword (str): The keyword to filter by.
    Returns:
        str: A string representation of the filtered rows.
    """
    df = _get_spreadsheet(filename)
    filtered_df = df[df[column_name].str.contains(keyword, na=False)]
    return filtered_df.to_string()