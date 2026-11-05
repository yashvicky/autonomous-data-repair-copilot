from pathlib import Path

import polars as pl
import pytest

from data_repair_copilot.csv_loader import load_csv
from data_repair_copilot.detectors.categories import detect_category_variants


def test_variants_and_evidence() -> None:
    frame = pl.DataFrame(
        {"status": ["Active", " active ", "ACTIVE", "Pending", "Active", "INACTIVE"]}
    )
    report = detect_category_variants(frame, column="status")
    assert report.row_count == 6 and len(report.groups) == 1
    group = report.groups[0]
    assert group.match_key == "active"
    assert [(v.value, v.row_indices) for v in group.variants] == [
        ("Active", [0, 4]),
        (" active ", [1]),
        ("ACTIVE", [2]),
    ]
    assert frame["status"][1] == " active "


def test_explicit_aliases() -> None:
    frame = pl.DataFrame({"country": ["US", "United States", "U.S.", "CA", "Canada"]})
    assert detect_category_variants(frame, column="country").groups == []
    result = detect_category_variants(
        frame, column="country", aliases={"US": "United States", "U.S.": "United States"}
    )
    assert len(result.groups) == 1
    assert [v.value for v in result.groups[0].variants] == ["US", "United States", "U.S."]
    assert [v.row_indices for v in result.groups[0].variants] == [[0], [1], [2]]


def test_boundaries() -> None:
    frame = pl.DataFrame({"state": [None, "", "  ", "TX", " TX "]})
    report = detect_category_variants(frame, column="state")
    assert report.skipped_missing_count == 3 and len(report.groups) == 1
    assert (
        detect_category_variants(pl.DataFrame(schema={"state": pl.String}), column="state").groups
        == []
    )
    with pytest.raises(ValueError, match="Unknown category"):
        detect_category_variants(frame, column="missing")
    with pytest.raises(ValueError, match="strings or nulls"):
        detect_category_variants(pl.DataFrame({"state": [1]}), column="state")
    with pytest.raises(ValueError, match="Conflicting aliases"):
        detect_category_variants(frame, column="state", aliases={"US": "USA", "us": "other"})
    with pytest.raises(ValueError, match="Chained aliases"):
        detect_category_variants(frame, column="state", aliases={"a": "b", "b": "c"})
    with pytest.raises(ValueError, match="non-empty"):
        detect_category_variants(frame, column="state", aliases={" ": "x"})


def test_csv_integration(tmp_path: Path) -> None:
    path = tmp_path / "file.csv"
    data = b"id,state\n001,TX\n002,tx\n003,CA\n"
    path.write_bytes(data)
    frame = load_csv(path)
    report = detect_category_variants(frame, column="state")
    assert [(v.value, v.row_indices) for v in report.groups[0].variants] == [
        ("TX", [0]),
        ("tx", [1]),
    ]
    assert frame["id"].to_list() == ["001", "002", "003"]
    assert path.read_bytes() == data
