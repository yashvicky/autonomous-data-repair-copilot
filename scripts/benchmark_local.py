"""Run the local benchmark from a source checkout without installing the package."""

import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
runpy.run_module("data_repair_copilot.evaluation.benchmark", run_name="__main__")
