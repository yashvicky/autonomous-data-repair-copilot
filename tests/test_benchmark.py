import pytest

from data_repair_copilot.evaluation.benchmark import benchmark_zip_detection


def test_small_synthetic_benchmark() -> None:
    result = benchmark_zip_detection(rows=21, repetitions=2)
    assert result["rows"] == 21
    assert result["expected_invalid"] == result["observed_invalid"] == 3
    assert result["warmup_runs"] == 1
    assert result["measured_runs"] == len(result["elapsed_seconds"]) == 2
    assert all(elapsed >= 0 for elapsed in result["elapsed_seconds"])
    assert (
        min(result["elapsed_seconds"]) <= result["median_seconds"] <= max(result["elapsed_seconds"])
    )
    assert result["local_compute_cost"] is None
    assert result["ai_comparison"] is None
    assert result["environment"]["python"]
    assert result["environment"]["polars"]


def test_invalid_arguments() -> None:
    for rows, repetitions in [(0, 1), (1, 0), (-1, 1), (True, 1), (1, 1.5)]:
        with pytest.raises(ValueError):
            benchmark_zip_detection(rows, repetitions)


def test_checkout_command() -> None:
    import json
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts/benchmark_local.py"),
            "--rows",
            "11",
            "--repetitions",
            "1",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=root,
    )
    report = json.loads(result.stdout)
    assert (report["rows"], report["observed_invalid"], report["measured_runs"]) == (11, 2, 1)
