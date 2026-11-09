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
