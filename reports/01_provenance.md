# 01. Provenance and benchmark environment

## Evidence

### GitHub Actions run

Public GitHub REST API metadata was saved in
[`manifests/github_run.json`](../manifests/github_run.json) and the 26-artifact
inventory in [`manifests/github_artifacts.json`](../manifests/github_artifacts.json).

| Field | Expected | Verified actual |
|---|---|---|
| Repository | `SemiAnalysisAI/InferenceX` | `SemiAnalysisAI/InferenceX` (public) |
| Run | `29820102138` | `29820102138`, completed / success |
| Head SHA | `3ac9ddfd8161c96ec7e18b1bcfab340369185fcf` | exact match |
| Branch | `explore/glm52-h200-agentx-pp-pareto` | exact match |
| Workflow | — | `End-to-End Tests` (`.github/workflows/e2e-tests.yml`, workflow ID `202452638`) |
| Display title | — | `e2e Test - GLM-5.2 FP8 H200 AgentX HiSparse complete c1-c8 sweep unofficial` |
| Matrix jobs | expected c1–c8 | eight successful `multi-node agentic` jobs, one each for c1–c8 |

The run's `referenced_workflows` entries are all pinned to the verified head SHA.
The eight job names state `glm5.2 fp8`, `cluster:h200-dgxc`, `dyn-sgl`, `1P
(TP1/PCP8) x 1D (TP8/DPA)`, DRAM KV offload, HiSparse, and their respective
concurrency. This is direct run metadata, not an interpretation of trace data.

### Artifact inventory

The API returned 26 artifacts: eight raw `agentic_...` artifacts, eight aggregated
`bmk_agentic_...` artifacts, eight server-log artifacts, `results_bmk`, and
`run-stats`. All 18 requested raw/aggregate/summary artifacts are currently
`expired: false`, with API expiry `2026-10-19T09:54:08Z`. The expected IDs for c1–c8,
`results_bmk` (`8497663596`), and `run-stats` (`8497677426`) all match the API
inventory. Names, byte sizes, SHA-256 digests supplied by GitHub, and timestamps are
preserved in the manifests.

An authenticated GitHub CLI retrieved all 18 requested ZIP archives. Each local
archive SHA-256 exactly matches the API-provided artifact digest; ZIP CRC validation
and extraction succeeded. The eight raw artifacts each contain a
`profile_export.jsonl`; the eight aggregate artifacts each contain the canonical
aggregate JSON. The per-artifact archive path, digest, extraction list, and validation
status are recorded in [`manifests/downloads.json`](../manifests/downloads.json).

### InferenceX source

The public source repository was cloned at `vendor/InferenceX` and detached at
`3ac9ddfd8161c96ec7e18b1bcfab340369185fcf`; the checkout is full (not shallow) and
clean. This is a local clone rather than a submodule, recorded in
[`vendor/README.md`](../vendor/README.md) and
[`manifests/provenance.json`](../manifests/provenance.json). The commit subject is
`test: prepare complete HiSparse AgentX sweep`.

The selected source configuration is
`configs/nvidia-master.yaml:8049-8080`, key
`glm5.2-fp8-h200-dynamo-sglang-agentic-hisparse-pareto`:

- target model `zai-org/GLM-5.2-FP8`, FP8, `dynamo-sglang`, `cluster:h200-dgxc`;
- `kv-p2p-transfer: mooncake`, disaggregated multi-node mode, DRAM KV offload and
  `hisparse` backend;
- concurrency list `[1, 2, 3, 4, 5, 6, 7, 8]`;
- one prefill worker `TP1/PCP8` and one decode worker `TP8` with DP attention.

The referenced recipe
`benchmarks/multi_node/srt-slurm-recipes/sglang/glm5.2/agentic/disagg-h200-1p1d-pcp8-tp8-dp8-hisparse.yaml:6-130`
independently specifies `h200`, one 8-GPU prefill node and one 8-GPU decode node
(16 H200 total), Dynamo frontend, SGLang backend, prefill/decode disaggregation,
Mooncake transfer, 1,048,576-token context/max-total-token limits, and HiSparse
decode (`flashmla_sparse`, `enable-hisparse: true`).

