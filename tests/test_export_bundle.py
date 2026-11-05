from pathlib import Path

import pytest

from data_repair_copilot.audit.report import AuditReport, DecisionMetadata, build_audit_report
from data_repair_copilot.csv_loader import load_csv
from data_repair_copilot.repairs.approval import Decision, apply_decisions, create_review
from data_repair_copilot.repairs.export import export_bundle
from data_repair_copilot.repairs.preview import CellProposal


def setup_bundle(tmp_path: Path):
    source = tmp_path / "source.csv"
    raw = b'id,value\r\n001,"old, text"\r\n002,keep\r\n'
    source.write_bytes(raw)
    frame = load_csv(source)
    review = create_review(
        frame,
        [
            CellProposal(row_index=0, column="value", proposed_value="new"),
            CellProposal(row_index=1, column="value", proposed_value="ignored"),
        ],
    )
    outcome = apply_decisions(
        frame,
        review,
        [Decision(change_index=0, action="approve"), Decision(change_index=1, action="reject")],
    )
    report = build_audit_report(
        review,
        outcome.records,
        {
            0: DecisionMetadata(reason="reviewed", confidence=None, approver="A"),
            1: DecisionMetadata(reason="not needed", confidence=None, approver="A"),
        },
    )
    return source, raw, frame, review, outcome, report


def test_export_bundle(tmp_path: Path) -> None:
    source, raw, frame, review, outcome, report = setup_bundle(tmp_path)
    paths = export_bundle(source, frame, review, outcome, report, tmp_path / "bundle")
    assert source.read_bytes() == raw == paths.original.read_bytes()
    assert len({paths.original, paths.cleaned, paths.report}) == 3
    assert load_csv(paths.cleaned)["value"].to_list() == ["new", "keep"]
    assert load_csv(paths.cleaned)["id"].to_list() == ["001", "002"]
    saved = AuditReport.model_validate_json(paths.report.read_text(encoding="utf-8"))
    assert [entry.action for entry in saved.entries] == ["approve", "reject"]
    assert saved == report and frame["value"].to_list() == ["old, text", "keep"]


@pytest.mark.regression
def test_invalid_inputs(tmp_path: Path) -> None:
    source, raw, frame, review, outcome, report = setup_bundle(tmp_path)
    target = tmp_path / "not-created"
    source.write_bytes(raw.replace(b"001", b"009"))
    with pytest.raises(ValueError, match="Source file"):
        export_bundle(source, frame, review, outcome, report, target)
    source.write_bytes(raw)
    fake = report.model_copy(update={"review_fingerprint": "wrong"})
    with pytest.raises(ValueError, match="does not match review"):
        export_bundle(source, frame, review, outcome, fake, target)
    altered = report.entries[0].model_copy(update={"replacement": "not reviewed"})
    fake = report.model_copy(update={"entries": [altered, report.entries[1]]})
    with pytest.raises(ValueError, match="decision records"):
        export_bundle(source, frame, review, outcome, fake, target)
    wrong = outcome.model_copy(update={"dataset": frame})
    with pytest.raises(ValueError, match="Repaired dataset"):
        export_bundle(source, frame, review, wrong, report, target)
    assert not target.exists() and source.read_bytes() == raw


@pytest.mark.regression
def test_no_overwrite_and_null(tmp_path: Path) -> None:
    source, raw, frame, review, outcome, report = setup_bundle(tmp_path)
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "sentinel").write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError):
        export_bundle(source, frame, review, outcome, report, existing)
    assert (existing / "sentinel").read_text(encoding="utf-8") == "keep"
    null_review = create_review(
        frame, [CellProposal(row_index=0, column="value", proposed_value=None)]
    )
    null_outcome = apply_decisions(frame, null_review, [Decision(change_index=0, action="approve")])
    null_report = build_audit_report(
        null_review,
        null_outcome.records,
        {0: DecisionMetadata(reason="test", confidence=None, approver="A")},
    )
    target = tmp_path / "null-output"
    with pytest.raises(ValueError, match="Cannot export nulls"):
        export_bundle(source, frame, null_review, null_outcome, null_report, target)
    assert not target.exists() and source.read_bytes() == raw
