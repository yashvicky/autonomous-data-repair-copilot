"""Build and export caller-attested local audit reports."""

import os
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from data_repair_copilot.repairs.approval import DecisionRecord, ReviewPacket

Confidence = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class DecisionMetadata(BaseModel):
    """Caller-supplied decision context; confidence is optional but explicit."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    reason: str
    confidence: Confidence | None
    approver: str

    @field_validator("reason", "approver")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class AuditEntry(BaseModel):
    change_index: int
    row_index: int
    column: str
    action: Literal["approve", "reject"]
    original: str | None
    replacement: str | None
    reason: str
    confidence: Confidence | None
    approver: str


class AuditReport(BaseModel):
    schema_version: Literal[1] = 1
    generated_at: datetime
    review_fingerprint: str
    entries: list[AuditEntry]


def build_audit_report(
    review: ReviewPacket,
    records: Sequence[DecisionRecord],
    metadata: Mapping[int, DecisionMetadata],
    *,
    generated_at: datetime | None = None,
) -> AuditReport:
    """Construct an audit document; identity and accuracy are caller-attested."""
    count = len(review.changes)
    if not count:
        raise ValueError("Review has no changes")
    indices = [record.change_index for record in records]
    if len(indices) != count or set(indices) != set(range(count)):
        raise ValueError("Exactly one decision record per reviewed change is required")
    if set(metadata) != set(range(count)) or any(type(key) is not int for key in metadata):
        raise ValueError("Metadata is required for every reviewed change")
    timestamp = generated_at if generated_at is not None else datetime.now(timezone.utc)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("generated_at must include a timezone")
    entries = []
    for record in sorted(records, key=lambda item: item.change_index):
        if record.change != review.changes[record.change_index]:
            raise ValueError("Decision record does not match the reviewed change")
        details = metadata[record.change_index]
        if not isinstance(details, DecisionMetadata):
            raise ValueError("Each metadata entry must be DecisionMetadata")
        change = record.change
        entries.append(
            AuditEntry(
                change_index=record.change_index,
                row_index=change.row_index,
                column=change.column,
                action=record.action,
                original=change.before,
                replacement=change.after,
                reason=details.reason,
                confidence=details.confidence,
                approver=details.approver,
            )
        )
    return AuditReport(
        generated_at=timestamp.astimezone(timezone.utc),
        review_fingerprint=review.fingerprint,
        entries=entries,
    )


def export_audit_json(report: AuditReport, destination: str | Path) -> None:
    """Create a new UTF-8 JSON file exclusively; never overwrite an existing file."""
    content = report.model_dump_json(indent=2) + "\n"
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
        output.write(content)
