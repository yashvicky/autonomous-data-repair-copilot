# Acceptance gates

Use a small, task-specific acceptance ledger for non-trivial implementation.
This workflow adapts the ideas and format described by
[Unlazy](https://github.com/Leonxlnx/unlazy/blob/main/references/gates.md).
The agent charter, assigned issue, architecture, and human approval fences
remain authoritative.

## Workflow

1. Read the assigned task and its acceptance criteria, `AGENTS.md`,
   `docs/architecture.md`, and the current status. Confirm dependencies.
2. Copy `docs/templates/acceptance-gates.md` to
   `docs/gates/DR-XXX.md` on the task branch. Replace every placeholder
   before starting implementation; map all task acceptance criteria to
   specific outcomes. Add a gate if a meaningful requirement is missing.
3. For each automated gate, choose a check that exercises the outcome directly.
   Use synthetic data, including a failing or positive control where useful.
   Checks must be non-destructive and within the assigned scope. Use manual
   gates for outcomes requiring human judgment.
4. Inspect commands and scripts before running them. Run relevant tests and
   checks on the final changes. Record actual evidence: command, exit code,
   result, commit or artifact link, and limitations. Never fabricate evidence.
5. Link the ledger and summarize passed, failed, and pending gates in the PR.
   A task remains in progress if any required gate is unmet or unverified.
   If a gate cannot be met, retain it, explain the blocker and handoff.
6. The founder reviews the work and merges. Update status at the next
   meaningful milestone. The ledger does not itself grant permission to merge.

## Gate format

Use unique IDs and indented attributes. For automated gates use both `CHECK:`
and `EXPECT:`; a pass requires exit code zero and matching output. Make the
expected text an actual success signal emitted after assertions succeed. A
manual gate has no `CHECK:` or `EXPECT:`; record review evidence instead.

`CHECK:` is executable shell code. A gate title and expected text cannot prove
that a check measures the stated outcome. Review the test itself, and use
the documented platform and working directory. Don't trust inherited scripts,
or grant credentials or production access merely to run a check.

## Relationship to Unlazy

This repository adopts the acceptance-gate method; it does not install or
execute Unlazy's checker, approval store, agent skill, hook, or scheduler.
Manual evidence recorded here is a project record, not the checker's
cryptographic-format automatic evidence. If the external checker is adopted
later, review its security documentation, pin a version or commit, inspect
checks and scripts, and use its actual evidence and approval rules. Agent
instructions and gate ledgers are not a security sandbox.
