# Gates: DR-006 Windows newline regression

Scope: Fix the CSV test fixture for Windows and verify embedded newline preservation.
Issue: founder-reported Windows test failure after DR-006 merge.
Base commit: 09c1093099018789cb38a8cbda87130bfef50120

- [x] G1: Explicit LF and CRLF fixture bytes preserve their embedded newlines.
  CHECK: uv run --locked pytest -q tests/test_csv_loader.py::test_preserves_raw_field_values
  EXPECT: 2 passed
  EVIDENCE: Linux Python 3.12.14; exit 0; 2 passed. Windows run pending.

- [x] G2: Project tests and lint pass.
  CHECK: uv run --locked pytest -q && uv run --locked ruff check .
  EXPECT: All checks passed!
  EVIDENCE: Linux Python 3.12.14; exit 0; 9 passed; Ruff passed. Windows run pending.

- [ ] G3: Founder reviews the change and Windows test output.
  EVIDENCE: pending founder review and Windows run.