`benchmarks/benchmark_lib.sh:1709-1726` maps loader
`semianalysis_cc_traces_weka_062126` to
`semianalysisai/cc-traces-weka-062126`. The recipe sets that exact override at line
130. `benchmark_lib.sh:1759-1869` constructs the AIPerf AgentX replay command,
passes the concurrency and benchmark duration, samples warmup start positions in
25–75% of each trajectory, uses a 600-second agentic cache warmup, requests up to
393 dataset entries, and writes output artifacts. `agentic_srt.sh:112-131` explains
that sequential concurrency points use a disjoint first-turn cache-bust keyspace
while each point's own warmup and profiling share markers.

The workflow uploads raw agentic data from `LOGS/agentic/**`, excluding
`inputs.json` and `profile_export_raw.jsonl`, and uploads aggregate JSON separately
(`.github/workflows/benchmark-multinode-tmpl.yml:359-375`). The in-repo aggregate
filter treats missing `benchmark_phase` as profiling but drops non-profiling and
error rows (`utils/agentic/aggregation/request_metrics.py:25-62`). It computes
`inter_token_latency` as both `itl` and `tpot` summary series
(`request_metrics.py:148-171`); that verifies the source's aggregation naming, not
that every artifact field has yet been observed.

The retrieved raw `benchmark_command.txt` for conc1 and conc8 directly verifies an
`aiperf profile` replay against `http://localhost:8000/v1/chat/completions`, streaming
mode, target model `zai-org/GLM-5.2-FP8`, respective concurrency, 3,600-second
benchmark duration, seed 42, trajectory start ratio 0.25–0.75, 600-second agentic
cache warmup, 1,800-second warmup grace, server token counting, Dynamo
conversation-aware routing, 3,600-second session timeout, no GPU telemetry, 393
dataset entries, and `semianalysis_cc_traces_weka_062126` source selection.

### Hugging Face source trace

The public dataset API reports immutable revision
`23f152f6f0f9399a85901b89a6458def0ef16729` (last modified
2026-06-21T17:48:50Z), not gated and not private. The immutable
`traces.jsonl` object advertises 1,847,151,435 bytes. It was downloaded with the
Xet-enabled Hugging Face client into a separate staging directory, then promoted only
after validation. The final local file has exactly 1,847,151,435 bytes and SHA-256
`29b6a19e751ff5230771519aab755f80a0f43a4ba9cf96b72d3a6a437ec99276`, which matches
the Hub's immutable `x-linked-etag`. A streaming JSONL check found 393 non-empty,
valid objects and 393 unique root IDs; every top-level record has the expected
`block_size`, `hash_id_scope`, `id`, `models`, and `requests` keys.

The dataset README and `stats.txt` at the same revision state 393 traces, 56,798
main turns, 1,697 subagent groups, 42,029 subagent inner requests, and 98,827 total
model requests. The later source-flattening step is responsible for independently
recomputing the detailed counts from the local source file.

## Inference

The actual source configuration and the GitHub job names jointly support describing
this experiment as: **Claude Code-originated workload traces replayed by target
GLM-5.2 FP8 on a shared 16×H200 Dynamo+SGLang prefill/decode-disaggregated system**.
Confidence is high for the server environment and workload selection because each
has both run metadata and same-SHA source configuration evidence.

This does **not** mean a Claude-labelled source request was served by Claude on an
H200. Any source `model` value is workload provenance and must remain distinct from
the target GLM-5.2 model.

## Unknown / limitations

- The public artifacts establish shared-run configuration and request records, not a
  GPU allocation, utilization, or hardware-affinity mapping for any conversation ID.
- The raw command establishes the dispatched replay options, but it does not expose a
  per-request actual cache-residency/hit metric. Source hash-prefix calculations are
  therefore theoretical workload reuse only.
- Source-model labels remain provenance labels for the original Claude Code workload;
  they are not target-model measurements. H200 latency claims in subsequent reports
  refer only to the target GLM-5.2 FP8 replay.
