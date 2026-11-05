"""Preview individual CSV cell proposals without applying any changes."""

from collections.abc import Sequence
from typing import Annotated

import polars as pl
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

RowIndex = Annotated[StrictInt, Field(ge=0)]


class CellProposal(BaseModel):
    """A proposed replacement at a zero-based data-row position."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    row_index: RowIndex
    column: str
    proposed_value: str | None

    @field_validator("column")
    @classmethod
    def column_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("column must not be blank")
        return value


class CellPreview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    row_index: RowIndex
    column: str
    before: str | None
    after: str | None


class RepairPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_count: int
    changes: list[CellPreview] = Field(default_factory=list)


def preview_changes(frame: pl.DataFrame, proposals: Sequence[CellProposal]) -> RepairPreview:
    """Compare proposals to a frame; produce no repaired dataset or writes.

    The snapshot is not a stable dataset identifier or authorization to apply
    a repair. Validate it against the current dataset before any later action.
    """
    changes: list[CellPreview] = []
    seen: set[tuple[int, str]] = set()
    for proposal in proposals:
        key = (proposal.row_index, proposal.column)
        if key in seen:
            raise ValueError(
                f"Multiple proposals target row {proposal.row_index} and column {proposal.column!r}"
            )
        seen.add(key)
        if proposal.column not in frame.columns:
            raise ValueError(f"Unknown column: {proposal.column!r}")
        if proposal.row_index >= frame.height:
            raise ValueError(f"Row index out of range: {proposal.row_index}")
        if frame.schema[proposal.column] not in (pl.String, pl.Null):
            raise ValueError("Preview supports only string or null columns")
        changes.append(
            CellPreview(
                row_index=proposal.row_index,
                column=proposal.column,
                before=frame[proposal.column][proposal.row_index],
                after=proposal.proposed_value,
            )
        )
    return RepairPreview(row_count=frame.height, changes=changes)
