# H200 AgentX Conversation-ID Benchmark Analysis

This repository is a reproducible analysis pipeline for the public InferenceX GitHub Actions run `29820102138`. It links source workload trace IDs from `semianalysisai/cc-traces-weka-062126` to observed H200 replay records, where available.

The source trace `model` field is a workload-provenance label from the original Claude Code collection. It is not the target model. The benchmark target is expected to be GLM-5.2 FP8 replayed on a shared 16×H200 system; every expected configuration value is revalidated against actual run metadata and source/config evidence.

## Studies

- **Study A — H200 HiSparse AgentX:** GitHub Actions run `29820102138`, the historical baseline retained in the repository root (`reports/`, `data/processed/`, and `figures/`).
- **Study B — H200 GPU-resident KV + MTP AgentX:** GitHub Actions run `31235207041`, analyzed without changing Study A under [studies/h200_gpu_resident_mtp](studies/h200_gpu_resident_mtp/README.md).

Study B compares public c8/c12/c16 replay evidence and retains the c8 HiSparse comparison only as an observed system-level difference. It does not assign a conversation ID to any GPU.

## Quick start

```sh
make bootstrap
make all
```

`make all` is deliberately honest about missing public data or credentials: it builds the scaffold and records unblock commands in `NEEDS_INPUT.md` rather than inventing measurements.

## Outputs

- `manifests/`: source/run provenance, artifact inventory, local download checksums.
- `data/processed/`: derived tables (not versioned when large).
- `reports/results_summary_ko.md`: Korean evidence/inference/unknown summary.
- `figures/`: PNG figures generated only from available analysis tables.

## Important interpretation limits

- `api_time` in the source trace is not H200 latency.
- A conversation ID identifies a workload trace, not a GPU allocation or affinity.
- `session_num` is retained as an opaque grouping field, but its replay-instance
  semantics are unvalidated. In this run it is unique per profiling row within
  each concurrency, so it does not de-correlate repetitions; paired bootstrap
  summaries cluster conservatively by root trace ID.
- Theoretical prefix reuse from source hash IDs is not an observed server cache-hit metric.
