# Local CSV analysis API prototype

This is a synchronous, process-local prototype for synthetic data only. It has
no authentication, tenant isolation, durable jobs, upload deletion, or
production security controls. Do not expose it to a network or use customer
data. Uploaded CSV bytes remain in process memory until process exit, and
capacity is limited to 16 uploads per app instance. Each upload is limited to
1,000,000 bytes. No files are written by this code.

From the repository root, start a local server:

```sh
uv sync --locked
uv run --locked uvicorn --app-dir src data_repair_copilot.api.app:create_app --factory --host 127.0.0.1
```

`POST /uploads` accepts a raw UTF-8 CSV request body with `Content-Type:
text/csv`. It validates the data and returns an `upload_id` and dimensions.
`POST /analyses/{upload_id}` performs a synchronous in-memory analysis and
returns missing-value and exact duplicate-row findings. It is not a queued job;
IDs and uploaded bytes are lost on process exit. There is no application UI,
CSV file picker, authenticated access, model call, persisted audit trail, or
repaired export. Multipart form upload is not supported.

The CSV parser preserves identifiers and quoted newlines according to the
existing loader. Results contain row positions, not stable record identifiers.
Capacity, memory use and responsiveness are not production benchmarks.

## Local review and export prototype

`POST /uploads/{upload_id}/previews` accepts `proposals` and creates an
in-memory review snapshot. `POST /reviews/{review_id}/decisions` accepts one
approve/reject decision and caller-supplied metadata per change. After that,
`GET /reviews/{review_id}/audit` returns a local report and
`GET /reviews/{review_id}/export` returns a new CSV. The source bytes remain
unchanged. CSV export fails when a reviewed result contains null values, because
CSV cannot distinguish null from an empty string. Up to 32 review snapshots
are held in process memory; all are lost on process exit.

**This is a simulation for local synthetic data, not authenticated human
approval.** Any caller with access to the service can submit decisions and
claim any reviewer name. The audit report is caller-attested, not durable,
authenticated, or tamper-evident. The service has no tenant isolation or
production security; do not expose it on a network or use customer data.
The original export bundle is a separate local file operation; these endpoints
return a CSV and an audit JSON response rather than that bundle.

## Local upload and overview

Open `http://127.0.0.1:8000/` after starting the local server to select a
synthetic CSV and view the row count, columns, distinct values and findings.
The screen calls the raw CSV upload, profile, and analysis endpoints; it does
not show raw sample values. `GET /uploads/{upload_id}/profile` returns the
existing deterministic profile with samples disabled. Actual nulls are counted
separately from empty strings, which are reported as missing by the detector.
This browser interface has no authentication or customer-data protections.
