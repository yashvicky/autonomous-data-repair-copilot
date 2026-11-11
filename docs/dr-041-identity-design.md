# DR-041: proposed V0.1 account and data-isolation design

**Status: PROPOSED — owner decision required.** This is not an implementation,
deployment authorization, provider purchase, or claim that the prototype can
handle customer data. The original gameplan requires human review and defers
enterprise SSO; the identity provider and details below are new recommendations,
not previously approved architectural decisions.

## V0.1 scope

A person has an individual account, can access only their own datasets and
related resources, and explicitly approves their own repairs. User-owned data
must remain separated from every other user. Organization accounts, shared
workspaces, owner/reviewer/viewer roles, and enterprise SSO are deferred.
Adding multiple users and sharing later requires a separately approved design.

The current API has no login or ownership enforcement. Its random identifiers,
loopback guard and caller-supplied reviewer names do not establish identity.
The existing in-memory state is neither durable nor tenant-isolated.

## Provider and storage recommendation

Recommend evaluating **Supabase Auth and managed PostgreSQL** as one possible
low-operations starting point. Supabase documents individual authentication and
PostgreSQL row-level security (RLS). The choice is not yet approved: no project,
account, paid plan, secret, external service, or production resource has been
created. Availability, actual costs, data region, privacy terms, and limits must
be verified before selecting or purchasing it. A different provider can satisfy
the same acceptance criteria.

For V0.1, the authenticated user is the owner of each resource. Store the
server-verified user identifier alongside uploads, analysis results, review
snapshots, decisions, audits and exports. Authorize every read and write in the
backend and enforce ownership at the storage boundary, with RLS as defense in
depth if PostgreSQL is selected. A caller-supplied ID, header, reviewer name or
model result never grants access. Prevent bypass via privileged service keys or
administrative database roles; test the real request path, not only policy SQL.

Use maintained authentication libraries and supported session flows. Validate
session identity server-side. Apply HTTPS, secure cookies and CSRF protections
appropriate to the final client/session design. Enforce expiry, logout and
revocation according to the chosen provider's documented behavior. Record an
approval against the authenticated user and the exact reviewed snapshot.

A production-ready upload lifecycle, protected durable audit and infrastructure
security remain separate required work under DR-042, DR-025, DR-043 and DR-045.
This proposal does not allow removing the local-only guard or using customer
data before those gates and deployment approvals are met.

## Required tests before closing DR-041

- Sign-in, logout, invalid and expired credentials; unauthenticated requests fail.
- At least two test users: each user can access their own uploads and review
  artifacts but cannot read, write, approve, audit or export the other's data,
  even with guessed identifiers or forged user headers.
- Approver identity comes from the authenticated session, not request metadata;
  changed or stale review snapshots cannot be approved.
- Identity and storage errors fail closed; ownership persists across restarts and
  is enforced for background jobs, object storage and caches when implemented.
- Tests use synthetic data; secrets and raw customer data are absent from logs.
  An independent security review is completed before customer use.

## Owner decisions before implementation

Confirm the individual-account V0.1 scope and select the provider and storage
architecture. Supabase is a recommendation to evaluate, not a commitment. No
provider account or paid resources should be created without authorization.

References: [Supabase Auth](https://supabase.com/docs/guides/auth),
[Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security),
[OWASP authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html),
and [OWASP multi-tenant security](https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html).
