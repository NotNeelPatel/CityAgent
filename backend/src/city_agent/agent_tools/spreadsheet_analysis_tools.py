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
    return f"Mean value in column '{column_name}': {df[column_name].mean()}"

def filter_values_impl(filename: str, columns: list, keyword: str) -> str:
    """
    Tool for retrieving specific information from a specified column in a given spreadsheet based on a keyword.
    Removes unnecessary columns
    Args:
        filename (str): The name of the spreadsheet file.
        column_name (str): The name of the column to search.
        keyword (str): The keyword to search for.
    Returns:
        str: A string representation of the rows that match the keyword in the specified column.
    """
    df = _get_spreadsheet(filename)
    try:
        specific_info_df = df[columns]
        specific_info_df = specific_info_df[specific_info_df.apply(lambda row: row.astype(str).str.contains(keyword, case=False, na=False).any(), axis=1)]
        if(len(specific_info_df) == 0):
            return f"No rows found in file '{filename}' containing keyword '{keyword}' in columns {columns}."
        elif(specific_info_df.size > 200):
            reduced_df = specific_info_df.head(min(10, len(specific_info_df)))
            return f"Data too large, showing first ~10 rows:\n{reduced_df.to_string()}\nUse more specific keywords or fewer columns to narrow down results."
        return specific_info_df.to_string()
    except KeyError as e:
        return f"Column not found in file '{filename}': {e}"

def get_unique_values_impl(filename: str, column_name: str) -> str:
    """
    Tool for retrieving unique values from a specified column in a given spreadsheet.
    Args:
        filename (str): The name of the spreadsheet file.
        column_name (str): The name of the column for which to retrieve unique values.
    Returns:
        str: A string representation of the unique values in the specified column.
    """
    df = _get_spreadsheet(filename)
    try:
        unique_values = df[column_name].unique()
        if(len(unique_values) > 20):
            unique_values = unique_values[:20]
            return f"More than 20 unique values found. Showing first 20 unique values:\n{str(unique_values)}"
        return str(unique_values)
    except KeyError:
        return f"Column '{column_name}' not found in file '{filename}'."

def count_values_impl(filename: str, column_name: str) -> str:
    """
    Tool for counting occurrences of each unique value in a specified column of a given spreadsheet.
    Args:
        filename (str): The name of the spreadsheet file.
        column_name (str): The name of the column to count values in.
    Returns:
        str: A string representation of the count of each unique value in the specified column.
    """
    df = _get_spreadsheet(filename)
    try:
        value_counts = df[column_name].value_counts()
        return f"Column '{column_name}' value counts:\n{value_counts.to_string()}"
    except KeyError:
        return f"Column '{column_name}' not found in file '{filename}'."

def get_min_in_column_impl(filename: str, column_name: str) -> float:
    """
    Tool for calculating the minimum value of a specified column in a given spreadsheet.
    Args:
        filename (str): The name of the spreadsheet file.
        column_name (str): The name of the column for which to calculate the minimum value.
    Returns:
        float: The minimum value of the specified column.
    """
    df = _get_spreadsheet(filename)
    try:
        return f"Minimum value in column '{column_name}': {df[column_name].min()}"
    except KeyError:
        return f"Column '{column_name}' not found in file '{filename}'."

def get_max_in_column_impl(filename: str, column_name: str) -> float:
    """
    Tool for calculating the maximum value of a specified column in a given spreadsheet.
    Args:
        filename (str): The name of the spreadsheet file.
        column_name (str): The name of the column for which to calculate the maximum value.
    Returns:
        float: The maximum value of the specified column.
    """
    df = _get_spreadsheet(filename)
    try:
        return f"Maximum value in column '{column_name}': {df[column_name].max()}"
    except KeyError:
        return f"Column '{column_name}' not found in file '{filename}'."

def get_sum_in_column_impl(filename: str, column_name: str) -> float:
    """
    Tool for calculating the sum of a specified column in a given spreadsheet.
    Args:
        filename (str): The name of the spreadsheet file.
        column_name (str): The name of the column for which to calculate the sum.
    Returns:
        float: The sum of the specified column.
    """
    df = _get_spreadsheet(filename)
    try:
        return f"Sum of values in column '{column_name}': {df[column_name].sum()}"
    except KeyError:
        return f"Column '{column_name}' not found in file '{filename}'."

def get_sum_of_filtered_values_impl(filename: str, column_name: str, keyword: str) -> float:
    """
    Tool for calculating the sum of values in a specified column that match a keyword in a given spreadsheet.
    Args:
        filename (str): The name of the spreadsheet file.
        column_name (str): The name of the column to sum values in.
        keyword (str): The keyword to filter rows by before summing.
    Returns:
        float: The sum of the values in the specified column for rows that match the keyword.
    """
    df = _get_spreadsheet(filename)
    try:
        count = (df[column_name] == keyword).sum()
        return f"Sum of values in column '{column_name}' for rows containing '{keyword}': {count}"
    except KeyError:
        return f"Column '{column_name}' not found in file '{filename}'."

def filter_values_in_range_impl(filename: str, column_name: str, min_value: float, max_value: float) -> str:
    """
    Tool for filtering rows in a specified column that fall within a given numeric range in a spreadsheet.
    Args:
        filename (str): The name of the spreadsheet file.
        column_name (str): The name of the column to filter.
        min_value (float): The minimum value of the range.
        max_value (float): The maximum value of the range.
    Returns:
        str: A string representation of the rows that match the filter criteria.
    """
    df = _get_spreadsheet(filename)
    try:
        filtered_df = df[(df[column_name] >= min_value) & (df[column_name] <= max_value)]
        if len(filtered_df) == 0:
            return f"No rows found in file '{filename}' with values in column '{column_name}' between {min_value} and {max_value}."
        elif filtered_df.size > 200:
            reduced_df = filtered_df.head(min(10, len(filtered_df)))
            return f"Data too large, showing first ~10 rows:\n{reduced_df.to_string()}\nUse narrower range to reduce results."
        return filtered_df.to_string()
    except KeyError:
        return f"Column '{column_name}' not found in file '{filename}'."