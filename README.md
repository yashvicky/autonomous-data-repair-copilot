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

## Issue schema

`Issue` in `data_repair_copilot.models.issue` is a Pydantic model requiring
`issue_type`, `severity` (`low`, `medium`, `high`, or `critical`), a non-empty
list of evidence strings, `affected_rows`, and a recommendation string. Text
fields and evidence entries cannot be blank. Row indices are distinct
non-negative integers, zero-based and excluding the CSV header; use an empty
list for an issue not tied to specific rows. Unknown fields are rejected.

Severity, evidence, and recommendations are supplied by the caller and are
not validated as fact or permission to repair. Evidence can contain sensitive
data. Existing detector results are not yet automatically converted to issues.

## Read-only repair preview

`preview_changes(frame, proposals)` accepts `CellProposal` objects specifying a
zero-based data-row index, a column, and a proposed string or null value. It
returns a `RepairPreview` with before and after values without changing the
frame or writing a file. Only string or null columns are supported. Duplicate
target cells, missing columns, and out-of-range rows are rejected.

A preview is a point-in-time comparison, not approval, a dataset identity, or
a repaired dataset. Before a later apply workflow, verify the dataset identity,
version, and current values and obtain required approval. Output can contain
sensitive source and proposed values. This feature does not apply changes.

## In-memory approve/reject workflow

`create_review(frame, proposals)` captures a preview and a SHA-256 fingerprint
of the full string/null dataframe, schema, and proposed changes.
`apply_decisions(frame, review, decisions)` requires one explicit `approve` or
`reject` decision per change, checks the fingerprint and preview, and returns a
separate dataframe plus in-memory decision records for both outcomes. No source
file is written. Stale content, altered preview, or incomplete decisions fail.

This is a local foundation only: records disappear unless the caller saves them;
there is no persistent audit, reviewer identity or authentication. The unkeyed
fingerprint detects accidental content drift, not forgery or authorization;
it does not bind external dataset identity. Do not use this as a production
approval boundary. Enforce identity, durable logging, authorization, and
revalidation before exposing it to customer data. Reports contain values.

## Audit report export

`build_audit_report(review, records, metadata)` creates a structured report
for every approved or rejected decision. For each change, supply a
`DecisionMetadata` with `reason`, `approver`, and `confidence` (a number
from 0 to 1, or `None` if unavailable). The report includes the original and
proposed values, decision, row and column, review fingerprint, and UTC creation
time. A rejected replacement is a proposal, not an applied value.

`export_audit_json(report, path)` creates a new UTF-8 JSON file and refuses
to overwrite an existing path. These reports may contain sensitive data;
control their storage and access. The function does not authenticate reviewers,
verify the caller-provided reason/confidence, or provide tamper-evident or
durable transactional logging. An I/O failure can leave a partial new file.
File permissions depend on the operating system. This is a local export, not
a production audit trail. Never treat model confidence as measured accuracy.

## Local CSV export bundle

`export_bundle(source_path, frame, review, outcome, report, destination)`
checks that source data, preview, outcome and report agree, then creates a new
directory with `original.csv`, `cleaned.csv`, and `repair_report.json`. The
original copy preserves source bytes. An existing destination is never
overwritten. The cleaned file contains approved changes and excludes rejected
changes; no input is modified.

The current CSV loader cannot distinguish null from an empty string, so an
output containing nulls is rejected instead of silently losing information.
Source bytes are read twice to detect ordinary changes but this is not an
atomic snapshot against concurrent writers. A write failure can leave a partial
new directory; verify all artifacts before use. Local permissions and data
protection depend on the OS. These files may contain sensitive data; reports
are caller-attested, not authenticated or tamper-proof. CSV values are preserved
without spreadsheet formula escaping; opening untrusted CSV in spreadsheet
software may interpret formulas. This is not a production storage service.

## Synthetic evaluation fixture

`evals/datasets/clean_v1.csv` contains six fictional records using reserved
example.com addresses. `corrupted_v1.csv` contains four deterministic cell
edits and a duplicate row. `evals/ground_truth/synthetic_v1.json` separately
records the injected changes, duplicate groups, zero-based data-row indices,
and SHA-256 hashes. Ground truth labels injected changes only, not every
possible quality issue or implied automatic repair.

`generate_fixture(clean_bytes)` in `data_repair_copilot.evaluation.fixtures`
returns the corrupted CSV and ground-truth JSON bytes without writing files.
`uv run --locked pytest -q tests/test_eval_datasets.py` verifies regeneration
against committed fixtures and checks the labels against the data. Git
attributes preserve fixture bytes across platforms. The tiny synthetic set is
a regression fixture, not evidence of production accuracy or representative
customer data. Do not replace these fixtures with real customer data.

## Evaluating detector findings

`evaluation.metrics.evaluate_detectors` compares explicitly supplied findings
per detector. A `Finding(kind, column, row_indices)` identifies one finding;
row positions are zero-based, and duplicate groups match only when the full
group matches (row order does not matter). Both mappings must include the same
detector names. Duplicate findings are rejected.

```python
from data_repair_copilot.evaluation.metrics import Finding, evaluate_detectors

finding = Finding("missing_value", "email", (4,))
results = evaluate_detectors({"missing": [finding]}, {"missing": [finding]})
assert results["missing"].precision == 1.0
assert results["missing"].recall == 1.0
```

Precision is TP / (TP + FP); recall is TP / (TP + FN). Each is `None`
when its denominator is zero. Ground truth must be complete for the chosen
evaluation scope or the reported scores are misleading. The tiny synthetic
fixture is a workflow check, not a measure of real-world accuracy. Its category
labels describe changed cells while the category detector reports groups; that
detector is excluded until a shared evaluation convention is defined.

## Evaluating false repairs

`evaluation.false_repair.evaluate_false_repairs(before, after, reference)`
compares actual changed cells with a complete reference dataset. It reports
counts of changed cells, correct changes, false repairs and their locations.
The false-repair rate is false repairs divided by all changed cells; it is
`None` when nothing changed. Unchanged errors and rejected proposals are not
repairs and do not affect the rate.

All three frames must have the same ordered columns and row count, with string
or null values. The caller must verify matching row identities and complete,
correct reference values: matching dimensions alone cannot establish either.
The function does not apply repairs, evaluate row insertions or deletions, or
measure missed repairs. Use independently verified reference data and do not
interpret this metric as evidence that a repair strategy is safe to automate.

## Regression tests

Run `uv run --locked pytest -q -m regression` for the selected regression suite.
See [regression tests](docs/regression-tests.md) for covered behavior and the
process for adding a test and synthetic fixture for each bug fix. Continue to
run the full test suite before submitting changes.

## Local benchmark

Run `uv run --locked python scripts/benchmark_local.py` to measure the synthetic
100,000-row local ZIP detector workload. See the [benchmark report](evals/benchmarks/DR-021-local.md)
for the measured scope, results, and limitations. The AI comparison and compute
cost are not yet measured.

## Candidate generation

`matching.candidates.generate_candidates(frame, block_columns=[...])` returns
zero-based row-position pairs that agree exactly on every explicitly selected
string column. It excludes null and whitespace-only blocking values, preserves
other values as-is, and does not modify the frame. Pair positions refer only to
the input in its current order. If the total would exceed `max_pairs` (default
10,000), it raises rather than returning an incomplete list.

A shared blocking key is only a reason to consider two records: it does not
confirm they represent the same entity. Exact blocking can miss true matches
when keys differ; no recall has been established. This function makes no AI
calls, approval decisions, merges, or repairs.
