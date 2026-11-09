# Evidence-linked explanations

`explain_evidence` returns supplied observations unchanged and places all
provider-generated text in a separate hypotheses section. Every hypothesis
must cite one or more valid zero-based observation indices. Provider errors,
invalid output and invalid references yield `provider_unavailable` and no
hypotheses. Successful explanations still require human review.

`GrokExplanationProvider` constructs an xAI Responses-style request with
structured output, an explicit model, no tools, and `store: false`. It accepts
an injected transport; there is no built-in network client or credential
handling. The test transport is simulated. Actual Grok API compatibility and
model availability have not been live-verified. See the
[xAI Responses reference](https://docs.x.ai/developers/rest-api-reference/inference)
and [structured outputs documentation](https://docs.x.ai/developers/model-capabilities/text/structured-outputs).

Citations prove only that a supplied evidence index exists; they do not prove
that the hypothesis follows from it. Models can invent or contradict facts,
misinterpret evidence, or follow malicious text embedded in data. Treat all
hypotheses as unverified, do not make repair decisions from them, and require
human review. Do not send customer data to an external provider without
explicit authorization. Calls and model output are not integrated with the
decision ledger; no Grok costs or calls occur through this code by itself.
