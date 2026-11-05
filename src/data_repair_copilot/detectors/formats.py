"""Report mismatches against explicitly selected, narrow format policies."""

import re
from collections.abc import Collection, Mapping
from datetime import date
from typing import Literal

import polars as pl
from pydantic import BaseModel, Field

FormatKind = Literal["email", "iso_date", "us_phone", "us_zip"]
_EMAIL = re.compile(
    r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+",
    re.ASCII,
)
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", re.ASCII)
_PHONE = re.compile(
    r"(?:[0-9]{10}|[0-9]{3}-[0-9]{3}-[0-9]{4}|\([0-9]{3}\) [0-9]{3}-[0-9]{4})", re.ASCII
)
_ZIP = re.compile(r"[0-9]{5}(?:-[0-9]{4})?", re.ASCII)
_KINDS = {"email", "iso_date", "us_phone", "us_zip"}


class FormatIssue(BaseModel):
    row_index: int
    reason: Literal["format_mismatch", "non_string_value"]


class FormatColumnResult(BaseModel):
    column: str
    format_kind: FormatKind
    skipped_missing_count: int
    issues: list[FormatIssue] = Field(default_factory=list)


class FormatReport(BaseModel):
    row_count: int
    columns: list[FormatColumnResult] = Field(default_factory=list)


def _matches(value: str, kind: str) -> bool:
    if kind == "email":
        return bool(_EMAIL.fullmatch(value)) and len(value) <= 254
    if kind == "iso_date":
        if not _DATE.fullmatch(value):
            return False
        try:
            date.fromisoformat(value)
        except ValueError:
            return False
        return True
    if kind == "us_phone":
        return bool(_PHONE.fullmatch(value))
    return bool(_ZIP.fullmatch(value))


def detect_invalid_formats(
    frame: pl.DataFrame,
    *,
    column_formats: Mapping[str, FormatKind],
    missing_markers: Collection[str] = ("",),
) -> FormatReport:
    """Compare raw strings against named policies; row indices are zero-based."""
    if isinstance(missing_markers, str) or any(not isinstance(x, str) for x in missing_markers):
        raise ValueError("missing_markers must be a collection of strings")
    unknown = set(column_formats).difference(frame.columns)
    if unknown:
        raise ValueError(f"Unknown columns: {', '.join(sorted(unknown))}")
    if any(kind not in _KINDS for kind in column_formats.values()):
        raise ValueError("Unsupported format kind")
    markers = set(missing_markers)
    results = []
    for name, kind in column_formats.items():
        issues: list[FormatIssue] = []
        skipped = 0
        for index, value in enumerate(frame[name]):
            if value is None or (isinstance(value, str) and value in markers):
                skipped += 1
            elif not isinstance(value, str):
                issues.append(FormatIssue(row_index=index, reason="non_string_value"))
            elif not _matches(value, kind):
                issues.append(FormatIssue(row_index=index, reason="format_mismatch"))
        results.append(
            FormatColumnResult(
                column=name, format_kind=kind, skipped_missing_count=skipped, issues=issues
            )
        )
    return FormatReport(row_count=frame.height, columns=results)
