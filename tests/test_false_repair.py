from pathlib import Path

import polars as pl
import pytest

from data_repair_copilot.csv_loader import load_csv
from data_repair_copilot.evaluation.false_repair import CellLocation, evaluate_false_repairs
from data_repair_copilot.repairs.approval import Decision, apply_decisions, create_review
from data_repair_copilot.repairs.preview import CellProposal


def test_mixed_changes() -> None:
    before = pl.DataFrame({"id": ["001", "002", "003"], "zip": ["111", "222", "00333"]})
    after = pl.DataFrame({"id": ["001", "002", "003"], "zip": ["00111", "99999", "00333"]})
    truth = pl.DataFrame({"id": ["001", "002", "003"], "zip": ["00111", "00222", "00333"]})
    result = evaluate_false_repairs(before, after, truth)
    assert (result.changed_cells, result.correct_changes, result.false_repairs) == (2, 1, 1)
    assert result.false_repair_rate == 0.5
    assert result.incorrect_locations == (CellLocation(1, "zip"),)
    # A new corruption of a previously correct cell is also a false repair.
    after = after.with_columns(pl.Series("id", ["1", "002", "003"]))
    result = evaluate_false_repairs(before, after, truth)
    assert (result.changed_cells, result.false_repairs, result.false_repair_rate) == (3, 2, 2 / 3)


def test_no_changes() -> None:
    before = pl.DataFrame({"value": ["wrong", None, ""]}, schema={"value": pl.String})
    truth = pl.DataFrame({"value": ["correct", "", ""]})
    result = evaluate_false_repairs(before, before.clone(), truth)
    assert (result.changed_cells, result.false_repairs, result.false_repair_rate) == (0, 0, None)
    after = pl.DataFrame({"value": ["wrong", "", None]}, schema={"value": pl.String})
    result = evaluate_false_repairs(before, after, truth)
    assert (result.changed_cells, result.correct_changes, result.false_repairs) == (2, 1, 1)
    assert result.incorrect_locations == (CellLocation(2, "value"),)


def test_invalid_alignment() -> None:
    source = pl.DataFrame({"a": ["1"], "b": ["2"]})
    for bad in (
        pl.DataFrame({"a": ["1"]}),
        source.reverse().clear(),
        source.select("b", "a"),
        pl.DataFrame({"a": [1], "b": ["2"]}),
    ):
        with pytest.raises(ValueError):
            evaluate_false_repairs(source, bad, source)
        with pytest.raises(ValueError):
            evaluate_false_repairs(source, source, bad)


def test_reviewed_synthetic_repairs() -> None:
    root = Path(__file__).resolve().parents[1]
    before = load_csv(root / "evals/datasets/corrupted_v1.csv").head(6)
    truth = load_csv(root / "evals/datasets/clean_v1.csv")
    snapshot = before.clone()
    review = create_review(
        before,
        [
            CellProposal(row_index=2, column="zip", proposed_value="02110"),
            CellProposal(row_index=3, column="signup_date", proposed_value="not a date"),
            CellProposal(row_index=4, column="email", proposed_value=truth["email"][4]),
        ],
    )
    outcome = apply_decisions(
        before,
        review,
        [
            Decision(change_index=0, action="approve"),
            Decision(change_index=1, action="approve"),
            Decision(change_index=2, action="reject"),
        ],
    )
    result = evaluate_false_repairs(before, outcome.dataset, truth)
    assert before.equals(snapshot)
    assert (result.changed_cells, result.correct_changes, result.false_repairs) == (2, 1, 1)
    assert result.false_repair_rate == 0.5
    assert result.incorrect_locations == (CellLocation(3, "signup_date"),)
