# Security readiness: proposed next work

The current application is a local synthetic-data prototype, not a service for
customer data. The loopback access guard narrows accidental exposure but is not
a replacement for authentication or production security. This plan is a
proposal; it does not authorize deployment, paid services, production data,
or major architecture changes.

## Acceptance work before customer access

1. **Identity and authorization (DR-041):** Select and approve an identity
   provider and user/tenant model. Validate identity server-side; assign every
   upload, review and export to a tenant; check ownership on every operation.
   Test unauthenticated, cross-tenant and forged-reviewer requests. Bind human
   approvals to authenticated identities, not caller-supplied names.
2. **Upload and deletion lifecycle (DR-042):** Define a bounded request and
   parsing policy, storage isolation, retention, deletion and recovery rules.
   Test malformed input, concurrent and oversized uploads, access control and
   cleanup failures. Keep original bytes immutable during analysis.
3. **Durable storage and jobs (DR-043/DR-044):** Choose an approved storage
   design. Persist state and recover failures with bounded work, timeouts and
   idempotency. The present process-memory dictionaries are not durable.
4. **Auditing (DR-025):** Record authenticated actor, decision, original and
   proposed state, timestamp, and verified provider usage/cost where available.
   Ensure missing data is explicit, protect logs, and test failure and recovery.
   A caller-selected sample flag is not evidence of an actual audit.
5. **Deployment controls (DR-045):** Independently verify application and
   dependency security checks, encrypted transport, secret management,
   production isolation, access logging, monitoring, and protected deployment.
   Threat-model the selected infrastructure and obtain the owner's deployment
   approval before exposing a service.
6. **Model and product checks:** Complete the live Grok integration and
   evaluation separately; explicitly authorize any provider spending and
   customer-data sharing. Require human approval for repairs; do not equate
   model confidence with correctness or authorization.

The exact provider, hosting, database, and retention policies are unresolved.
Each change needs its own reviewable scope, acceptance gates and tests. Keep
production gates open until the integrated system has been verified.
