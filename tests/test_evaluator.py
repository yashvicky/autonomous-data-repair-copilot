import json
from pathlib import Path

import pytest

from data_repair_copilot.csv_loader import load_csv
from data_repair_copilot.detectors.duplicates import detect_duplicates
from data_repair_copilot.detectors.formats import detect_invalid_formats
from data_repair_copilot.detectors.missing import detect_missing
from data_repair_copilot.evaluation.metrics import DetectorMetrics, Finding, evaluate_detectors


def test_known_scores() -> None:
    a = Finding("missing", "email", (1,))
    b = Finding("missing", "email", (2,))
    c = Finding("missing", "email", (3,))
    result = evaluate_detectors({"missing": [a, b], "other": []}, {"missing": [a, c], "other": []})
    assert result["missing"] == DetectorMetrics(1, 1, 1, 0.5, 0.5)
    assert result["other"] == DetectorMetrics(0, 0, 0, None, None)
    assert Finding("duplicate", None, (6, 0)) == Finding("duplicate", None, (0, 6))
    assert evaluate_detectors(
        {"duplicate": [Finding("duplicate", None, (0, 6))]},
        {"duplicate": [Finding("duplicate", None, (0, 6, 7))]},
    )["duplicate"] == DetectorMetrics(0, 1, 1, 0.0, 0.0)


def test_undefined_scores() -> None:
    f = Finding("missing", "email", (0,))
    result = evaluate_detectors(
        {"no_predictions": [], "no_truth": [f]}, {"no_predictions": [f], "no_truth": []}
    )
    assert result["no_predictions"] == DetectorMetrics(0, 0, 1, None, 0.0)
    assert result["no_truth"] == DetectorMetrics(0, 1, 0, 0.0, None)


def test_invalid_inputs() -> None:
    f = Finding("missing", "email", (0,))
    with pytest.raises(ValueError):
        evaluate_detectors({"missing": [f, f]}, {"missing": []})
    with pytest.raises(ValueError):
        evaluate_detectors({"missing": []}, {})
    with pytest.raises(ValueError):
        evaluate_detectors({"": []}, {"": []})
    for indices in [(), (-1,), (1, 1), (True,)]:
        with pytest.raises(ValueError):
            Finding("missing", "email", indices)


def test_synthetic_detectors() -> None:
    root = Path(__file__).resolve().parents[1]
    frame = load_csv(root / "evals/datasets/corrupted_v1.csv")
    labels = json.loads((root / "evals/ground_truth/synthetic_v1.json").read_text(encoding="utf-8"))
    truth = {"missing": [], "format": [], "duplicate_rows": [], "duplicate_ids": []}
    kind_to_detector = {
        "missing_value": "missing",
        "invalid_zip_format": "format",
        "invalid_iso_date": "format",
        "exact_duplicate_row": "duplicate_rows",
        "duplicate_id": "duplicate_ids",
    }
    for issue in labels["issues"]:
        if issue["kind"] in kind_to_detector:
            rows = issue.get("row_indices", [issue.get("row_index")])
            truth[kind_to_detector[issue["kind"]]].append(
                Finding(issue["kind"], issue.get("column"), tuple(rows))
            )
    missing = detect_missing(frame)
    formats = detect_invalid_formats(
        frame, column_formats={"zip": "us_zip", "signup_date": "iso_date"}
    )
    duplicates = detect_duplicates(frame, id_column="customer_id")
    predicted = {
        "missing": [
            Finding("missing_value", col.column, (row,))
            for col in missing.columns
            for row in col.missing_row_indices
        ],
        "format": [
            Finding(
                {"us_zip": "invalid_zip_format", "iso_date": "invalid_iso_date"}[col.format_kind],
                col.column,
                (issue.row_index,),
            )
            for col in formats.columns
            for issue in col.issues
        ],
        "duplicate_rows": [
            Finding("exact_duplicate_row", None, tuple(g.row_indices))
            for g in duplicates.duplicate_rows
        ],
        "duplicate_ids": [
            Finding("duplicate_id", "customer_id", tuple(g.row_indices))
            for g in duplicates.duplicate_ids
        ],
    }
    metrics = evaluate_detectors(predicted, truth)
    assert metrics == {
        name: DetectorMetrics(n, 0, 0, 1.0, 1.0)
        for name, n in {"missing": 1, "format": 2, "duplicate_rows": 1, "duplicate_ids": 1}.items()
    }
