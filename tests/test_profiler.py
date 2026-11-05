from pathlib import Path

import polars as pl
import pytest

from data_repair_copilot.csv_loader import load_csv
from data_repair_copilot.profiler import profile_dataframe


def test_profiles_known_values() -> None:
    frame = pl.DataFrame({"id": ["001", "001", "002", None], "number": [1, 2, 2, 3]})
    result = profile_dataframe(frame, sample_limit=2)
    assert (result.row_count, result.column_count) == (4, 2)
    first, second = result.columns
    assert (first.name, first.data_type, first.null_count, first.null_percentage) == (
        "id",
        "String",
        1,
        25.0,
    )
    assert first.unique_count == 2
    assert first.unique_percentage == pytest.approx(2 / 3 * 100)
    assert first.sample_values == ["001", "002"]
    assert second.data_type == "Int64"
    assert (second.null_percentage, second.unique_count, second.unique_percentage) == (0, 3, 75)
    assert second.sample_values == [1, 2]
    assert frame["id"].to_list() == ["001", "001", "002", None]


def test_empty_and_null_only() -> None:
    empty = profile_dataframe(pl.DataFrame(schema={"id": pl.String})).columns[0]
    assert (empty.null_count, empty.null_percentage, empty.unique_count) == (0, None, 0)
    assert (empty.unique_percentage, empty.sample_values) == (None, [])
    nulls = profile_dataframe(pl.DataFrame({"id": [None, None]}, schema={"id": pl.String}))
    col = nulls.columns[0]
    assert (col.null_count, col.null_percentage, col.unique_count) == (2, 100, 0)
    assert (col.unique_percentage, col.sample_values) == (None, [])
    with pytest.raises(ValueError, match="non-negative"):
        profile_dataframe(pl.DataFrame(), sample_limit=-1)


def test_csv_integration(tmp_path: Path) -> None:
    path = tmp_path / "example.csv"
    original = b"id,note\n001,\n001,NULL\n002,NA\n"
    path.write_bytes(original)
    frame = load_csv(path)
    result = profile_dataframe(frame)
    assert (result.row_count, result.column_count) == (3, 2)
    assert result.columns[0].sample_values == ["001", "002"]
    assert result.columns[1].sample_values == ["", "NULL", "NA"]
    assert result.columns[1].null_count == 0
    assert path.read_bytes() == original
