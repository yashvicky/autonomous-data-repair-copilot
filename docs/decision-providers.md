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

A future Jev or other provider can implement the same protocol. This change
contains no Jev adapter, API call, credentials, timeout policy, retries, model
validation, or customer-data authorization. Provider-reported model metadata
is not verified by the interface. A real integration must record the exact
model version for evaluations, apply its own timeout and provenance controls,
and comply with the project's data and spending fences.

This interface does not review, authorize, or apply repairs. The existing human
approval workflow remains separate. Do not send customer data to a provider
without authorization or use model confidence as an automatic approval.
