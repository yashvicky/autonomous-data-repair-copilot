from pathlib import Path

import polars as pl
import pytest

from data_repair_copilot.csv_loader import load_csv
from data_repair_copilot.detectors.missing import detect_missing


def test_missing_markers() -> None:
    frame = pl.DataFrame({"x": [None, "", "NULL", "NA", " "], "y": ["0", "1", "2", "3", "4"]})
    report = detect_missing(frame, missing_markers=("", "NULL"))
    assert report.row_count == 5
    assert report.columns[0].missing_row_indices == [0, 1, 2]
    assert report.columns[0].zero_row_indices == []
    assert report.columns[1].missing_row_indices == []
    assert frame["x"].to_list() == [None, "", "NULL", "NA", " "]


def test_zero_ambiguity() -> None:
    frame = pl.DataFrame({"amount": ["", "0", "00", "0.0", "1"], "id": ["", "0", "00", "A", "B"]})
    report = detect_missing(frame, zero_check_columns=("amount",))
    amount, identifier = report.columns
    assert amount.missing_row_indices == [0]
    assert amount.zero_row_indices == [1]
    assert amount.classification == "suspected_null_zero_ambiguity"
    assert identifier.classification == "no_suspected_ambiguity"
    assert identifier.zero_row_indices == []
    numeric = detect_missing(pl.DataFrame({"n": [0, None, 2]}), zero_check_columns=("n",))
    assert numeric.columns[0].zero_row_indices == [0]
    assert numeric.columns[0].classification == "suspected_null_zero_ambiguity"
    no_missing = detect_missing(pl.DataFrame({"n": [0, 1]}), zero_check_columns=("n",))
    assert no_missing.columns[0].classification == "no_suspected_ambiguity"


def test_csv_integration(tmp_path: Path) -> None:
    source = tmp_path / "test.csv"
    original = b"id,amount\n001,\n002,0\n003,NULL\n"
    source.write_bytes(original)
    frame = load_csv(source)
    report = detect_missing(frame, zero_check_columns=("amount",))
    assert frame["id"].to_list() == ["001", "002", "003"]
    assert frame["amount"].to_list() == ["", "0", "NULL"]
    assert report.columns[1].missing_row_indices == [0]
    assert report.columns[1].zero_row_indices == [1]
    assert source.read_bytes() == original


def test_boundaries() -> None:
    frame = pl.DataFrame(schema={"x": pl.String})
    report = detect_missing(frame, zero_check_columns=("x",))
    assert report.row_count == 0
    assert report.columns[0].missing_row_indices == []
    assert report.columns[0].classification == "no_suspected_ambiguity"
    with pytest.raises(ValueError, match="Unknown"):
        detect_missing(frame, zero_check_columns=("typo",))
    with pytest.raises(ValueError, match="collection of strings"):
        detect_missing(frame, missing_markers="NULL")
    with pytest.raises(ValueError, match="collection of column names"):
        detect_missing(frame, zero_check_columns="x")
    assert (
        detect_missing(pl.DataFrame({"x": ["NULL", "NA", " "]})).columns[0].missing_row_indices
        == []
    )
