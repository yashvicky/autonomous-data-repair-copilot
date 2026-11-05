# Decision ledger (partial)

`decisions.ledger.match_and_record` wraps the standalone Jev entity-match
adapter and appends a metadata-only entry before returning its result. Entries
contain a caller-supplied UUID, UTC time, route, requested and reported model,
outcome, confidence, whether review is required, a caller-selected audit-sample
flag, and cost status. Raw records, credentials and provider error text are not
stored in entries. The flag does not capture a sample or prove that one was
reviewed; `review_required` does not prove an escalation was delivered.

Costs are explicitly `unknown` (`cost_usd` is null). The adapter does not
obtain verified usage or billing data, including on errors where a request may
still have incurred a charge. No cost is estimated or represented as zero.

`InMemoryDecisionLedger` keeps records only during the current process. It is
not durable, authenticated, encrypted, tamper-evident, concurrency-safe, or a
production audit system. A ledger write failure prevents the wrapper returning
the decision, but a call may already have happened, and a crash or sink error
may leave no record. The wrapper cannot guarantee exactly-once recording.

Calling the existing adapter directly bypasses the wrapper. The application has
no unified model-call path, durable sink, verified billing integration, actual
review routing, or audit-sample storage. Consequently the requirement that every
model decision is recorded with cost and escalation remains unmet. This work
makes no live model calls; customer-data and spending fences still apply.
