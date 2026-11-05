from pathlib import Path

import polars as pl
import pytest

from data_repair_copilot.csv_loader import load_csv
from data_repair_copilot.detectors.duplicates import detect_duplicates


def test_exact_rows() -> None:
    frame = pl.DataFrame(
        {"id": ["001", "001", "001", "002", "002"], "v": ["A", "A", "a", None, None]}
    )
    result = detect_duplicates(frame)
    assert [x.row_indices for x in result.duplicate_rows] == [[0, 1], [3, 4]]
    assert result.duplicate_ids == []
    assert frame["v"].to_list() == ["A", "A", "a", None, None]


def test_duplicate_ids() -> None:
    frame = pl.DataFrame({"id": ["001", "1", "001", "", "", None, None, "A", "a"]})
    result = detect_duplicates(frame, id_column="id")
    assert [x.row_indices for x in result.duplicate_ids] == [[0, 2]]
    assert [x.row_indices for x in result.duplicate_rows] == [[0, 2], [3, 4], [5, 6]]
    assert result.id_column == "id"


def test_boundaries() -> None:
    empty = pl.DataFrame(schema={"id": pl.String})
    assert detect_duplicates(empty, id_column="id").duplicate_ids == []
    assert detect_duplicates(pl.DataFrame()).duplicate_rows == []
    with pytest.raises(ValueError, match="Unknown ID column"):
        detect_duplicates(empty, id_column="unknown")
    frame = pl.DataFrame({"__duplicate_row_index": [1, 1], "id": ["0", "0"]})
    result = detect_duplicates(frame, id_column="id")
    assert result.duplicate_rows[0].row_indices == [0, 1]
    assert result.duplicate_ids[0].row_indices == [0, 1]


def test_csv_integration(tmp_path: Path) -> None:
    path = tmp_path / "input.csv"
    raw = b"id,value\n001,red\n001,red\n1,red\n001,blue\n"
    path.write_bytes(raw)
    frame = load_csv(path)
    result = detect_duplicates(frame, id_column="id")
    assert [x.row_indices for x in result.duplicate_rows] == [[0, 1]]
    assert [x.row_indices for x in result.duplicate_ids] == [[0, 1, 3]]
    assert frame["id"].to_list() == ["001", "001", "1", "001"]
    assert path.read_bytes() == raw
