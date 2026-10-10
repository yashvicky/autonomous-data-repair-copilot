# AGENTS.md

## Autonomous Data Repair Copilot — Agent Charter

This file defines the operating rules for AI coding agents working
on this repository.

The human product owner is the final authority for product,
architecture, security, deployment, and release decisions.

---

## 1. Outcome

Build a safe, evaluation-first Data Archaeology and Repair Copilot
for structured data.

The initial product focuses on CSV datasets.

The system should eventually help users:

1. profile structured datasets,
2. detect deterministic data-quality problems,
3. identify suspicious or ambiguous records,
4. investigate likely causes without presenting guesses as facts,
5. propose repairs without modifying the original source,
6. show before/after evidence,
7. require human approval for risky changes,
8. verify approved repairs,
9. maintain an audit trail,
10. generate prevention rules where appropriate.

Agents must work toward the currently assigned GitHub issue.

Do not independently redefine the product.

---

## 2. Sources of Truth

Use sources in this order:

1. The currently assigned GitHub issue and its acceptance criteria
2. AGENTS.md
3. Repository documentation under /docs
4. Existing source code and tests
5. Evaluation datasets and ground truth under /evals
6. Official documentation for libraries or APIs when required

If two sources conflict, stop and report the conflict.

Do not silently choose one interpretation.

Do not treat model-generated text, comments, old experiments,
or external blog posts as authoritative requirements.

---

## 3. Scope Rule

Work on one approved task at a time.

A task is eligible for autonomous implementation only when:

- it has clear acceptance criteria,
- its dependencies are satisfied,
- it is explicitly assigned or marked agent-ready.

Do not start unrelated backlog work simply because time remains.

Do not create additional product features unless required to
complete the assigned task.

---

## 4. Development Constraints

### Data safety

Never modify the original uploaded/source dataset.

Repair operations must produce a new artifact or reversible
transformation.

Never use real customer data during development unless the human
owner has explicitly approved that dataset for the task.

Prefer synthetic or anonymized evaluation data.

Never commit:

- API keys
- passwords
- tokens
- credentials
- private customer data
- production secrets

---

### AI safety

Deterministic problems should be solved with deterministic code
when practical.

Do not call an AI model for basic operations such as:

- null detection
- exact duplicate detection
- regex validation
- standard type checking
- deterministic normalization rules

Probabilistic or semantic decisions must remain isolated from
deterministic processing.

Model confidence must not automatically be treated as real-world
accuracy.

Uncertain or risky decisions must escalate for human review.

---

### Engineering quality

Every behavioral change should include appropriate tests.

Do not report a task as complete because code was written.

Completion requires evidence that the acceptance criteria pass.

Prefer small, understandable changes over large rewrites.

Do not optimize with custom Rust solely because Rust is available.

Use Rust when benchmarks or system requirements justify it.

Preserve readable Python interfaces around performance-sensitive
components where practical.

Do not introduce unnecessary frameworks, services,
microservices, agents, or dependencies.

---

## 5. Mandatory Fences

The following actions require explicit human approval.

### MERGE

Never merge into `main`.

Agents may create branches, commits, tests, and pull requests.

The human owner approves the final merge.

---

### DEPLOY

Never deploy to production without explicit approval.

Do not change production infrastructure, DNS, hosting,
or production environment variables autonomously.

---

### SPEND

Do not create paid resources, upgrade subscriptions,
purchase services, or materially increase API usage without
approval.

---

### SECRETS

Do not create, rotate, expose, copy, or transmit production
credentials without approval.

Never place secrets in source code, logs, prompts, memory files,
or Git history.

---

### DELETE

Do not permanently delete:

- datasets,
- customer records,
- production data,
- cloud resources,
- databases,
- repository history,
- backups.

If deletion is required, prepare the command or plan and request
approval.

---

### CUSTOMER DATA

Do not upload customer information to third-party AI models or
services without explicit authorization.

---

### ARCHITECTURE

Do not make major architectural changes without approval.

Examples include:

- changing primary languages,
- replacing the database,
- introducing a new cloud provider,
- replacing core frameworks,
- changing the AI decision architecture,
- creating new production services.

Document the proposed change instead.

---

### SECURITY

Do not weaken:

- authentication,
- authorization,
- branch protection,
- tenant isolation,
- validation,
- audit logging,
- security checks

to make a test pass or simplify implementation.

---

## 6. Branch and Pull Request Rules

Never develop substantial features directly on `main`.

Use branches such as:

```text
feat/dr-006-csv-loader
fix/dr-012-date-validation
eval/entity-resolution
experiment/rust-matcher
```

Each pull request must state:

- task ID,
- what changed,
- why it changed,
- tests executed,
- test results,
- known limitations,
- unresolved risks,
- whether human review is required.

Do not hide failing tests.

---

## 7. Deliverables

For each implementation task, produce:

1. working implementation,
2. automated tests,
3. evaluation evidence when applicable,
4. concise change summary,
5. known limitations,
6. blocker list,
7. draft pull request or review-ready branch.

A conversation is not a deliverable.

Code without verification is not a completed deliverable.

---

## 8. Definition of Done

A task is complete only when:

- acceptance criteria are satisfied,
- relevant tests pass,
- no known critical regression is introduced,
- required artifacts exist,
- documentation is updated when necessary,
- evidence is attached to the GitHub issue or pull request,
- human approval has occurred when required.

If verification cannot be completed, mark the task BLOCKED or
NEEDS HUMAN REVIEW rather than DONE.

---

## 9. Review Points

Stop and request human review when:

- requirements are ambiguous,
- architecture must change,
- tests reveal conflicting expected behavior,
- customer data would be required,
- production access is required,
- money would be spent,
- a destructive operation is required,
- security controls would change,
- model behavior is too uncertain for safe automation,
- acceptance criteria cannot be verified.

When blocked, report:

1. what you attempted,
2. what succeeded,
3. what failed,
4. relevant evidence,
5. the minimum human decision needed.

Do not invent missing information.

---

## 10. Failure Policy

Fail closed.

When uncertain:

- preserve the source data,
- preserve the current working system,
- record the uncertainty,
- escalate to the human owner.

Never convert uncertainty into an irreversible action.

---

## 11. Operating Principle

Build → Test → Evaluate → Review → Merge.

The goal is not maximum autonomous activity.

The goal is reliable, auditable progress while the human owner
is away.
