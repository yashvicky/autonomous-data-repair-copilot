# Autonomous Data Repair Copilot

Detect → Investigate → Repair → Verify → Prevent

An evaluation-first data quality and remediation system for structured data.

## Current scope

V0.1 focuses on CSV datasets.

The system will:
- profile structured data
- detect deterministic data quality problems
- identify suspicious patterns
- propose repairs without modifying source data
- support human approval
- verify repairs
- generate prevention rules

## Status

Early development.

## Development setup

Install uv first. On Windows PowerShell:

```powershell
winget install --id=astral-sh.uv -e
```

Reopen your terminal and verify `uv --version`. From the repository root:

```sh
uv sync --locked
```

This creates `.venv` using Python 3.12 and the committed `uv.lock`, including
pytest and Ruff. uv can download Python 3.12 if it is missing. Python patch
versions and platform wheels may differ across machines; dependencies are locked.
Do not commit `.venv` or credentials. No shell activation is needed.

Verify:

```sh
uv run --locked python --version
uv run --locked pytest
uv run --locked ruff check .
```

Use `uv add` / `uv add --dev` for intentional dependency changes, and commit
both `pyproject.toml` and `uv.lock`. Do not hand-edit the lockfile.
