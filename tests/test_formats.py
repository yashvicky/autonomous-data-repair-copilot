from pathlib import Path

import polars as pl
import pytest

from data_repair_copilot.csv_loader import load_csv
from data_repair_copilot.detectors.formats import detect_invalid_formats


def test_email_and_date() -> None:
    frame = pl.DataFrame(
        {
            "email": ["a.b+tag@example.com", "no-at.example", "a..b@example.com", ""],
            "date": ["2024-02-29", "2023-02-29", "01/02/2024", None],
        }
    )
    result = detect_invalid_formats(frame, column_formats={"email": "email", "date": "iso_date"})
    assert [issue.row_index for issue in result.columns[0].issues] == [1, 2]
    assert [issue.row_index for issue in result.columns[1].issues] == [1, 2]
    assert [x.skipped_missing_count for x in result.columns] == [1, 1]
    assert frame["date"].to_list()[1] == "2023-02-29"


def test_phone_and_zip() -> None:
    frame = pl.DataFrame(
        {
            "phone": ["2145551234", "214-555-1234", "(214) 555-1234", "+44 20 1234 5678"],
            "zip": ["00501", "12345-6789", "1234", "１２３４５"],
        }
    )
    report = detect_invalid_formats(frame, column_formats={"phone": "us_phone", "zip": "us_zip"})
    assert [x.row_index for x in report.columns[0].issues] == [3]
    assert [x.row_index for x in report.columns[1].issues] == [2, 3]


def test_boundaries() -> None:
    frame = pl.DataFrame({"zip": [12345, None]}, schema={"zip": pl.Int64})
    result = detect_invalid_formats(frame, column_formats={"zip": "us_zip"})
    assert result.columns[0].issues[0].reason == "non_string_value"
    assert result.columns[0].skipped_missing_count == 1
    empty = detect_invalid_formats(
        pl.DataFrame(schema={"zip": pl.String}), column_formats={"zip": "us_zip"}
    )
    assert empty.row_count == 0 and empty.columns[0].issues == []
    with pytest.raises(ValueError, match="Unknown columns"):
        detect_invalid_formats(frame, column_formats={"oops": "us_zip"})
    with pytest.raises(ValueError, match="Unsupported"):
        detect_invalid_formats(frame, column_formats={"zip": "unknown"})  # type: ignore[dict-item]
    with pytest.raises(ValueError, match="collection of strings"):
        detect_invalid_formats(frame, column_formats={}, missing_markers="NULL")
    marked = detect_invalid_formats(
        pl.DataFrame({"x": ["NULL", "bad"]}),
        column_formats={"x": "email"},
        missing_markers=("", "NULL"),
    )
    assert marked.columns[0].skipped_missing_count == 1
    assert [i.row_index for i in marked.columns[0].issues] == [1]


def test_csv_integration(tmp_path: Path) -> None:
    path = tmp_path / "file.csv"
    data = b"id,zip\n001,00501\n002,1234\n003,\n"
    path.write_bytes(data)
    frame = load_csv(path)
    report = detect_invalid_formats(frame, column_formats={"zip": "us_zip"})
    assert [x.row_index for x in report.columns[0].issues] == [1]
    assert report.columns[0].skipped_missing_count == 1
    assert frame["id"].to_list() == ["001", "002", "003"]
    assert path.read_bytes() == data
