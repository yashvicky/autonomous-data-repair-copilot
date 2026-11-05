"""Detect exact duplicate rows and explicitly selected identifiers."""

import polars as pl
from pydantic import BaseModel, Field


class DuplicateGroup(BaseModel):
    row_indices: list[int] = Field(default_factory=list)


class DuplicateReport(BaseModel):
    row_count: int
    id_column: str | None
    duplicate_rows: list[DuplicateGroup] = Field(default_factory=list)
    duplicate_ids: list[DuplicateGroup] = Field(default_factory=list)


def detect_duplicates(frame: pl.DataFrame, *, id_column: str | None = None) -> DuplicateReport:
    """Group exact matches using zero-based row indices; do not change input.

    Entire-row comparisons include nulls. For the explicitly selected ID column,
    null and empty-string IDs are excluded; all other values are compared as-is.
    """
    if id_column is not None and id_column not in frame.columns:
        raise ValueError(f"Unknown ID column: {id_column}")
    if not frame.columns:
        return DuplicateReport(row_count=frame.height, id_column=id_column)
    index_name = "__duplicate_row_index"
    while index_name in frame.columns:
        index_name += "_"
    indexed = frame.with_row_index(index_name)

    def grouped(data: pl.DataFrame, columns: list[str]) -> list[DuplicateGroup]:
        groups = data.group_by(columns, maintain_order=True).agg(pl.col(index_name))
        return [
            DuplicateGroup(row_indices=indices)
            for indices in groups[index_name].to_list()
            if len(indices) > 1
        ]

    rows = grouped(indexed, frame.columns)
    ids = []
    if id_column is not None:
        valid = pl.col(id_column).is_not_null()
        if frame.schema[id_column] == pl.String:
            valid = valid & (pl.col(id_column) != "")
        ids = grouped(indexed.filter(valid), [id_column])
    return DuplicateReport(
        row_count=frame.height, id_column=id_column, duplicate_rows=rows, duplicate_ids=ids
    )
