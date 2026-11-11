# Gates: Local API access guard

Scope: Enforce the existing local-only prototype boundary; do not claim production security.
Issue: Owner requested checking the screen and API security after PRs #32 and #33.
Base commit: f0f1f05f9b51a81229ad0e2d8edcc8a700efe780

- [x] G1: Loopback clients with local Host and matching Origin can use the local API.
  CHECK: uv run --locked pytest -q tests/test_local_access.py::test_local_requests
  EXPECT: 1 passed
  EVIDENCE: Linux, Python 3.12.14; exit 0; 1 passed; TestClient deprecation warning; see PR.

- [x] G2: Remote clients, non-local Host, untrusted Origin and forwarded headers fail closed.
  CHECK: uv run --locked pytest -q tests/test_local_access.py::test_untrusted_requests
  EXPECT: 1 passed
  EVIDENCE: Linux, Python 3.12.14; exit 0; 1 passed; TestClient deprecation warning; see PR.

- [x] G3: Full tests and Ruff pass.
  CHECK: uv run --locked pytest -q && uv run --locked ruff check .
  EXPECT: All checks passed!
  EVIDENCE: Linux, Python 3.12.14; exit 0; 89 passed; Ruff passed; one TestClient deprecation warning; see PR.

- [x] G4: The browser layout and synthetic upload flow are visually verified.
  EVIDENCE: Assistant checked Chromium desktop and synthetic upload: 7 rows, 5 columns, 2 findings. No mobile or cross-browser verification.

- [ ] G5: Production authentication, authorization, tenant isolation, upload lifecycle and durable auditing are independently verified.
  EVIDENCE: pending; local access guard does not implement production controls.

- [ ] G6: Founder reviews and merges.
  EVIDENCE: pending founder review.
