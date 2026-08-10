# 12. ID03 local cpy comparison plan

## Public reference selected for the later comparison

### Evidence

- Canonical ID03 source trace: 07dd40536557a1d6440a923557c3129dc929.

| concurrency | profile_request_count | coverage_ratio | distinct_exact_source_key_count | ttft_mean_ms | ttft_median_ms | ttft_p90_ms | ttft_p95_ms | itl_sample_count | weighted_itl_ms | weighted_decode_tps | e2e_median_ms | e2e_p90_ms | wall_span_s | wall_output_tps | output_tokens_total | ttft_inflation_vs_c8 | tps_retention_vs_c8 | wall_throughput_ratio_vs_c8 | weighting |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | 119 | 1 | 119 | 2709.92 | 1080.57 | 3326.14 | 6497.04 | 119 | 11.0553 | 90.4544 | 3604.66 | 8113.73 | 482.691 | 77.9692 | 37635 | 1 | 1 | 1 | output-transition-token-weighted ITL; wall output TPS is parallel-system rate |
| 12 | 112 | 0.941176 | 112 | 7037.98 | 1729.72 | 17659.2 | 27469.3 | 112 | 11.3219 | 88.3243 | 4614.45 | 22447.9 | 836.789 | 38.0921 | 31875 | 1.60075 | 0.976452 | 0.488553 | output-transition-token-weighted ITL; wall output TPS is parallel-system rate |
| 16 | 13 | 0.109244 | 13 | 18173.7 | 1647.92 | 41057.6 | 73862.1 | 13 | 11.4114 | 87.6317 | 7859.8 | 41702.7 | 301.854 | 13.003 | 3925 | 1.52505 | 0.968795 | 0.166771 | output-transition-token-weighted ITL; wall output TPS is parallel-system rate |

- Public c8 is the primary H200 reference because it has full ID03 source-key profiling coverage. Its request-level source-key table is ../processed/id03_h200_reference_requests.csv.

### Inference

- Later analysis should compare both absolute matched-request values and scaling direction, not promote public c8 and local cpy8 to equivalent workloads.

### Unknown

- No local raw logs or local cpy measurements are present in this public study. No local metric is calculated here.

## Meaning of local cpy1–cpy8 to verify first

### Required local evidence for every cpy label

- cpy label; configured concurrency; observed maximum simultaneous requests; independent root-session count; distinct conversation-ID count; source-trace-ID count; request and successful-request counts per copy; start timestamps; and end timestamps.
- Show whether each copy executes the canonical ID03 sequence independently and whether AIPerf concurrency is actually N for cpyN.

### Unknown

- Whether cpyN is a same-trace replication label, global concurrency N, or N independent sessions remains unknown until the preceding fields are extracted from local config/logs.

## Exact join contract

- Read ../handoff/id03_local_join_contract.md before extracting local data. The canonical exact key is source_trace_id + source_outer_idx + source_inner_idx. Source conversation path and turn index validate the candidate match; a missing or conflicting validation field must be reported rather than silently accepted.
- For a strict TTFT subset: exact key, successful request on both systems, and both TTFT values. For a strict decode subset: strict TTFT conditions plus output_tokens > 1, ITL present, and equal observed output length.

## Context-limit contract

### Evidence

- Public H200 uses a 1,048,576-token context; the stated local maximum is 202,752. The public 202,752-compatible subset status is unavailable_exact_target_tokenization.

### Required local/public fit rule

- Use target logical prompt tokens + requested output limit <= 202752, or a documented exact loader/server fit condition. Do not replace target logical prompt tokens with public input_sequence_length or source_input_tokens.

## Metrics to calculate after local extraction

| Area | Required comparable metrics |
| --- | --- |
| Coverage | successful/transmitted/failed requests; first/last successful exact key; first failed key; context-overflow position |
| Tokens | total/mean/median/max input with semantics; cache read/load/store with scope; output tokens |
| TTFT | mean, median, P90, P95, max (ms) |
| Decode | ITL sample count; weighted ITL; weighted decode TPS; median decode TPS |
| End-to-end | E2E mean/median/P90; wall span; wall output TPS |
| System | GPU utilization; HBM used/free; KV block/token use; scheduler running/waiting requests, if available |

## Scaling definitions

- Local TPS retention at cpyN = weighted_decode_tps_cpyN / weighted_decode_tps_cpy1.
- Local median TTFT inflation at cpyN = median_ttft_cpyN / median_ttft_cpy1.
- Local wall-throughput scaling at cpyN = wall_output_tps_cpyN / wall_output_tps_cpy1.
- Public ID03 reference direction uses c8 as baseline: c12/c8 and c16/c8 in ../processed/id03_h200_scaling_curve.csv.

## Interpretation boundaries

### Evidence

- Public c8/c12/c16 is a mixed-root 2P2D, 32×H200, MTP-enabled replay. The public table retains coverage differences and MTP behavior.

### Inference

- Scaling behavior (where TTFT inflates, whether ITL/TPS retains, and wall-throughput changes) may be more informative than an unqualified absolute hardware ratio.

### Unknown

- Without local topology, MTP, KV, context-fit, and request-level evidence, no apples-to-apples hardware-efficiency or causal cache conclusion is allowed.
