# Current Project Status

Last updated: 2026-10-26 (America/Chicago)

## Project

Autonomous Data Repair Copilot

Detect → Investigate → Repair → Verify → Prevent

Current scope: CSV-first structured-data remediation.

## Current Milestone

Establish the project operating system and development foundation before
implementing the data-repair engine.

## Completed

- **DR-001 — GitHub repository and branch protection: COMPLETE.**
  Repository, main branch, protection, PR workflow, and labels established
  (founder-reported completion).
- **DR-002 — Agent charter: COMPLETE.**
  Agent constraints, approval fences, definition of done, and fail-closed
  behavior defined in [AGENTS.md](../AGENTS.md).
  Evidence: [merged PR #2](https://github.com/yashvicky/autonomous-data-repair-copilot/pull/2).
- **DR-003 — System architecture: COMPLETE.**
  Python, Polars/DuckDB, Rust, Jev, Grok, and human-review boundaries;
  immutable source data; evaluation-first design; V0.1 scope/non-goals;
  model-version policy; and experimental Jev image/Box/long-context lane
  documented in [architecture.md](architecture.md).
  Evidence: [merged PR #3](https://github.com/yashvicky/autonomous-data-repair-copilot/pull/3).

- **DR-004 — Current project status: COMPLETE.**
  Handoff document merged in [PR #4](https://github.com/yashvicky/autonomous-data-repair-copilot/pull/4).

- **DR-005 — Development tooling: COMPLETE.**
  Merged in [PR #5](https://github.com/yashvicky/autonomous-data-repair-copilot/pull/5).
  Linux verification is recorded in the PR; founder reports Windows checks passed.

## In Progress

Acceptance-gate workflow documentation is being prepared for human review.

## Next Task

**DR-006 — CSV loader preserving raw values.**

Start only when assigned. First define its gates against its approved
acceptance criteria; preserve identifiers, leading zeros, and source data.

## Product State

Product implementation has not started yet. There is no CSV loader,
profiler, data-quality detector, repair engine, Jev or Grok runtime
integration, FastAPI backend, frontend, or production deployment.

No unattended development routine is currently established.

## Locked Architectural Decisions

Unless explicitly changed by the human owner:

1. Python is the primary application language.
2. Polars and DuckDB handle deterministic processing.
3. Custom Rust requires a measured bottleneck or justified system requirement.
4. Jev provides bounded decisions; application code controls the workflow.
5. Grok supports investigation, explanation, and development assistance.
6. Original datasets remain immutable.
7. Propose repairs before mutation; initially all modifications require approval.
8. Risky or ambiguous repairs require human review.
9. Evaluation precedes increased autonomy.
10. V0.1 remains CSV-first.
11. Jev image, Box, and long-context features are experimental, not V0.1 dependencies.
12. Agents require human approval for merge, deploy, spend, customer-data
    access, and major architecture changes. All other charter fences also apply.

[architecture.md](architecture.md) and [AGENTS.md](../AGENTS.md) remain
authoritative; this summary does not replace them.

## Current Blockers

No product blocker reported; gate workflow awaits review and merge.

## Current Risks

- **Scope expansion:** new model features must not automatically expand V0.1.
- **Premature optimization:** do not add custom Rust without performance evidence.
- **AI overuse:** use deterministic code for reliable rule-based checks.
- **Unsafe repairs:** no autonomous modification of customer data is allowed.

## Agent Instructions

Before work, read:

1. [AGENTS.md](../AGENTS.md).
2. [architecture.md](architecture.md).
3. This file.
4. The assigned GitHub issue and its acceptance criteria.

Confirm dependencies are complete and work only on the assigned task.
Do not independently start later backlog tasks, integrations, deployments,
or experimental capabilities.

If this status conflicts with GitHub or architecture documentation, stop
and request human review. Do not silently treat an agent's completion claim
as verified evidence.

## Next Update Trigger

Update this file when a milestone completes, the active task changes,
a blocker appears or clears, a major architectural decision changes,
deployment state changes, or product scope changes.

Do not update it for trivial commits. Keep implementation details in the
architecture, issues, tests, and pull requests.
