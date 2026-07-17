"""
utils.py — Helper functions for data parsing and processing.
"""

import io
import base64

import pandas as pd


def parse_upload(contents: str, filename: str) -> pd.DataFrame:
    """Decode a Dash Upload base64 payload and return a DataFrame.

    Supports .csv, .xlsx, and .xls files.
    """
    _, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)

    if filename.endswith(".csv"):
        df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
    elif filename.endswith((".xls", ".xlsx")):
        df = pd.read_excel(io.BytesIO(decoded), engine="openpyxl")
    else:
        raise ValueError("Unsupported file type. Please use .csv, .xlsx, or .xls")

    return df


def try_parse_datetime(series: pd.Series):
    """Return *series* parsed as datetime if ≥90% of non-null values parse, else None."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    if pd.api.types.is_numeric_dtype(series):
        return None

    non_null = series.dropna()
    if non_null.empty:
        return None

    # Bare short numbers ("1", "2024") are codes or years, not dates —
    # dateutil would happily mis-parse them as day-of-current-month.
    as_str = non_null.astype(str)
    if as_str.str.fullmatch(r"\d{1,4}").mean() > 0.5:
        return None

    parsed = pd.to_datetime(non_null, errors="coerce", format="mixed")
    if parsed.notna().sum() / len(non_null) >= 0.9:
        return pd.to_datetime(series, errors="coerce", format="mixed")
    return None


def coerce_datetime_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convert string columns that look like dates into datetime dtype, in place."""
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            continue
        parsed = try_parse_datetime(df[col])
        if parsed is not None:
            df[col] = parsed
    return df
