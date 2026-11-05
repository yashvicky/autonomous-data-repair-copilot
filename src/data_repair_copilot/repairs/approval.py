"""Review and apply explicit cell decisions to a separate in-memory frame."""

import hashlib
import json
from collections.abc import Sequence
from typing import Annotated, Literal

import polars as pl
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from data_repair_copilot.repairs.preview import CellPreview, CellProposal, preview_changes

Index = Annotated[StrictInt, Field(ge=0)]


class ReviewPacket(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    row_count: Index
    changes: tuple[CellPreview, ...]
    fingerprint: str


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    change_index: Index
    action: Literal["approve", "reject"]


class DecisionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    change_index: Index
    action: Literal["approve", "reject"]
    change: CellPreview


class RepairOutcome(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    dataset: pl.DataFrame
    records: tuple[DecisionRecord, ...]


def _fingerprint(frame: pl.DataFrame, changes: Sequence[CellPreview]) -> str:
    if any(dtype not in (pl.String, pl.Null) for dtype in frame.schema.values()):
        raise ValueError("Review supports only string or null columns")
    document = {
        "columns": [(name, str(dtype)) for name, dtype in frame.schema.items()],
        "rows": frame.rows(),
        "changes": [change.model_dump(mode="json") for change in changes],
    }
    encoded = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def create_review(frame: pl.DataFrame, proposals: Sequence[CellProposal]) -> ReviewPacket:
    """Bind a validated preview to the entire frame's content and schema."""
    preview = preview_changes(frame, proposals)
    if not preview.changes:
        raise ValueError("At least one proposal is required")
    changes = tuple(preview.changes)
    return ReviewPacket(
        row_count=frame.height, changes=changes, fingerprint=_fingerprint(frame, changes)
    )


def apply_decisions(
    frame: pl.DataFrame, review: ReviewPacket, decisions: Sequence[Decision]
) -> RepairOutcome:
    """Apply approved changes to a separate frame; return an in-memory decision log.

    Caller must authenticate the reviewer and persist the returned records.
    The unkeyed fingerprint detects content drift, not fraud or authorization.
    """
    if not review.changes:
        raise ValueError("Review must contain at least one change")
    if (
        frame.height != review.row_count
        or _fingerprint(frame, review.changes) != review.fingerprint
    ):
        raise ValueError("Dataset or reviewed changes differ from the review packet")
    indices = [decision.change_index for decision in decisions]
    if len(indices) != len(review.changes) or set(indices) != set(range(len(review.changes))):
        raise ValueError("Exactly one decision is required for each reviewed change")
    proposals = [
        CellProposal(row_index=c.row_index, column=c.column, proposed_value=c.after)
        for c in review.changes
    ]
    checked = preview_changes(frame, proposals)
    if tuple(checked.changes) != review.changes:
        raise ValueError("Preview no longer matches the dataset")
    actions = {d.change_index: d.action for d in decisions}
    replacements: dict[str, list[str | None]] = {}
    records = []
    for index, change in enumerate(review.changes):
        action = actions[index]
        records.append(DecisionRecord(change_index=index, action=action, change=change))
        if action == "approve":
            values = replacements.setdefault(change.column, frame[change.column].to_list())
            values[change.row_index] = change.after
    dataset = frame.clone()
    if replacements:
        dataset = dataset.with_columns(
            [pl.Series(name, values, dtype=pl.String) for name, values in replacements.items()]
        )
    return RepairOutcome(dataset=dataset, records=tuple(records))
