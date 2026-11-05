# DR-021 local baseline

Run from the repository root:

```sh
uv sync --locked
uv run --locked python scripts/benchmark_local.py
```

The command emits JSON to standard output. Defaults: 100,000 synthetic rows,
10% intentionally invalid ZIP strings, one warm-up, and three timed runs.
`--rows` and `--repetitions` adjust the workload. The timer includes the
existing format detector and its result materialization. It excludes synthetic
data generation, CSV loading, I/O, and any other product stages. Counts are
checked on every run. This workload is deterministic but is not representative
of every customer dataset.

## Recorded local run

Run on 2026-11-04 (America/Chicago); Python 3.12.14; Polars 2.0.0;
Linux 6.18.57 x86_64 (glibc 2.41); processor model unavailable in runtime.
100,000 rows; 10,000 invalid expected and observed; one warm-up and three
measurements. Elapsed seconds: 0.049205, 0.048298, 0.048070; median 0.048298.
Values are rounded; timing varies by hardware, load and runtime. This is not an
end-to-end latency or a performance guarantee.

| Measurement | Local ZIP check | AI workload |
| --- | --- | --- |
| Latency | 0.048298 seconds median for 100,000 synthetic rows | Not measured |
| Cost | Not measured; local compute is not assumed free | Not measured |

## Unmet comparison

No model integration or comparable AI measurement exists in this repository.
AI calls can incur charges and require owner approval; do not send customer
data. ZIP validation is deterministic and the agent charter excludes using an
AI model for such checks. A meaningful AI comparison requires a separately
approved, comparable semantic workload, a pinned model/provider, synthetic
evaluation data, measured latency and usage, a dated price source, and a
spend limit. Until then, the tracker requirement to compare local processing
and AI calls remains unmet. Do not infer cost or speed from the unavailable
cells above.
