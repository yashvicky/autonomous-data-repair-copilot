# Architecture

## 1. Purpose

The Autonomous Data Repair Copilot is an evaluation-first system for understanding, repairing, verifying, and preventing structured-data quality problems.

The initial product wedge is intentionally narrow:

- CSV input first
- preserve the original source
- detect deterministic problems locally
- isolate ambiguous semantic decisions
- propose repairs before applying them
- require human approval for risky changes
- verify every applied repair
- produce an audit trail
- generate prevention rules where appropriate

The product should evolve from a CSV repair copilot into a broader data reliability system only after the core workflow proves useful to real users.

---

## 2. V0.1 Product Boundary

### In scope

V0.1 accepts structured CSV data and supports:

1. profiling,
2. missing-value analysis,
3. exact duplicate detection,
4. type/format inconsistencies,
5. categorical inconsistencies,
6. repair proposals,
7. before/after previews,
8. human approval,
9. repaired-copy export,
10. audit history,
11. prevention-rule generation.

### Out of scope for V0.1

Do not make these launch dependencies:

- Snowflake/BigQuery/Databricks connectors
- production database writes
- autonomous production remediation
- Kubernetes
- Kafka
- microservices
- OpenLineage integration
- enterprise SSO
- custom Rust rewrites without benchmarks
- image/document cleaning
- OCR pipelines
- fully autonomous semantic merges
- agent swarms

These may be added later when user evidence justifies them.

---

## 3. System Boundaries

### Python

Python is the primary orchestration and application language.

Responsibilities:

- product/business logic
- data-quality detectors
- repair proposal orchestration
- evaluation harnesses
- Jev/Grok provider adapters
- FastAPI backend
- audit and verification workflows
- user-facing workflow coordination

Python remains the default implementation language unless a benchmark or hard platform requirement justifies another language.

### Rust

Rust is an optimization layer, not the default implementation language.

Use Rust only when:

- profiling shows a real CPU or memory bottleneck,
- a hot path has a clear stable contract,
- the performance improvement is measurable,
- the additional maintenance cost is justified.

Likely future candidates:

- large-scale entity-resolution candidate generation
- high-throughput parsing
- CPU-intensive normalization/matching
- concurrency-sensitive ingestion helpers

Preferred integration path:

Python -> PyO3/Maturin -> focused Rust crate

Polars already provides a Rust-powered execution engine, so custom Rust should not be added merely for language preference.

### Polars and DuckDB

Use Polars and DuckDB for deterministic local processing.

Examples:

- null detection
- exact duplicate detection
- basic schema checks
- type and range checks
- deterministic category normalization
- local analytical SQL
- candidate narrowing before model calls

A model should not be used for operations that deterministic code can perform reliably.

---

## 4. Decision Architecture

The system separates deterministic processing from probabilistic judgment.

```text
Input
  |
  v
Profiler
  |
  v
Deterministic detectors
  |
  +-------------------+
  |                   |
obvious rule       ambiguous case
  |                   |
  v                   v
Python/Polars      Decision Router
                      |
                      +--> Jev
                      |
                      +--> Grok escalation
                      |
                      +--> Human review
  |                   |
  +---------+---------+
            |
            v
      Repair proposal
            |
            v
      Human approval
            |
            v
          Repair
            |
            v
        Verification
            |
            v
        Audit trail
            |
            v
     Prevention rule
```

---

## 5. Jev Boundary

Jev is a bounded decision provider, not the system controller.

Use Jev for narrow semantic questions such as:

- same entity / different entity / review
- category classification
- repair-risk classification
- bounded scoring
- yes/no semantic judgments

Application code owns:

- thresholds
- routing
- permissions
- repair execution
- retries
- fallbacks
- audit policy
- escalation
- human approval

Jev output must never directly mutate customer data.

### Model-version policy

Do not rely on a moving model alias for evaluation-critical behavior.

- Record the exact Jev model version used for every evaluated decision.
- Pin version IDs for benchmarks and threshold tuning.
- Treat alias changes as model changes that require re-evaluation.
- Promote a newer model only after it passes the project's evaluation suite.

As of the Jev 1.14 release, `jev-preview` points to `jev-1.14.0`. The stable alias may move separately. The architecture must therefore keep model selection configurable and versioned.

Official model docs:
https://docs.typesafe.ai/models

---

## 6. Jev 1.14 Experimental Capability Lane

Jev 1.14 adds capabilities that are useful for future versions of this product but are NOT V0.1 dependencies.

### Images

Jev can accept PNG/JPEG images in state, instructions, or criteria.

Potential future data-repair uses:

- screenshot-based data issue triage
- scanned forms
- spreadsheet screenshots
- visually comparing reference records
- validating exported reports
- locating suspicious fields in image-based source material

Image support is currently behind a Danger Zone header and TypeSafe documents it as experimental rather than production-ready.

Official docs:
https://docs.typesafe.ai/images

### Box

