from pathlib import Path
import json
from typing import Optional, Tuple
import pandas as pd
from src.supabase_interface import download_supabase_file
from city_agent.error_codes import ErrorCode


def _normalize_for_json(value):
    """Convert pandas/numpy/NaN values into JSON-safe Python primitives."""
    if isinstance(value, dict):
        return {str(k): _normalize_for_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_normalize_for_json(v) for v in value]
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def _format_rows_for_output(df: pd.DataFrame) -> pd.DataFrame:
    """Present rows using spreadsheet-style numbering (header row = 1).
    This fixes the off by 2 error seen in results"""
    formatted_df = df.copy()
    formatted_df.index = formatted_df.index + 2
    formatted_df.index.name = "row"
    return formatted_df


def _tool_success(tool_name: str, data: dict) -> str:
    """Return a structured, non-throwing success payload."""
    payload = {
        "status": "success",
        "tool": tool_name,
        "data": _normalize_for_json(data),
        "error": None,
    }
    return json.dumps(
        payload,
        ensure_ascii=True,
    )


def _tool_error(
    message: str,
    tool_name: str = "unknown",
    code: str = ErrorCode.TOOL_EXECUTION_ERROR.value,
) -> str:
    """Return a structured, non-throwing error payload."""
    payload = {
        "status": "error",
        "tool": tool_name,
        "data": None,
        "error": {
            "code": code,
            "message": message,
        },
    }
    return json.dumps(
        _normalize_for_json(payload),
        ensure_ascii=True,
    )


def _column_not_found_error(filename: str, column_name: str, tool_name: str) -> str:
    return _tool_error(
        f"Column '{column_name}' not found in file '{filename}'.",
        tool_name=tool_name,
        code=ErrorCode.COLUMN_NOT_FOUND.value,
    )


def _sheet_not_found_error(filename: str, sheet_name: str, tool_name: str) -> str:
    return _tool_error(
        f"Sheet '{sheet_name}' not found in file '{filename}'.",
        tool_name=tool_name,
        code=ErrorCode.READ_FAILURE.value,
    )


def _get_column(
    df: pd.DataFrame, filename: str, column_name: str, tool_name: str
) -> Tuple[Optional[pd.Series], Optional[str]]:
    if column_name not in df.columns:
        return None, _column_not_found_error(filename, column_name, tool_name)
    return df[column_name], None


