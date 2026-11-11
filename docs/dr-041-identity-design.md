# DR-041: proposed identity and tenant-isolation design

**Status: PROPOSED — owner decision required.** This document is not an
implementation, deployment authorization, provider purchase, or claim that the
current prototype can handle customer data.

## Problem and recommendation

The local API uses process-memory dictionaries keyed by random identifiers. It
does not authenticate callers, associate resources with tenants, or verify the
identity behind an approval. The loopback guard is not a user or tenant boundary.

Recommend a provider-neutral OpenID Connect (OIDC) login with a managed identity
provider, server-side membership checks, and a durable tenant-scoped data store.
One organization is a tenant; a user may belong to multiple tenants. Initial
roles are owner, reviewer, and viewer. These are proposed, not locked decisions.
An owner manages membership; a reviewer may approve or reject repairs; a viewer
can inspect authorized data but cannot approve. Ownership and membership come
from server-controlled state, not request headers, form fields or a model.

## Request and approval boundary

1. The browser starts an authorization-code login with PKCE through the chosen
   identity provider. The backend validates issuer, audience, signature, expiry,
   state, nonce and other applicable protocol requirements before creating a
   secure server-side session. Use established maintained libraries, not custom
   cryptographic or password-handling code. Enforce HTTPS in production and
   secure, HttpOnly cookies with an appropriate SameSite and CSRF strategy.
2. For each protected request, derive the user from the validated session and
   load current tenant membership server-side. Deny by default if the session,
   membership, role, or authorization check is missing, stale or unavailable.
   Tenant selection is accepted only after membership is verified.
3. All upload, profile, analysis, review, decision, audit and export reads and
   writes are scoped at the storage boundary to that verified tenant. Random
   identifiers do not grant access. Authorize each action and role; a missing
   or unauthorized resource should not reveal another tenant's existence.
4. The backend records approval against the authenticated reviewer identity and
   the exact reviewed snapshot. A caller-supplied name is display metadata,
   never identity. Changes remain proposals until an authorized reviewer decides.
5. Use tenant-owned durable records and transactional audit events. The exact
   database and row-level security policy require a separate approved storage
   design; do not claim existing process-memory state is durable or isolated.

## Required tests before closing DR-041

- Login, logout, session expiry and invalid or revoked credentials; no protected
  route succeeds without valid authentication.
- Two tenants and multiple roles: cross-tenant read/write/preview/decision/audit/
  export attempts fail, including guessed IDs and forged tenant headers.
- Viewer approval is rejected; reviewer impersonation using request metadata
  fails; review snapshot changes invalidate approval.
- Removed membership or revoked sessions cannot keep accessing data; verify
  concurrent requests, caching, job boundaries and restart behavior.
- Storage enforces tenant scope in every query, object path and cache key;
  failure of identity, membership or storage checks fails closed.
- No credentials or raw customer records appear in application logs or tests;
  use synthetic fixtures. Run an independent security review before customer use.

## Decisions needed

The owner must approve or change the following before implementation:

- Managed OIDC provider and account; do not create or purchase one yet.
- Tenant model (one organization per tenant) and initial role permissions.
- Durable storage and deployment architecture, including tenant enforcement and
  session handling. This overlaps DR-043 and DR-045 and needs its own review.

Sources: [OWASP authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html),
[OWASP multi-tenant security](https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html),
and [OWASP authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html).
