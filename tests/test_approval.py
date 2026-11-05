from pathlib import Path

import polars as pl
import pytest
from pydantic import ValidationError

from data_repair_copilot.csv_loader import load_csv
from data_repair_copilot.repairs.approval import Decision, apply_decisions, create_review
from data_repair_copilot.repairs.preview import CellProposal


@pytest.mark.regression
def test_approved_copy_and_rejected_log() -> None:
    frame = pl.DataFrame({"id": ["001", "002"], "value": ["bad", "old"]})
    review = create_review(
        frame,
        [
            CellProposal(row_index=0, column="value", proposed_value="good"),
            CellProposal(row_index=1, column="value", proposed_value="new"),
        ],
    )
    outcome = apply_decisions(
        frame,
        review,
        [Decision(change_index=1, action="reject"), Decision(change_index=0, action="approve")],
    )
    assert outcome.dataset["value"].to_list() == ["good", "old"]
    assert frame["value"].to_list() == ["bad", "old"]
    assert outcome.dataset is not frame
    assert [
        (r.change_index, r.action, r.change.before, r.change.after) for r in outcome.records
    ] == [(0, "approve", "bad", "good"), (1, "reject", "old", "new")]


@pytest.mark.regression
def test_fail_closed() -> None:
    frame = pl.DataFrame({"id": ["001"], "value": ["bad"]})
    proposals = [CellProposal(row_index=0, column="value", proposed_value="good")]
    review = create_review(frame, proposals)
    with pytest.raises(ValueError, match="differ"):
        apply_decisions(
            frame.with_columns(pl.lit("002").alias("id")),
            review,
            [Decision(change_index=0, action="approve")],
        )
    altered = review.model_copy(
        update={"changes": (review.changes[0].model_copy(update={"after": "evil"}),)}
    )
    with pytest.raises(ValueError, match="differ"):
        apply_decisions(frame, altered, [Decision(change_index=0, action="approve")])
    with pytest.raises(ValueError, match="Exactly one"):
        apply_decisions(frame, review, [])
    with pytest.raises(ValueError, match="Exactly one"):
        apply_decisions(frame, review, [Decision(change_index=1, action="approve")])
    with pytest.raises(ValueError, match="At least one"):
        create_review(frame, [])
    with pytest.raises(ValidationError):
        Decision(change_index=0, action="maybe")  # type: ignore[arg-type]
    two = create_review(
        frame, [proposals[0], CellProposal(row_index=0, column="id", proposed_value="003")]
    )
    with pytest.raises(ValueError, match="Exactly one"):
        apply_decisions(
            frame,
            two,
            [Decision(change_index=0, action="approve"), Decision(change_index=0, action="reject")],
        )
    rejected = apply_decisions(frame, review, [Decision(change_index=0, action="reject")])
    assert rejected.dataset.equals(frame)
    assert rejected.records[0].action == "reject"
    assert frame["value"].to_list() == ["bad"]


def test_source_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "input.csv"
    raw = b"id,value\n001,old\n002,\n"
    path.write_bytes(raw)
    frame = load_csv(path)
    review = create_review(
        frame,
        [
            CellProposal(row_index=0, column="value", proposed_value=None),
            CellProposal(row_index=1, column="value", proposed_value="new"),
        ],
    )
    outcome = apply_decisions(
        frame,
        review,
        [Decision(change_index=0, action="approve"), Decision(change_index=1, action="reject")],
    )
    assert outcome.dataset["value"].to_list() == [None, ""]
    assert frame["value"].to_list() == ["old", ""]
    assert path.read_bytes() == raw
