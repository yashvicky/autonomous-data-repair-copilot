# Regression tests

Run the selected regression suite from the repository root:

```sh
uv sync --locked
uv run --locked pytest -q -m regression
```

Run the full test suite and Ruff before submitting a change:

```sh
uv run --locked pytest -q
uv run --locked ruff check .
```

## What this suite protects

- **Known bug: Windows newline handling.** The byte-defined LF and CRLF
  fixtures in `tests/test_csv_loader.py::test_preserves_raw_field_values`
  protect the failure fixed in [PR #8](https://github.com/yashvicky/autonomous-data-repair-copilot/pull/8).
  Embedded newlines and leading-zero identifiers must be preserved.
- **Safety checks, not claimed historical bugs:** source immutability,
  approved versus rejected changes, stale review rejection, export validation
  and overwrite prevention, and false-repair counting.

The marker selects existing tests; all remain part of the full suite. A pass
is not proof that every possible bug is covered or that Windows has been tested.

## When fixing a bug

1. Record the reported behavior, expected behavior, reproduction steps, and an
   issue or PR link where available. Do not include private or customer data.
2. Add the smallest synthetic fixture and a test that reproduces the failure.
   For byte-sensitive bugs, write explicit bytes to avoid platform translation.
3. Confirm the test fails for the original defect when practical; record the
   failing result or explain why it could not be reproduced safely.
4. Fix the defect, add `@pytest.mark.regression`, and run the selected suite and
   full tests. Document the fixture, test, link, and platform in this file.
5. Record actual results in the task's acceptance ledger and PR. If the defect
   cannot be reproduced, do not claim it is fixed; document the blocker.

This is a project workflow; it does not automatically enforce that every
future bug has a regression test.
