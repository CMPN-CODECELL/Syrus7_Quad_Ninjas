import os
import pytest
from pathlib import Path
from data_loader import (
    get_dataset_path,
    validate_dataset_exists,
    load_dataset,
    get_dataset_info,
    DatasetNotFoundError,
    PROJECT_ROOT,
    DEFAULT_DATASET_FILENAME
)


def test_get_dataset_path_default():
    path = get_dataset_path()
    assert path == PROJECT_ROOT / DEFAULT_DATASET_FILENAME
    assert path.name == "hackathon_hospital_bottleneck_dataset.xlsx"


def test_validate_dataset_exists_success():
    path = validate_dataset_exists()
    assert path.is_file()


def test_load_dataset_loads_all_worksheets():
    hourly_df, sheets_dict = load_dataset()
    assert len(hourly_df) == 17544
    assert len(hourly_df.columns) == 55
    assert set(sheets_dict.keys()) == {
        "Hourly_Data", "Data_Dictionary", "Refresh_Design", "Dashboard_Sample"
    }


def test_load_dataset_returns_deep_copies():
    df1, _ = load_dataset()
    df1.drop(columns=["timestamp"], inplace=True)

    df2, _ = load_dataset()
    assert "timestamp" in df2.columns
    assert len(df2.columns) == 55


def test_get_dataset_info_quality_report():
    info = get_dataset_info()
    assert info["exists"] is True
    assert info["filename"] == DEFAULT_DATASET_FILENAME
    assert info["row_count"] == 17544
    assert info["column_count"] == 55
    assert info["duplicate_timestamps"] == 0
    assert info["timestamp_min"] == "2024-01-01T00:00:00"
    assert info["timestamp_max"] == "2025-12-31T23:00:00"
    assert info["data_quality_status"] == "VALID"


def test_dataset_not_found_error_raised_when_file_missing(monkeypatch, tmp_path):
    fake_path = tmp_path / "non_existent_file.xlsx"
    monkeypatch.setenv("DATASET_PATH", str(fake_path))

    with pytest.raises(DatasetNotFoundError) as exc_info:
        validate_dataset_exists()

    err_msg = str(exc_info.value)
    assert "Required dataset file not found" in err_msg
    assert DEFAULT_DATASET_FILENAME in err_msg