Jev 1.14 adds a Box question that returns a bounding box around a target in an image.

Potential future uses:

- locate a field in a scanned form
- identify table regions
- crop suspected bad-data regions before further processing
- assist visual quality checks

Box must not be used as proof that a target exists; pair it with a presence/decision check before acting.

Official docs:
https://docs.typesafe.ai/primitives/box

### Long context

Jev can opt into longer per-request/per-question context limits through a Danger Zone header.

Potential future uses:

- large data dictionaries
- long schema documentation
- incident logs
- transformation histories
- large groups of candidate records

Do not enable long context by default.

The provider documentation states that long context is slower and less accurate than staying within the standard limits, so the default architecture should prefer:

1. deterministic filtering,
2. summarization/selection,
3. smaller atomic questions,
4. long context only when necessary.

---

## 7. Grok Boundary

Grok is a reasoning, investigation, and explanation layer.

Good uses:

- explain why an issue is suspicious
- propose investigation steps
- summarize evidence
- generate draft SQL/dbt prevention logic
- analyze logs and metadata
- help developers implement and review code

Do not use Grok for:

- basic null checks
- exact duplicate checks
- regex validation
- deterministic transformations
- silently approving risky repairs
- direct production writes

Product-runtime Grok usage must be separate from development-agent Grok usage.

---

## 8. Data Safety

The original uploaded dataset is immutable.

Every repair must produce either:

- a new dataset,
- a reversible transformation,
- or an explicit approved transaction in a later production-database phase.

For every proposed/applied repair, preserve:

- dataset identifier
- issue identifier
- original value/state
- proposed replacement
- detection rule
- decision provider/model version if applicable
- decision output
- confidence/score if applicable
- human approval state
- verification result
- timestamp

Never infer a cause as fact when only a suspicious pattern has been observed.

Represent separately:

- observed evidence,
- suspected cause,
- proposed action.

---

## 9. Repair Risk Policy

Initial automation maturity:

### Stage 1 — Human oversight

All modifications require approval.

### Stage 2 — Deterministic automation

Only deterministic, reversible, well-tested operations may run automatically.

Semantic/ambiguous repairs remain in the review queue.

### Stage 3 — Trusted policy automation

Autonomous semantic remediation requires:

- repeated validated history,
- known organizational policy,
- strong evaluation evidence,
- low measured false-repair rate,
- auditability,
- rollback/recovery.

This stage is not part of V0.1.

---

## 10. Evaluation Architecture

No model or repair strategy is trusted because of vendor claims.

Maintain ground-truth evaluation datasets that measure:

- detection precision
- detection recall
- entity-resolution accuracy
- false-repair rate
- review/escalation rate
- latency
- memory usage
- model cost
- cost per processed dataset / 100K rows

For Jev upgrades, compare the current pinned version and proposed version on the same evaluation set before promotion.

Experimental Jev image, Box, and long-context capabilities require separate evaluation sets before production use.

---

## 11. Development-Agent Boundary

Autonomous coding agents are development infrastructure, not product-runtime agents.

They may:

- work on approved issues,
- create feature branches,
- write code/tests/docs,
- run approved local checks,
- prepare draft pull requests.

They may not:

- merge to main,
- deploy production,
- spend money,
- alter secrets,
- access real customer data without approval,
- change major architecture autonomously.

See `/AGENTS.md` for the authoritative agent charter.

---

## 12. Initial Repository Direction

Target structure:

```text
autonomous-data-repair-copilot/
|
|-- AGENTS.md
|-- README.md
|-- docs/
|   |-- architecture.md
|   |-- current_status.md
|
|-- src/
|   |-- data_repair_copilot/
|       |-- profiler/
|       |-- detectors/
|       |-- repairs/
|       |-- matching/
|       |-- decisions/
|       |-- validators/
|       |-- models/
|
|-- crates/
|   |-- # optional future Rust components
|
|-- tests/
|   |-- unit/
|   |-- integration/
|
|-- evals/
|   |-- datasets/
|   |-- ground_truth/
|   |-- benchmarks/
```

Do not create every directory before a task needs it.

---

## 13. Core Architectural Principles

1. Preserve originals.
2. Deterministic before probabilistic.
3. Evidence before explanation.
4. Proposal before mutation.
5. Human review for uncertainty.
6. Verification after repair.
7. Prevention after verification.
8. Evaluation before autonomy.
9. Pin model behavior before trusting thresholds.
10. Add Rust only for measured bottlenecks.
11. Experimental model features stay isolated behind adapters and flags.
12. Real user pain determines expansion.

---

## 14. V0.1 Success Condition

V0.1 is successful when a new user can:

1. upload a CSV,
2. understand detected issues,
3. inspect supporting evidence,
4. review repair proposals,
5. approve selected repairs,
6. receive a repaired copy,
7. see what changed,
8. receive prevention guidance,

without the system modifying the original data and without requiring the founder to manually operate the workflow.
