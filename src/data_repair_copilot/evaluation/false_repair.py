"""Evaluate changed cells against an explicitly supplied complete reference."""

from dataclasses import dataclass

import polars as pl


@dataclass(frozen=True)
class CellLocation:
    row_index: int
    column: str


@dataclass(frozen=True)
class FalseRepairReport:
    changed_cells: int
    correct_changes: int
    false_repairs: int
    false_repair_rate: float | None
    incorrect_locations: tuple[CellLocation, ...]


def evaluate_false_repairs(
    before: pl.DataFrame, after: pl.DataFrame, reference: pl.DataFrame
) -> FalseRepairReport:
    """Count changed cells differing from a complete, aligned reference.

    All frames must have identical ordered columns and row counts. The caller
    must verify that row positions refer to the same records and the reference
    contains the correct value for every cell; shape cannot prove alignment or
    reference quality. Only string and null columns are supported. This scores
    actual differences, not approvals, proposals, missed repairs, or row edits.
    """
    if any(
        frame.columns != before.columns or frame.height != before.height
        for frame in (after, reference)
    ):
        raise ValueError("frames must have identical ordered columns and row counts")
    if any(
        dtype not in (pl.String, pl.Null)
        for frame in (before, after, reference)
        for dtype in frame.dtypes
    ):
        raise ValueError("evaluation supports only string or null columns")

    changed = 0
    incorrect = []
    for column in before.columns:
        for row_index, (old, new, expected) in enumerate(
            zip(before[column], after[column], reference[column], strict=True)
        ):
            if old != new:
                changed += 1
                if new != expected:
                    incorrect.append(CellLocation(row_index, column))
    wrong = len(incorrect)
    return FalseRepairReport(
        changed_cells=changed,
        correct_changes=changed - wrong,
        false_repairs=wrong,
        false_repair_rate=wrong / changed if changed else None,
        incorrect_locations=tuple(incorrect),
    )