def _get_spreadsheet(
    filename: str,
    sheet_name: Optional[str] = None,
    target_column: Optional[str] = None,
    get_info: bool = False,
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Helper function to read a spreadsheet file (CSV or XLSX) into a pandas DataFrame.
    Args:
        filename (str): The name of the spreadsheet file to read.
        sheet_name (Optional[str]): The name of the sheet to read. If None, reads the first sheet. Only applicable for XLSX files.
        target_column (Optional[str]): The name of the column to filter for. Used for identifying the specific sheet
        get_info (bool): For the get_spreadsheet_info tool to explain if there are multiple sheets
    Returns:
        Tuple[Optional[pd.DataFrame], Optional[str]]: DataFrame on success, error text on failure.
    """
    if isinstance(sheet_name, str):
        sheet_name = sheet_name.strip() or None

    if not filename.endswith(".csv") and not filename.endswith(".xlsx"):
        return None, _tool_error(
            f"Unsupported file type for file '{filename}'. Only .csv and .xlsx files are supported.",
            tool_name="spreadsheet",
            code=ErrorCode.UNSUPPORTED_FILE_TYPE.value,
        )

    try:
        db_file_info = download_supabase_file(filename, "documents")
        # db_file_info[0] is the local file path of the downloaded file
        if db_file_info[0].endswith(".csv"):
            return pd.read_csv(db_file_info[0], encoding="cp1252"), None
        if db_file_info[0].endswith(".xlsx"):
            xls = pd.ExcelFile(db_file_info[0])
            if sheet_name and sheet_name not in xls.sheet_names:
                return None, _sheet_not_found_error(filename, sheet_name, "spreadsheet")
            if get_info:
                # Attach workbook-level info while returning a standard (df, error) tuple.
                sheet_rows = {sheet: len(xls.parse(sheet)) for sheet in xls.sheet_names}
                selected_sheet = sheet_name or xls.sheet_names[0]
                selected_df = xls.parse(selected_sheet)
                selected_df.attrs["sheet_info"] = {
                    "sheet_names": sheet_rows,
                    "selected_sheet": selected_sheet,
                }
                return selected_df, None
            if sheet_name:
                return xls.parse(sheet_name), None
            if target_column:
                # If a target column is specified, we need to find which sheet it is in.
                for workbook_sheet_name in xls.sheet_names:
                    df = xls.parse(workbook_sheet_name)
                    if target_column in df.columns:
                        return df, None
                return None, _tool_error(
                    f"Column '{target_column}' not found in any sheet of file '{filename}'.",
                    tool_name="spreadsheet",
                    code=ErrorCode.COLUMN_NOT_FOUND.value,
                )
            return xls.parse(xls.sheet_names[0]), None
        return None, _tool_error(
            f"Downloaded file '{filename}' is not a supported spreadsheet type.",
            tool_name="spreadsheet",
            code=ErrorCode.UNSUPPORTED_DOWNLOADED_TYPE.value,
        )
    except FileNotFoundError:
        return None, _tool_error(
            f"File not found: {filename}. Retry with an exact filename from search_data results.",
            tool_name="spreadsheet",
            code=ErrorCode.FILE_NOT_FOUND.value,
        )
    except Exception as e:
        return None, _tool_error(
            f"Error reading file '{filename}': {str(e)}. Retry once; if it persists, try another file.",
            tool_name="spreadsheet",
            code=ErrorCode.READ_FAILURE.value,
        )


def get_spreadsheet_info_impl(filename: str, sheet_name: Optional[str] = None) -> str:
    """
    Tool for retrieving basic information about a spreadsheet
    Args:
        filename (str): The name of the spreadsheet file.

    Returns:
        str: A string representation of the head and first 5 rows of the spreadsheet.
    """
    df, error = _get_spreadsheet(filename, sheet_name=sheet_name, get_info=True)
    if error:
        return error
    additional_info = df.attrs.get("sheet_info") if hasattr(df, "attrs") else None
    preview_df = _format_rows_for_output(df.head())
    return _tool_success(
        "get_spreadsheet_info",
        {
            "filename": filename,
            "additional_info": additional_info,
            "preview": preview_df.to_string(),
        },
    )


def get_mean_impl(
    filename: str, column_name: str, sheet_name: Optional[str] = None
) -> str:
    """
    Tool for calculating the mean of a specified column in a given spreadsheet.
    Args:
        filename (str): The name of the spreadsheet file.
        column_name (str): The name of the column for which to calculate the mean.
    Returns:
        str: The mean value of the specified column.
    """
    df, error = _get_spreadsheet(
        filename, sheet_name=sheet_name, target_column=column_name
    )
    if error:
        return error
    column, error = _get_column(df, filename, column_name, "get_mean")
    if error:
        return error
    return _tool_success(
        "get_mean",
        {
            "filename": filename,
            "column": column_name,
            "mean": column.mean(),
        },
    )


def filter_values_impl(
    filename: str,
    columns: list,
    keyword: str,
    sheet_name: Optional[str] = None,
) -> str:
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
    df, error = _get_spreadsheet(
        filename,
        sheet_name=sheet_name,
        target_column=columns[0] if columns else None,
    )
    if error:
        return error
    missing_columns = [column for column in columns if column not in df.columns]
    if missing_columns:
        return _tool_error(
            f"Column not found in file '{filename}': {missing_columns}",
            tool_name="filter_values",
            code=ErrorCode.COLUMN_NOT_FOUND.value,
        )

    specific_info_df = df[columns]
    # Use vectorized matching across selected columns instead of row-wise apply.
    mask = (
        specific_info_df.astype(str)
        .apply(lambda col: col.str.contains(keyword, case=False, na=False, regex=False))
        .any(axis=1)
    )
    specific_info_df = specific_info_df[mask]

    if len(specific_info_df) == 0:
        return _tool_success(
            "filter_values",
            {
                "filename": filename,
                "columns": columns,
                "keyword": keyword,
                "row_count": 0,
                "result": "",
                "truncated": False,
            },
        )
    if specific_info_df.size > 200:
        reduced_df = _format_rows_for_output(
            specific_info_df.head(min(10, len(specific_info_df)))
        )
        return _tool_success(
            "filter_values",
            {
                "filename": filename,
                "columns": columns,
                "keyword": keyword,
                "row_count": len(specific_info_df),
                "result": reduced_df.to_string(),
                "truncated": True,
                "message": "Use more specific keywords or fewer columns to narrow down results.",
            },
        )
    specific_info_df = _format_rows_for_output(specific_info_df)
    return _tool_success(
        "filter_values",
        {
            "filename": filename,
            "columns": columns,
            "keyword": keyword,
            "row_count": len(specific_info_df),
            "result": specific_info_df.to_string(),
            "truncated": False,
        },
    )


def get_unique_values_impl(
    filename: str, column_name: str, sheet_name: Optional[str] = None
) -> str:
    """
    Tool for retrieving unique values from a specified column in a given spreadsheet.
    Args:
        filename (str): The name of the spreadsheet file.
        column_name (str): The name of the column for which to retrieve unique values.
    Returns:
        str: A string representation of the unique values in the specified column.
    """
    df, error = _get_spreadsheet(
        filename, sheet_name=sheet_name, target_column=column_name
    )
    if error:
        return error
    column, error = _get_column(df, filename, column_name, "get_unique_values")
    if error:
        return error
    unique_values = column.unique()
    if len(unique_values) > 20:
        unique_values = unique_values[:20]
        return _tool_success(
            "get_unique_values",
            {
                "filename": filename,
                "column": column_name,
                "unique_values": unique_values.tolist(),
                "truncated": True,
            },
        )
    return _tool_success(
        "get_unique_values",
        {
            "filename": filename,
            "column": column_name,
            "unique_values": unique_values.tolist(),
            "truncated": False,
        },
    )


def count_values_impl(
    filename: str, column_name: str, sheet_name: Optional[str] = None
) -> str:
    """
    Tool for counting occurrences of each unique value in a specified column of a given spreadsheet.
    Args:
        filename (str): The name of the spreadsheet file.
        column_name (str): The name of the column to count values in.
    Returns:
        str: A string representation of the count of each unique value in the specified column.
    """
    df, error = _get_spreadsheet(
        filename, sheet_name=sheet_name, target_column=column_name
    )
    if error:
        return error
    column, error = _get_column(df, filename, column_name, "count_values")
    if error:
        return error
    value_counts = column.value_counts()
    return _tool_success(
        "count_values",
        {
            "filename": filename,
            "column": column_name,
            "value_counts": value_counts.to_dict(),
        },
    )


def get_min_in_column_impl(
    filename: str, column_name: str, sheet_name: Optional[str] = None
) -> str:
    """
    Tool for calculating the minimum value of a specified column in a given spreadsheet.
    Args:
        filename (str): The name of the spreadsheet file.
        column_name (str): The name of the column for which to calculate the minimum value.
    Returns:
        str: The minimum value of the specified column.
    """
    df, error = _get_spreadsheet(
        filename, sheet_name=sheet_name, target_column=column_name
    )
    if error:
        return error
    column, error = _get_column(df, filename, column_name, "get_min_in_column")
    if error:
        return error
    return _tool_success(
        "get_min_in_column",
        {
            "filename": filename,
            "column": column_name,
            "minimum": column.min(),
        },
    )


def get_max_in_column_impl(
    filename: str, column_name: str, sheet_name: Optional[str] = None
) -> str:
    """
    Tool for calculating the maximum value of a specified column in a given spreadsheet.
    Args:
        filename (str): The name of the spreadsheet file.
        column_name (str): The name of the column for which to calculate the maximum value.
    Returns:
        str: The maximum value of the specified column.
    """
    df, error = _get_spreadsheet(
        filename, sheet_name=sheet_name, target_column=column_name
    )
    if error:
        return error
    column, error = _get_column(df, filename, column_name, "get_max_in_column")
    if error:
        return error
    return _tool_success(
        "get_max_in_column",
        {
            "filename": filename,
            "column": column_name,
            "maximum": column.max(),
        },
    )


def get_sum_in_column_impl(
    filename: str, column_name: str, sheet_name: Optional[str] = None
) -> str:
    """
    Tool for calculating the sum of a specified column in a given spreadsheet.
    Args:
        filename (str): The name of the spreadsheet file.
        column_name (str): The name of the column for which to calculate the sum.
    Returns:
        str: The sum of the specified column.
    """
    df, error = _get_spreadsheet(
        filename, sheet_name=sheet_name, target_column=column_name
    )
    if error:
        return error
    column, error = _get_column(df, filename, column_name, "get_sum_in_column")
    if error:
        return error
    return _tool_success(
        "get_sum_in_column",
        {
            "filename": filename,
            "column": column_name,
            "sum": column.sum(),
        },
    )


def get_sum_of_filtered_values_impl(
    filename: str,
    column_name: str,
    keyword: str,
    filter_column: Optional[str] = None,
    sheet_name: Optional[str] = None,
) -> str:
    """
    Tool for calculating the sum of values in a specified column after filtering rows by keyword.
    Args:
        filename (str): The name of the spreadsheet file.
        column_name (str): The name of the column to sum values in.
        keyword (str): The keyword to filter rows by before summing.
        filter_column (Optional[str]): The column to apply keyword filtering on.
            If omitted, falls back to legacy all-column matching.
    Returns:
        str: The sum of the values in the specified column for rows that match the keyword.
    """
    df, error = _get_spreadsheet(
        filename, sheet_name=sheet_name, target_column=column_name
    )
    if error:
        return error
    column, error = _get_column(df, filename, column_name, "get_sum_of_filtered_values")
    if error:
        return error

    if filter_column:
        filter_series, error = _get_column(
            df, filename, filter_column, "get_sum_of_filtered_values"
        )
        if error:
            return error
        mask = filter_series.astype(str).str.contains(
            keyword, case=False, na=False, regex=False
        )
        matched_on = filter_column
    else:
        # Backward-compatible fallback for existing 3-argument calls.
        mask = (
            df.astype(str)
            .apply(
                lambda col: col.str.contains(keyword, case=False, na=False, regex=False)
            )
            .any(axis=1)
        )
        matched_on = "all_columns"
    filtered_df = df[mask]

    if filtered_df.empty:
        return _tool_success(
            "get_sum_of_filtered_values",
            {
                "filename": filename,
                "sum_column": column_name,
                "keyword": keyword,
                "matched_on": matched_on,
                "match_count": 0,
                "numeric_match_count": 0,
                "sum": 0,
            },
        )

    numeric_values = pd.to_numeric(filtered_df[column_name], errors="coerce")
    numeric_match_count = int(numeric_values.notna().sum())
    if numeric_match_count == 0 and len(filtered_df) > 0:
        return _tool_error(
            f"Column '{column_name}' has no numeric values in matched rows.",
            tool_name="get_sum_of_filtered_values",
            code=ErrorCode.NON_NUMERIC_SUM_COLUMN.value,
        )
    total_sum = numeric_values.sum()

    return _tool_success(
        "get_sum_of_filtered_values",
        {
            "filename": filename,
            "sum_column": column_name,
            "keyword": keyword,
            "matched_on": matched_on,
            "match_count": len(filtered_df),
            "numeric_match_count": numeric_match_count,
            "sum": total_sum,
        },
    )


def filter_values_in_range_impl(
    filename: str,
    column_name: str,
    min_value: float,
    max_value: float,
    sheet_name: Optional[str] = None,
) -> str:
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
    df, error = _get_spreadsheet(
        filename, sheet_name=sheet_name, target_column=column_name
    )
    if error:
        return error
    column, error = _get_column(df, filename, column_name, "filter_values_in_range")
    if error:
        return error
    filtered_df = df[(column >= min_value) & (column <= max_value)]
    if len(filtered_df) == 0:
        return _tool_success(
            "filter_values_in_range",
            {
                "filename": filename,
                "column": column_name,
                "min_value": min_value,
                "max_value": max_value,
                "row_count": 0,
                "result": "",
                "truncated": False,
            },
        )
    if filtered_df.size > 200:
        reduced_df = _format_rows_for_output(
            filtered_df.head(min(10, len(filtered_df)))
        )
        return _tool_success(
            "filter_values_in_range",
            {
                "filename": filename,
                "column": column_name,
                "min_value": min_value,
                "max_value": max_value,
                "row_count": len(filtered_df),
                "result": reduced_df.to_string(),
                "truncated": True,
                "message": "Use narrower range to reduce results.",
            },
        )
    filtered_df = _format_rows_for_output(filtered_df)
    return _tool_success(
        "filter_values_in_range",
        {
            "filename": filename,
            "column": column_name,
            "min_value": min_value,
            "max_value": max_value,
            "row_count": len(filtered_df),
            "result": filtered_df.to_string(),
            "truncated": False,
        },
    )


def purge_cached_files():
    """
    Utility function to clear cached files in the /tmp directory.
    """
    tmp_dir = Path("/tmp")
    for file in tmp_dir.glob("tmp*"):
        if str(file).endswith((".csv", ".xlsx", ".pdf", ".xls", ".docx")):
            try:
                file.unlink()
            except Exception:
                # Not dealing with this error, this can be ignored for the most part
                continue
