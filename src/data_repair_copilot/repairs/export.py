"""Export a local, separate original, repaired CSV and decision report."""

import csv
import io
import json
from pathlib import Path

import polars as pl
from pydantic import BaseModel, ConfigDict

from data_repair_copilot.audit.report import AuditReport, DecisionMetadata, export_audit_json
from data_repair_copilot.csv_loader import load_csv
from data_repair_copilot.repairs.approval import (
    Decision,
    RepairOutcome,
    ReviewPacket,
    apply_decisions,
)


class ExportPaths(BaseModel):
    model_config = ConfigDict(frozen=True)

    directory: Path
    original: Path
    cleaned: Path
    report: Path


def export_bundle(
    source_path: str | Path,
    frame: pl.DataFrame,
    review: ReviewPacket,
    outcome: RepairOutcome,
    report: AuditReport,
    destination: str | Path,
) -> ExportPaths:
    """Create separate artifacts in a new directory after consistency checks.

    This is local export, not a transactional or authenticated production
    storage service. CSV cannot preserve null versus empty string; null output
    is rejected rather than silently converted.
    """
    source = Path(source_path)
    raw_before = source.read_bytes()
    loaded = load_csv(source)
    raw_after = source.read_bytes()
    if raw_before != raw_after or not loaded.equals(frame):
        raise ValueError("Source file does not match reviewed dataset or changed during reading")
    if report.review_fingerprint != review.fingerprint:
        raise ValueError("Audit report does not match review")
    records = outcome.records
    if len(report.entries) != len(records):
        raise ValueError("Audit report does not cover all decision records")
    for index, (entry, record) in enumerate(zip(report.entries, records, strict=True)):
        change = record.change
        if (
            entry.change_index != index
            or record.change_index != index
            or entry.action != record.action
            or entry.row_index != change.row_index
            or entry.column != change.column
            or entry.original != change.before
            or entry.replacement != change.after
        ):
            raise ValueError("Audit report does not match decision records")
        DecisionMetadata(reason=entry.reason, approver=entry.approver, confidence=entry.confidence)
    decisions = [Decision(change_index=r.change_index, action=r.action) for r in records]
    checked = apply_decisions(frame, review, decisions)
    if checked.records != records or not checked.dataset.equals(outcome.dataset):
        raise ValueError("Repaired dataset does not match reviewed decisions")
    if any(series.null_count() for series in checked.dataset):
        raise ValueError("Cannot export nulls without losing distinction from empty strings")
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(checked.dataset.columns)
    writer.writerows(checked.dataset.iter_rows())
    clean_bytes = buffer.getvalue().encode("utf-8")
    # Verify JSON serialization before touching the destination.
    json.loads(report.model_dump_json())
    root = Path(destination)
    root.mkdir(mode=0o700, parents=False, exist_ok=False)
    paths = ExportPaths(
        directory=root,
        original=root / "original.csv",
        cleaned=root / "cleaned.csv",
        report=root / "repair_report.json",
    )
    with paths.original.open("xb") as output:
        output.write(raw_before)
    with paths.cleaned.open("xb") as output:
        output.write(clean_bytes)
    export_audit_json(report, paths.report)
    return paths
