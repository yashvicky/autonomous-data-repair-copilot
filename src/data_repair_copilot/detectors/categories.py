"""Group suspected category variants with evidence; never modify data."""

from collections.abc import Mapping

import polars as pl
from pydantic import BaseModel, Field


class CategoryVariant(BaseModel):
    value: str
    row_indices: list[int] = Field(default_factory=list)


class CategoryGroup(BaseModel):
    match_key: str
    variants: list[CategoryVariant] = Field(default_factory=list)


class CategoryReport(BaseModel):
    column: str
    row_count: int
    skipped_missing_count: int
    groups: list[CategoryGroup] = Field(default_factory=list)


def _key(value: str) -> str:
    return " ".join(value.split()).casefold()


def detect_category_variants(
    frame: pl.DataFrame,
    *,
    column: str,
    aliases: Mapping[str, str] | None = None,
) -> CategoryReport:
    """Report distinct original values sharing a case/whitespace or alias key.

    Alias keys and targets are strings and are normalized only for comparison.
    Empty or whitespace-only values and nulls are excluded. Row positions are
    zero-based data-row indices. Only explicitly selected string columns work.
    """
    if column not in frame.columns:
        raise ValueError(f"Unknown category column: {column}")
    if frame.schema[column] not in (pl.String, pl.Null):
        raise ValueError("Category column must contain strings or nulls")
    normalized_aliases: dict[str, str] = {}
    for alias, target in (aliases or {}).items():
        if not isinstance(alias, str) or not isinstance(target, str):
            raise ValueError("Aliases and targets must be strings")
        source, destination = _key(alias), _key(target)
        if not source or not destination:
            raise ValueError("Aliases and targets must be non-empty")
        if source in normalized_aliases and normalized_aliases[source] != destination:
            raise ValueError("Conflicting aliases after normalization")
        normalized_aliases[source] = destination
    # Alias chains are ambiguous without an explicit policy; fail rather than
    # silently treating the same canonical name differently across records.
    for source, target in normalized_aliases.items():
        if target in normalized_aliases and normalized_aliases[target] != target:
            raise ValueError(f"Chained aliases are not supported: {source}")
    buckets: dict[str, dict[str, list[int]]] = {}
    skipped = 0
    for index, value in enumerate(frame[column]):
        if value is None or not _key(value):
            skipped += 1
            continue
        normalized = _key(value)
        match_key = normalized_aliases.get(normalized, normalized)
        buckets.setdefault(match_key, {}).setdefault(value, []).append(index)
    groups = [
        CategoryGroup(
            match_key=key,
            variants=[
                CategoryVariant(value=value, row_indices=rows) for value, rows in values.items()
            ],
        )
        for key, values in buckets.items()
        if len(values) > 1
    ]
    return CategoryReport(
        column=column, row_count=frame.height, skipped_missing_count=skipped, groups=groups
    )
