from datetime import datetime, timezone
from pathlib import Path

import polars as pl
import pytest
from pydantic import ValidationError

from data_repair_copilot.audit.report import (
    AuditReport,
    DecisionMetadata,
    build_audit_report,
    export_audit_json,
)
from data_repair_copilot.csv_loader import load_csv
from data_repair_copilot.repairs.approval import Decision, apply_decisions, create_review
from data_repair_copilot.repairs.preview import CellProposal


def setup_decisions():
    frame = pl.DataFrame({"id": ["001", "002"], "status": ["old", "other"]})
    review = create_review(
        frame,
        [
            CellProposal(row_index=0, column="status", proposed_value="new"),
            CellProposal(row_index=1, column="status", proposed_value=None),
        ],
    )
    outcome = apply_decisions(
        frame,
        review,
        [Decision(change_index=0, action="approve"), Decision(change_index=1, action="reject")],
    )
    metadata = {
        0: DecisionMetadata(reason="Confirmed by owner", confidence=0.8, approver="Reviewer A"),
        1: DecisionMetadata(reason="Insufficient evidence", confidence=None, approver="Reviewer A"),
    }
    return frame, review, outcome, metadata


def test_report_contents() -> None:
    frame, review, outcome, metadata = setup_decisions()
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    report = build_audit_report(review, outcome.records, metadata, generated_at=timestamp)
    assert report.generated_at == timestamp and report.review_fingerprint == review.fingerprint
    assert [
        (x.action, x.original, x.replacement, x.reason, x.confidence, x.approver)
        for x in report.entries
    ] == [
        ("approve", "old", "new", "Confirmed by owner", 0.8, "Reviewer A"),
        ("reject", "other", None, "Insufficient evidence", None, "Reviewer A"),
    ]
    assert report.entries[1].row_index == 1 and report.entries[1].column == "status"
    assert frame["status"].to_list() == ["old", "other"]
    assert AuditReport.model_validate_json(report.model_dump_json()) == report


def test_invalid_report_inputs() -> None:
    _, review, outcome, metadata = setup_decisions()
    with pytest.raises(ValueError, match="Metadata"):
        build_audit_report(review, outcome.records, {0: metadata[0]})
    with pytest.raises(ValueError, match="Exactly one"):
        build_audit_report(review, outcome.records[:1], metadata)
    with pytest.raises(ValueError, match="Exactly one"):
        build_audit_report(review, [outcome.records[0], outcome.records[0]], metadata)
    tampered = outcome.records[0].model_copy(update={"change": review.changes[1]})
    with pytest.raises(ValueError, match="does not match"):
        build_audit_report(review, [tampered, outcome.records[1]], metadata)
    with pytest.raises(ValueError, match="timezone"):
        build_audit_report(review, outcome.records, metadata, generated_at=datetime(2026, 1, 1))
    for value in [-0.1, 1.1, float("nan")]:
        with pytest.raises(ValidationError):
            DecisionMetadata(reason="ok", confidence=value, approver="A")
    with pytest.raises(ValidationError):
        DecisionMetadata(reason=" ", confidence=None, approver="A")
    with pytest.raises(ValidationError):
        DecisionMetadata(reason="ok", confidence=None, approver=" ")


def test_export_file(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    raw = b"id,status\n001,old\n002,other\n"
    source.write_bytes(raw)
    frame = load_csv(source)
    review = create_review(
        frame, [CellProposal(row_index=0, column="status", proposed_value="new")]
    )
    outcome = apply_decisions(frame, review, [Decision(change_index=0, action="approve")])
    report = build_audit_report(
        review,
        outcome.records,
        {0: DecisionMetadata(reason="Reviewed", confidence=None, approver="A")},
    )
    destination = tmp_path / "audit.json"
    export_audit_json(report, destination)
    assert AuditReport.model_validate_json(destination.read_text(encoding="utf-8")) == report
    initial = destination.read_bytes()
    with pytest.raises(FileExistsError):
        export_audit_json(report, destination)
    with pytest.raises(FileExistsError):
        export_audit_json(report, source)
    assert destination.read_bytes() == initial and source.read_bytes() == raw
    assert frame["status"].to_list() == ["old", "other"]
