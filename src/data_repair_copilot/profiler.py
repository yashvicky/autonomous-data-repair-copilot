"""Deterministic, read-only summaries of column values."""

from typing import Any

import polars as pl
from pydantic import BaseModel, Field


class ColumnProfile(BaseModel):
    name: str
    data_type: str
    null_count: int
    null_percentage: float | None
    unique_count: int
    unique_percentage: float | None
    sample_values: list[Any] = Field(default_factory=list)


class DatasetProfile(BaseModel):
    row_count: int
    column_count: int
    columns: list[ColumnProfile]


def profile_dataframe(frame: pl.DataFrame, *, sample_limit: int = 5) -> DatasetProfile:
    """Return actual types, null and distinct rates, and first distinct samples.

    Null percentage uses all rows as denominator. Unique percentage is the
    number of distinct non-null values divided by non-null rows. Undefined
    percentages are None. Empty strings and text such as 'NULL' are values.
    """
    if sample_limit < 0:
        raise ValueError("sample_limit must be non-negative")
    profiles = []
    for series in frame:
        non_null = series.drop_nulls()
        null_count = series.null_count()
        distinct = non_null.unique(maintain_order=True)
        profiles.append(
            ColumnProfile(
                name=series.name,
                data_type=str(series.dtype),
                null_count=null_count,
                null_percentage=(100 * null_count / frame.height if frame.height else None),
                unique_count=len(distinct),
                unique_percentage=(100 * len(distinct) / len(non_null) if len(non_null) else None),
                sample_values=distinct.head(sample_limit).to_list(),
            )
        )
    return DatasetProfile(row_count=frame.height, column_count=frame.width, columns=profiles)
