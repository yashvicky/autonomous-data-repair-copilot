import csv
import io
import json
from pathlib import Path

import pytest

from data_repair_copilot.csv_loader import load_csv
from data_repair_copilot.evaluation.fixtures import generate_fixture

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "evals/datasets/clean_v1.csv"
CORRUPTED = ROOT / "evals/datasets/corrupted_v1.csv"
TRUTH = ROOT / "evals/ground_truth/synthetic_v1.json"


def test_regenerates_exactly() -> None:
    clean = CLEAN.read_bytes()
    first = generate_fixture(clean)
    second = generate_fixture(clean)
    assert first == second == (CORRUPTED.read_bytes(), TRUTH.read_bytes())
    assert CLEAN.read_bytes() == clean


def test_ground_truth() -> None:
    clean = list(csv.DictReader(io.StringIO(CLEAN.read_text(encoding="utf-8"))))
    corrupt = list(csv.DictReader(io.StringIO(CORRUPTED.read_text(encoding="utf-8"))))
    truth = json.loads(TRUTH.read_text(encoding="utf-8"))
    expected = {(1, "status"), (2, "zip"), (3, "signup_date"), (4, "email")}
    changes = [x for x in truth["issues"] if "row_index" in x]
    assert {(x["row_index"], x["column"]) for x in changes} == expected
    actual = {
        (i, col) for i in range(len(clean)) for col in clean[i] if clean[i][col] != corrupt[i][col]
    }
    assert actual == expected
    for entry in changes:
        assert clean[entry["row_index"]][entry["column"]] == entry["original"]
        assert corrupt[entry["row_index"]][entry["column"]] == entry["corrupted"]
    assert len(clean) == 6 and len(corrupt) == 7 and corrupt[0] == corrupt[6]
    groups = {x["kind"]: x["row_indices"] for x in truth["issues"] if "row_indices" in x}
    assert groups == {"exact_duplicate_row": [0, 6], "duplicate_id": [0, 6]}
    assert clean[0]["customer_id"] == "001"


def test_loader_and_invalid_source() -> None:
    source = CLEAN.read_bytes()
    frame = load_csv(CORRUPTED)
    assert frame.height == 7 and frame["customer_id"].to_list()[0] == "001"
    with pytest.raises(ValueError, match="headers"):
        generate_fixture(b"wrong,columns\na,b\n")
    with pytest.raises(ValueError, match="value changed"):
        generate_fixture(source.replace(b"02110", b"99999"))
    assert CLEAN.read_bytes() == source
