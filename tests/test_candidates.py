import polars as pl
import pytest

from data_repair_copilot.matching.candidates import CandidatePair, generate_candidates


def test_exact_blocking() -> None:
    frame = pl.DataFrame(
        {
            "zip": ["02110", "10001", "02110", "02110", "10001"],
            "name": ["Ada", "Bob", "ADA", "Other", "Bob"],
        }
    )
    before = frame.clone()
    expected = [CandidatePair(0, 2), CandidatePair(0, 3), CandidatePair(1, 4), CandidatePair(2, 3)]
    assert generate_candidates(frame, block_columns=["zip"]) == expected
    assert generate_candidates(frame, block_columns=["zip"]) == expected
    assert frame.equals(before)
    # Shared key only identifies candidates, including potentially different entities.
    assert frame["name"][0] != frame["name"][3]


def test_missing_and_multiple_columns() -> None:
    frame = pl.DataFrame(
        {
            "a": ["x", "x", "x", "", "", None, None, "  ", "X"],
            "b": ["z", "z", "Z", "z", "z", "z", "z", "z", "z"],
        }
    )
    assert generate_candidates(frame, block_columns=["a", "b"]) == [CandidatePair(0, 1)]
    assert generate_candidates(frame, block_columns=["a"]) == [
        CandidatePair(0, 1),
        CandidatePair(0, 2),
        CandidatePair(1, 2),
    ]
    assert generate_candidates(frame.head(0), block_columns=["a"]) == []


def test_pair_limit() -> None:
    frame = pl.DataFrame({"key": ["x", "x", "x", "y", "y"]})
    with pytest.raises(ValueError, match="count 4 exceeds limit 3"):
        generate_candidates(frame, block_columns=["key"], max_pairs=3)
    assert len(generate_candidates(frame, block_columns=["key"], max_pairs=4)) == 4
    assert (
        generate_candidates(pl.DataFrame({"key": ["x"]}), block_columns=["key"], max_pairs=0) == []
    )


def test_invalid_inputs() -> None:
    frame = pl.DataFrame({"key": ["x"], "number": [1]})
    for columns in ([], "key", [""], ["missing"], ["key", "key"], ["number"]):
        with pytest.raises(ValueError):
            generate_candidates(frame, block_columns=columns)
    for limit in (-1, True, 1.5):
        with pytest.raises(ValueError):
            generate_candidates(frame, block_columns=["key"], max_pairs=limit)
