"""Report explicit missing values and potential zero/missing ambiguity."""

from collections.abc import Collection
from typing import Literal

import polars as pl
from pydantic import BaseModel, Field


class MissingColumnResult(BaseModel):
    column: str
    missing_row_indices: list[int] = Field(default_factory=list)
    zero_row_indices: list[int] = Field(default_factory=list)
    classification: Literal["suspected_null_zero_ambiguity", "no_suspected_ambiguity"]


class MissingReport(BaseModel):
    row_count: int
    columns: list[MissingColumnResult]


def detect_missing(
    frame: pl.DataFrame,
    *,
    missing_markers: Collection[str] = ("",),
    zero_check_columns: Collection[str] = (),
) -> MissingReport:
    """Report 0-based data-row positions without changing source values.

    Actual nulls always count. Text markers match exactly; by default only an
    empty string is a marker. Zero checks are opt-in and recognize numeric zero
    and the exact string '0'. Coexistence signals uncertainty, not a repair.
    """
    if isinstance(missing_markers, str) or any(not isinstance(x, str) for x in missing_markers):
        raise ValueError("missing_markers must be a collection of strings")
    if isinstance(zero_check_columns, str):
        raise ValueError("zero_check_columns must be a collection of column names")
    markers = set(missing_markers)
    selected = set(zero_check_columns)
    unknown = selected.difference(frame.columns)
    if unknown:
        raise ValueError(f"Unknown zero-check columns: {', '.join(sorted(unknown))}")
    results = []
    for column in frame:
        missing, zeros = [], []
        for index, value in enumerate(column):
            if value is None or (isinstance(value, str) and value in markers):
                missing.append(index)
            elif column.name in selected and (
                value == "0"
                or (isinstance(value, (int, float)) and not isinstance(value, bool) and value == 0)
            ):
                zeros.append(index)
        results.append(
            MissingColumnResult(
                column=column.name,
                missing_row_indices=missing,
                zero_row_indices=zeros,
                classification=(
                    "suspected_null_zero_ambiguity"
                    if missing and zeros
                    else "no_suspected_ambiguity"
                ),
            )
        )
    return MissingReport(row_count=frame.height, columns=results)
