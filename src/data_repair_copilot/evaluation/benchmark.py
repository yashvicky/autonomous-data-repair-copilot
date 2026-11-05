"""Measure local ZIP format detection on synthetic in-memory data."""

import argparse
import json
import platform
import statistics
import time
from importlib.metadata import version

import polars as pl

from data_repair_copilot.detectors.formats import detect_invalid_formats


def benchmark_zip_detection(rows: int = 100_000, repetitions: int = 3) -> dict:
    """Time the detector after one warm-up, excluding frame creation and I/O."""
    if type(rows) is not int or rows <= 0 or type(repetitions) is not int or repetitions <= 0:
        raise ValueError("rows and repetitions must be positive integers")
    frame = pl.DataFrame({"zip": ["1234" if i % 10 == 0 else "02110" for i in range(rows)]})
    expected = (rows + 9) // 10

    def run() -> int:
        report = detect_invalid_formats(frame, column_formats={"zip": "us_zip"})
        count = len(report.columns[0].issues)
        if report.row_count != rows or count != expected:
            raise RuntimeError("detector output differs from the synthetic workload expectation")
        return count

    run()
    timings = []
    for _ in range(repetitions):
        start = time.perf_counter()
        count = run()
        timings.append(time.perf_counter() - start)
    return {
        "workload": "synthetic US ZIP format validation, in-memory, single column",
        "rows": rows,
        "expected_invalid": expected,
        "observed_invalid": count,
        "warmup_runs": 1,
        "measured_runs": repetitions,
        "elapsed_seconds": timings,
        "median_seconds": statistics.median(timings),
        "timed_scope": (
            "format detector and result materialization; excludes data generation and I/O"
        ),
        "local_compute_cost": None,
        "ai_comparison": None,
        "environment": {
            "python": platform.python_version(),
            "polars": version("polars"),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor() or None,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    if args.rows <= 0 or args.repetitions <= 0:
        parser.error("rows and repetitions must be positive")
    print(json.dumps(benchmark_zip_detection(args.rows, args.repetitions), indent=2))


if __name__ == "__main__":
    main()
