"""Dataset Loader and Path Resolution Module for HospAI.

Locates, validates, cleans, and loads the Excel dataset from the project root.
Preserves original Excel file, guarantees copy safety, and handles missing dataset errors.
"""

import os
from pathlib import Path
from functools import lru_cache
from typing import Dict, Any, Tuple
import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_DATASET_FILENAME = "hackathon_hospital_bottleneck_dataset.xlsx"

REQUIRED_COLUMNS = [
    "timestamp", "department", "hour_of_day", "day_of_week", "month",
    "is_weekend", "is_public_holiday", "arrivals_last_hour", "arrivals_last_3h",
    "arrivals_last_6h", "arrivals_last_24h", "arrivals_same_hour_prev_week",
    "occupied_beds", "total_beds", "doctors_on_duty", "nurses_on_duty",
    "patients_awaiting_lab", "patients_awaiting_imaging",
    "actual_arrivals_next_4h", "actual_peak_occupancy_next_4h_pct",
    "actual_max_wait_next_4h_minutes", "actual_overload_next_4h"
]


class DatasetNotFoundError(FileNotFoundError):
    """Raised when the Excel dataset file is missing from the project root."""
    pass


def get_dataset_path() -> Path:
    """Resolves the absolute path to the dataset file.

    Supports override via DATASET_PATH environment variable.
    Defaults to PROJECT_ROOT / hackathon_hospital_bottleneck_dataset.xlsx.
    """
    env_path = os.getenv("DATASET_PATH")
    if env_path:
        path = Path(env_path).resolve()
    else:
        path = PROJECT_ROOT / DEFAULT_DATASET_FILENAME

    return path


def validate_dataset_exists() -> Path:
    """Validates that the dataset file exists at the resolved path.

    Raises DatasetNotFoundError with clear instructions if missing.
    """
    path = get_dataset_path()
    if not path.is_file():
        raise DatasetNotFoundError(
            f"Required dataset file not found at '{path}'. "
            f"Expected filename '{DEFAULT_DATASET_FILENAME}' inside the project root directory '{PROJECT_ROOT}'. "
            f"Please place '{DEFAULT_DATASET_FILENAME}' in the root directory before running HospAI."
        )
    return path


@lru_cache(maxsize=1)
def _raw_load_excel() -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame], Dict[str, Any]]:
    """Internal cached loader that reads Excel sheets and performs data validation."""
    path = validate_dataset_exists()

    excel_file = pd.ExcelFile(path)
    sheet_names = excel_file.sheet_names

    if "Hourly_Data" not in sheet_names:
        raise ValueError(
            f"Excel file at '{path}' is missing the required 'Hourly_Data' worksheet. "
            f"Found sheets: {sheet_names}"
        )

    sheets_dict = {}
    for name in sheet_names:
        sheets_dict[name] = pd.read_excel(excel_file, sheet_name=name)

    hourly_df = sheets_dict["Hourly_Data"]

    # Validate required columns
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in hourly_df.columns]
    if missing_cols:
        raise ValueError(f"Worksheet 'Hourly_Data' is missing required columns: {missing_cols}")

    # Parse timestamps and sort chronologically
    hourly_df["timestamp"] = pd.to_datetime(hourly_df["timestamp"])
    hourly_df = hourly_df.sort_values("timestamp").reset_index(drop=True)

    # Check for duplicate timestamps & continuity
    duplicate_timestamps_count = int(hourly_df["timestamp"].duplicated().sum())

    diffs = hourly_df["timestamp"].diff()
    unexpected_gaps_count = int((diffs > pd.Timedelta(hours=1)).sum())

    quality_summary = {
        "resolved_path": str(path),
        "exists": True,
        "filename": path.name,
        "project_root": str(PROJECT_ROOT),
        "worksheets": sheet_names,
        "primary_sheet": "Hourly_Data",
        "row_count": int(hourly_df.shape[0]),
        "column_count": int(hourly_df.shape[1]),
        "duplicate_timestamps": duplicate_timestamps_count,
        "unexpected_gaps": unexpected_gaps_count,
        "timestamp_min": hourly_df["timestamp"].min().isoformat(),
        "timestamp_max": hourly_df["timestamp"].max().isoformat(),
        "departments": hourly_df["department"].unique().tolist(),
        "data_quality_status": "VALID" if duplicate_timestamps_count == 0 else "WARNING"
    }

    return hourly_df, sheets_dict, quality_summary


def load_dataset() -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """Loads dataset and returns DEEP COPIES to prevent cache corruption."""
    hourly_df, sheets_dict, _ = _raw_load_excel()
    copied_sheets = {k: v.copy() for k, v in sheets_dict.items()}
    return hourly_df.copy(), copied_sheets


def get_dataset_info() -> Dict[str, Any]:
    """Returns detailed metadata and data-quality report for the dataset."""
    path = get_dataset_path()
    if not path.is_file():
        return {
            "resolved_path": str(path),
            "exists": False,
            "error": f"Dataset missing at '{path}'. Expected '{DEFAULT_DATASET_FILENAME}' in project root '{PROJECT_ROOT}'."
        }

    hourly_df, sheets_dict, summary = _raw_load_excel()

    null_counts = hourly_df.isnull().sum()
    columns_with_nulls = null_counts[null_counts > 0].to_dict()

    sheet_info = {}
    for name, df in sheets_dict.items():
        sheet_info[name] = {
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1]),
            "column_names": list(df.columns)
        }

    info = {
        **summary,
        "sheet_details": sheet_info,
        "null_analysis": {
            "total_nulls": int(null_counts.sum()),
            "columns_with_nulls": columns_with_nulls,
            "note": "Exactly 4 target columns have 4 NaN rows at the end of the time series due to 4-hour forward lookahead calculation."
        }
    }
    return info
