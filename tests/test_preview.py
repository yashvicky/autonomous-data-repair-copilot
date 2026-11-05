from pathlib import Path

import polars as pl
import pytest
from pydantic import ValidationError

from data_repair_copilot.csv_loader import load_csv
from data_repair_copilot.repairs.preview import CellProposal, RepairPreview, preview_changes


def test_preview_values() -> None:
    frame = pl.DataFrame({"id": ["001", "002"], "status": [" bad ", None]})
    proposals = [
        CellProposal(row_index=0, column="status", proposed_value="good"),
        CellProposal(row_index=1, column="status", proposed_value=""),
    ]
    result = preview_changes(frame, proposals)
    assert result.row_count == 2
    assert [(c.row_index, c.column, c.before, c.after) for c in result.changes] == [
        (0, "status", " bad ", "good"),
        (1, "status", None, ""),
    ]
    assert frame["status"].to_list() == [" bad ", None]


def test_source_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "input.csv"
    original = b"id,value\r\n001,old\r\n"
    path.write_bytes(original)
    frame = load_csv(path)
    before = frame.clone()
    result = preview_changes(
        frame, [CellProposal(row_index=0, column="value", proposed_value="new")]
    )
    assert (result.changes[0].before, result.changes[0].after) == ("old", "new")
    assert frame.equals(before)
    assert path.read_bytes() == original


def test_invalid_proposals() -> None:
    frame = pl.DataFrame({"s": ["value"], "n": [1]})
    with pytest.raises(ValidationError):
        CellProposal(row_index=-1, column="s", proposed_value="x")
    with pytest.raises(ValidationError):
        CellProposal(row_index=True, column="s", proposed_value="x")
    with pytest.raises(ValidationError):
        CellProposal(row_index=0, column="s", proposed_value=3)
    with pytest.raises(ValueError, match="Unknown column"):
        preview_changes(frame, [CellProposal(row_index=0, column="missing", proposed_value="x")])
    with pytest.raises(ValueError, match="out of range"):
        preview_changes(frame, [CellProposal(row_index=1, column="s", proposed_value="x")])
    with pytest.raises(ValueError, match="only string or null"):
        preview_changes(frame, [CellProposal(row_index=0, column="n", proposed_value="2")])
    proposal = CellProposal(row_index=0, column="s", proposed_value="x")
    with pytest.raises(ValueError, match="Multiple proposals"):
        preview_changes(frame, [proposal, proposal])
    assert frame["s"].to_list() == ["value"]


def test_empty_and_round_trip() -> None:
    frame = pl.DataFrame({"value": ["001"]})
    empty = preview_changes(frame, [])
    assert empty.row_count == 1 and empty.changes == []
    preview = preview_changes(
        frame, [CellProposal(row_index=0, column="value", proposed_value=None)]
    )
    assert RepairPreview.model_validate_json(preview.model_dump_json()) == preview
    assert preview.changes[0].after is None
