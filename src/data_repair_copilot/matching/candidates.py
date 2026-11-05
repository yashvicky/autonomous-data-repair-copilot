"""Generate bounded candidate pairs using exact, explicit blocking keys."""

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations

import polars as pl


@dataclass(frozen=True, order=True)
class CandidatePair:
    """Zero-based positions in the exact input frame, not stable record IDs."""

    left_row: int
    right_row: int


def generate_candidates(
    frame: pl.DataFrame, *, block_columns: Sequence[str], max_pairs: int = 10_000
) -> list[CandidatePair]:
    """Generate same-key pairs; no match decisions or data mutation occur.

    Every selected column must match exactly. Rows with null or whitespace-only
    values in any selected key are excluded. Other strings are not normalized.
    If the complete pair count exceeds max_pairs, raise before making pairs.
    Candidate positions are only valid for the input frame in its current order.
    """
    if isinstance(block_columns, (str, bytes)) or not block_columns:
        raise ValueError("block_columns must be a non-empty sequence of column names")
    if any(not isinstance(name, str) or not name.strip() for name in block_columns):
        raise ValueError("block columns must be nonblank strings")
    if len(set(block_columns)) != len(block_columns):
        raise ValueError("block columns must be unique")
    if type(max_pairs) is not int or max_pairs < 0:
        raise ValueError("max_pairs must be a non-negative integer")
    if any(name not in frame.columns for name in block_columns):
        raise ValueError("unknown blocking column")
    if any(frame.schema[name] not in (pl.String, pl.Null) for name in block_columns):
        raise ValueError("blocking columns must contain strings or nulls")

    groups: dict[tuple[str, ...], list[int]] = {}
    for row_index, key in enumerate(frame.select(block_columns).iter_rows()):
        if any(value is None or not value.strip() for value in key):
            continue
        groups.setdefault(key, []).append(row_index)

    pair_count = sum(len(group) * (len(group) - 1) // 2 for group in groups.values())
    if pair_count > max_pairs:
        raise ValueError(f"candidate pair count {pair_count} exceeds limit {max_pairs}")
    return sorted(
        CandidatePair(left, right)
        for group in groups.values()
        for left, right in combinations(group, 2)
    )
