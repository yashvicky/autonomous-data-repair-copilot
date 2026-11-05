# Decision provider interface

`DecisionProvider` defines one method: `decide(request) -> DecisionResult`.
A request contains an ID, a question and at least two unique allowed choices.
A result either selects one allowed choice or requests human review. Provider
confidence is optional and uncalibrated; it does not grant repair approval.

Use `request_decision(provider, request)` to validate provider output against
the request. Provider exceptions and malformed or out-of-scope responses
return `needs_review`, with a reason distinguishing a provider error from an
invalid response. Exception details are not returned. The human-review stub
always returns `needs_review` and does not invoke a model.

A future Jev or other provider can implement the same protocol. A separate
entity-match adapter is proposed in `decisions.jev_entity`; it is not wired to
this protocol or the product workflow and has not been live-verified. It needs
explicit credentials and spending authorization for a real call. Provider-reported
model metadata is not verified by the generic interface. A real integration must record the exact
model version for evaluations, apply its own timeout and provenance controls,
and comply with the project's data and spending fences.

This interface does not review, authorize, or apply repairs. The existing human
approval workflow remains separate. Do not send customer data to a provider
without authorization or use model confidence as an automatic approval.

## Standalone Jev entity-match adapter

`match_entities(left, right, model=..., transport=...)` builds a documented
TypeSafe Choice request for `same_entity`, `different_entity`, or `needs_review`.
Use an exact model version; aliases are rejected. The separate
`typesafe_http_transport(api_key)` uses the fixed TypeSafe HTTPS endpoint,
one request, a timeout, no redirects, and no retries. Construction does not
call the service; calling `match_entities` with that transport sends the records
and may incur cost. Do not send customer data without explicit authorization.
Supply credentials securely at runtime; never commit or paste them into issues.

The adapter checks response type, model, choice, confidence, and probability
distribution and returns human review on errors. A model result is only a
recommendation; confidence does not authorize a repair. Live behavior, pricing,
and deployment are not validated by mock tests. See
[TypeSafe Choice documentation](https://docs.typesafe.ai/primitives/choice)
and [model documentation](https://docs.typesafe.ai/models).
