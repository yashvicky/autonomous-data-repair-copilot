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

## CSV loader

`data_repair_copilot.csv_loader.load_csv(path)` reads a UTF-8 (optionally
BOM-prefixed), comma-delimited CSV with a required, unique, non-empty header.
All parsed cells are strings, including empty cells and null-like text. CSV
quoting is decoded; original file bytes and quoting remain unchanged on disk.
Malformed rows, invalid UTF-8, and missing files raise `CsvLoadError`.
The loader reads the full dataset into memory and does not detect encodings.

From the repository root in PowerShell:

```powershell
$env:PYTHONPATH = "src"
uv run --locked python -c 'from data_repair_copilot.csv_loader import load_csv; print(load_csv("example.csv"))'
```

## Column profiler

`profile_dataframe(frame)` returns a Pydantic dataset summary and one profile
per Polars column. Types are actual Polars dtypes, not inferred semantic types.
Null percentage is null rows / all rows × 100; unique percentage is distinct
non-null values / non-null rows × 100. A zero denominator returns `None`.
Empty strings and text such as `NULL` are values, not automatic nulls.
Samples are the first five distinct non-null values by default; set
`sample_limit` to change the cap, or zero to omit samples. Samples can
contain sensitive data, so handle profile output accordingly. The profiler
reads the full frame and computes exact distinct values in memory.

## Missing-value detector

`detect_missing(frame)` returns a Pydantic report with zero-based data-row
positions. True nulls and the exact empty string are missing by default. Pass
`missing_markers=("", "NULL")` to configure exact text matches; there is no
trimming, case folding, or implicit conversion. The input is never changed.

Opt specific columns into zero inspection via `zero_check_columns=("amount",)`.
Only numeric zero and the exact string `"0"` are considered. If a selected
column contains both a missing value and a zero, the report flags **suspected**
ambiguity for human review; it does not say which zeros are missing or repair
anything. Missing markers take precedence if `"0"` is configured as missing.
Row indices exclude the header and are zero-based, not CSV line numbers.
Reports hold all matching indices in memory and may expose sensitive row
locations; protect them accordingly.

## Exact duplicate detector

`detect_duplicates(frame, id_column="id")` reports groups of zero-based data-row
indices for exact duplicate rows and, when explicitly selected, duplicate IDs.
Groups contain every matching row, including the first. Row comparisons cover
all columns and treat nulls as equal; ID groups exclude null and empty-string
IDs. Whitespace and case are not normalized and `001` differs from `1`.
No row is deleted or changed. Grouping follows Polars equality semantics and
keeps groups and indices in input order. The detector groups data in memory;
reports include potentially sensitive row locations.

## Format-policy detector

`detect_invalid_formats(frame, column_formats={"email": "email", "zip": "us_zip"})`
checks only the specified columns and returns mismatch row positions (zero-based
data-row indices) and reason codes. It never changes data or outputs raw values.
Accepted policies are deliberately narrow:

- `email`: common ASCII mailbox syntax with a dotted domain, up to 254 characters;
  this is not a complete email standard or deliverability check.
- `iso_date`: `YYYY-MM-DD`, requiring a real calendar date.
- `us_phone`: ten digits, `DDD-DDD-DDDD`, or `(DDD) DDD-DDDD`.
- `us_zip`: five ASCII digits or ZIP+4 with a hyphen.

Other legitimate formats may be flagged. True nulls and exact empty strings are
skipped; pass exact `missing_markers` to change the string markers. Non-string
values are reported separately; whitespace is not trimmed. A mismatch is not
proof an address, number, or postal code is invalid. No repair is performed.
Reports retain matching row positions in memory and may be sensitive.

## Category inconsistency detector

`detect_category_variants(frame, column="status")` groups distinct original
strings that share a comparison key after Unicode case-folding and whitespace
collapsing. Each variant includes its exact original value and zero-based data
row indices. Nulls and whitespace-only strings are skipped. Repeated identical
strings alone do not produce an inconsistency group.

Provide explicit aliases, for example `aliases={"US": "United States"}`, to
group additional variants. Conflicting normalized aliases and alias chains are
rejected. Alias mapping is a comparison rule, not a verified equivalence; review
the evidence. No data is changed or repaired. Raw values and row locations in
the report can be sensitive; grouping all values uses memory.
