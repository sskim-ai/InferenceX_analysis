# 11. ID03 public H200 deep dive

## Canonical ID resolution

### Evidence

- Primary trace: 07dd40536557a1d6440a923557c3129dc929. The requested prefix 07dd405 is accepted only because the versioned resolution table reports a unique full source-trace ID.

| id_label | requested_value | requested_value_type | resolved_full_source_trace_id | resolution_match_count | resolution_status | candidate_full_ids | present_c8 | present_c12 | present_c16 | present_hisparse_c8 | notes | all_request_count_c8 | warmup_request_count_c8 | profiling_phase_count_c8 | successful_profile_request_count_c8 | error_count_c8 | cancellation_count_c8 | all_request_count_c12 | warmup_request_count_c12 | profiling_phase_count_c12 | successful_profile_request_count_c12 | error_count_c12 | cancellation_count_c12 | all_request_count_c16 | warmup_request_count_c16 | profiling_phase_count_c16 | successful_profile_request_count_c16 | error_count_c16 | cancellation_count_c16 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ID03 | 07dd405 | prefix | 07dd40536557a1d6440a923557c3129dc929 | 1 | unique | 07dd40536557a1d6440a923557c3129dc929 | True | True | True | False | Evidence: full ID resolved by strict startswith() over source/H200 ID universe. | 119 | 0 | 119 | 119 | 0 | 0 | 119 | 7 | 112 | 112 | 0 | 0 | 26 | 13 | 13 | 13 | 0 | 0 |

## c8 / c12 / c16 source-turn coverage

### Evidence

| concurrency | all_request_count | warmup_count | profiling_phase_count | successful_profiling_count | distinct_exact_source_key_count_profile | source_coverage_ratio_profile | source_request_index_min | source_request_index_max | source_input_tokens_min | source_input_tokens_max | wall_span_s | error_count | cancellation_count | duplicate_exact_source_key_count_profile |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | 119 | 0 | 119 | 119 | 119 | 1 | 0 | 118 | 30784 | 117696 | 482.691 | 0 | 0 | 0 |
| 12 | 119 | 7 | 112 | 112 | 112 | 0.941176 | 0 | 118 | 30784 | 117696 | 1392.31 | 0 | 0 | 0 |
| 16 | 26 | 13 | 13 | 13 | 13 | 0.109244 | 7 | 118 | 61248 | 117696 | 1353.97 | 0 | 0 | 0 |

### Replay scheduling evidence

| concurrency | evidence_type | value | classification | source_file | source_line | scope_note |
| --- | --- | --- | --- | --- | --- | --- |
| 8 | benchmark_duration_s | 3600 | Evidence | data/raw/h200_gpu_resident_mtp/conc8/result/9017979109/conc_8/benchmark_command.txt | 1 | AIPerf command setting; not a per-ID measurement |
| 8 | trajectory_start_ratio | 0.25_to_0.75 | Evidence | data/raw/h200_gpu_resident_mtp/conc8/result/9017979109/conc_8/benchmark_command.txt | 1 | AIPerf command setting; not a per-ID measurement |
| 8 | warmup_requests_per_lane | 10 | Evidence | data/raw/h200_gpu_resident_mtp/conc8/result/9017979109/conc_8/benchmark_command.txt | 1 | AIPerf command setting; not a per-ID measurement |
| 8 | dataset_entries | 393 | Evidence | data/raw/h200_gpu_resident_mtp/conc8/result/9017979109/conc_8/benchmark_command.txt | 1 | AIPerf command setting; not a per-ID measurement |
| 8 | warmup_profile_handoff | 2026-08-08 05:23:13.433 - PhaseRunner - INFO - All accelerated-warmup wire requests returned; preserving paused DAG work for profiling handoff. | Evidence | data/raw/h200_gpu_resident_mtp/conc8/result/9017979109/conc_8/aiperf_artifacts/logs/aiperf.log | 80 | Raw AIPerf runtime-log line; raw log remains Git-ignored |
| 8 | profiling_recycling | 2026-08-08 05:23:13.655 - AgenticReplayTiming - INFO - PROFILING setup: 8 trajectory lanes; recycle draws roots from the dataset sampler | Evidence | data/raw/h200_gpu_resident_mtp/conc8/result/9017979109/conc_8/aiperf_artifacts/logs/aiperf.log | 88 | Raw AIPerf runtime-log line; raw log remains Git-ignored |
| 12 | benchmark_duration_s | 3600 | Evidence | data/raw/h200_gpu_resident_mtp/conc12/result/9019209525/conc_12/benchmark_command.txt | 1 | AIPerf command setting; not a per-ID measurement |
| 12 | trajectory_start_ratio | 0.25_to_0.75 | Evidence | data/raw/h200_gpu_resident_mtp/conc12/result/9019209525/conc_12/benchmark_command.txt | 1 | AIPerf command setting; not a per-ID measurement |
| 12 | warmup_requests_per_lane | 10 | Evidence | data/raw/h200_gpu_resident_mtp/conc12/result/9019209525/conc_12/benchmark_command.txt | 1 | AIPerf command setting; not a per-ID measurement |
| 12 | dataset_entries | 393 | Evidence | data/raw/h200_gpu_resident_mtp/conc12/result/9019209525/conc_12/benchmark_command.txt | 1 | AIPerf command setting; not a per-ID measurement |
| 12 | warmup_profile_handoff | 2026-08-08 07:13:15.173 - PhaseRunner - INFO - All accelerated-warmup wire requests returned; preserving paused DAG work for profiling handoff. | Evidence | data/raw/h200_gpu_resident_mtp/conc12/result/9019209525/conc_12/aiperf_artifacts/logs/aiperf.log | 101 | Raw AIPerf runtime-log line; raw log remains Git-ignored |
| 12 | profiling_recycling | 2026-08-08 07:13:15.388 - AgenticReplayTiming - INFO - PROFILING setup: 12 trajectory lanes; recycle draws roots from the dataset sampler | Evidence | data/raw/h200_gpu_resident_mtp/conc12/result/9019209525/conc_12/aiperf_artifacts/logs/aiperf.log | 109 | Raw AIPerf runtime-log line; raw log remains Git-ignored |
| 16 | benchmark_duration_s | 3600 | Evidence | data/raw/h200_gpu_resident_mtp/conc16/result/9020484364/conc_16/benchmark_command.txt | 1 | AIPerf command setting; not a per-ID measurement |
| 16 | trajectory_start_ratio | 0.25_to_0.75 | Evidence | data/raw/h200_gpu_resident_mtp/conc16/result/9020484364/conc_16/benchmark_command.txt | 1 | AIPerf command setting; not a per-ID measurement |
| 16 | warmup_requests_per_lane | 10 | Evidence | data/raw/h200_gpu_resident_mtp/conc16/result/9020484364/conc_16/benchmark_command.txt | 1 | AIPerf command setting; not a per-ID measurement |
| 16 | dataset_entries | 393 | Evidence | data/raw/h200_gpu_resident_mtp/conc16/result/9020484364/conc_16/benchmark_command.txt | 1 | AIPerf command setting; not a per-ID measurement |
| 16 | id03_initial_trajectory_state | 2026-08-08 08:53:17.737 - aiperf.timing.trajectory_source - INFO -     lane=13  sample_time= 68%  root_next=  8/9   ( 89% turns)  live=3 ready=2  trace_id=07dd40536557a1d6440a923557c3129dc929 | Evidence | data/raw/h200_gpu_resident_mtp/conc16/result/9020484364/conc_16/aiperf_artifacts/logs/aiperf.log | 70 | Raw AIPerf runtime-log line; raw log remains Git-ignored |
| 16 | warmup_profile_handoff | 2026-08-08 09:10:06.093 - PhaseRunner - INFO - All accelerated-warmup wire requests returned; preserving paused DAG work for profiling handoff. | Evidence | data/raw/h200_gpu_resident_mtp/conc16/result/9020484364/conc_16/aiperf_artifacts/logs/aiperf.log | 124 | Raw AIPerf runtime-log line; raw log remains Git-ignored |
| 16 | profiling_recycling | 2026-08-08 09:10:06.310 - AgenticReplayTiming - INFO - PROFILING setup: 16 trajectory lanes; recycle draws roots from the dataset sampler | Evidence | data/raw/h200_gpu_resident_mtp/conc16/result/9020484364/conc_16/aiperf_artifacts/logs/aiperf.log | 132 | Raw AIPerf runtime-log line; raw log remains Git-ignored |

- **Evidence:** these rows preserve the relevant AIPerf log evidence for the fixed profiling duration, randomized trajectory starts, warmup handoff, and root recycling. They describe the replay process; they do not assign a causal latency effect to one mechanism.
### Exact observed source-position coverage

- **Evidence (c12):** warmup source-request indices: `0–6`; successful profiling source-request indices: `7–118`. The full exact index list is retained in `../processed/id03_source_coverage_by_concurrency.csv`.

- **Evidence (c16):** warmup source-request indices: `7; 37–39; 81–89`; successful profiling source-request indices: `90–101; 118`. The full exact index list is retained in `../processed/id03_source_coverage_by_concurrency.csv`.


## Inference

- c8 is the primary public comparison reference because it covers all 119 distinct ID03 source keys as successful profiling requests and has 119 ITL-valid requests. c12 covers 112/119 keys after seven ID03 warmup rows; c16 covers 13/119 profiling keys and is a late-tail subset rather than a whole-trace estimate.
- The fixed 3,600-second profiling window, randomized trajectory start positions, warmup handoff, recycling, and mixed-workload scheduling are evidence-backed contributors to coverage differences. They do not identify one sufficient cause for every missing ID03 source key.

## Unknown

- The public data does not expose the counterfactual schedule that would prove exactly why a specific key was absent in a run, nor does it make the c16 tail a random or representative sample of the full ID03 trace.

## Exact c8 ↔ c12 ↔ c16 request matching

### Evidence

| pair | left_concurrency | right_concurrency | matched_source_key_count | same_output_length_count | strict_ttft_count | strict_decode_count | median_ttft_ratio_right_over_left | p90_ttft_ratio_right_over_left | median_itl_ratio_right_over_left | weighted_itl_left_ms | weighted_itl_right_ms | weighted_itl_ratio_right_over_left | median_e2e_ratio_right_over_left | coverage_overlap_ratio_jaccard | matching_method |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| c8_c12 | 8 | 12 | 112 | 112 | 112 | 112 | 1.45117 | 14.064 | 0.992266 | 11.1574 | 11.3219 | 1.01475 | 1.14901 | 0.941176 | source_trace_id+source_outer_idx+source_inner_idx; source-key median per concurrency |
| c8_c16 | 8 | 16 | 13 | 13 | 13 | 13 | 1.28084 | 17.2266 | 1.00834 | 10.962 | 11.4114 | 1.041 | 1.14554 | 0.109244 | source_trace_id+source_outer_idx+source_inner_idx; source-key median per concurrency |
| c12_c16 | 12 | 16 | 13 | 13 | 13 | 13 | 0.32583 | 11.2269 | 1.00706 | 11.3456 | 11.4114 | 1.0058 | 0.894576 | 0.116071 | source_trace_id+source_outer_idx+source_inner_idx; source-key median per concurrency |

- Matching key: source_trace_id + source_outer_idx + source_inner_idx. Source conversation path and turn index are retained as validation fields. Pair rows first collapse repeated source-key/concurrency records before ratios.
- Full reviewable pair data: ../processed/id03_exact_match_c8_c12.csv, ../processed/id03_exact_match_c8_c16.csv, ../processed/id03_exact_match_c12_c16.csv, and ../processed/id03_exact_match_all.csv.

### Inference

- On the large c8↔c12 overlap, median TTFT rises while weighted ITL changes modestly. The c8↔c16 overlap is only 13 exact keys, so it supports a tail-subset comparison rather than a full-trace concurrency curve.

### Unknown

- Matching a source key controls workload identity, not all system state, queue position, MTP behavior, route, or cache residency. It cannot isolate a pure concurrency effect.

## ID03 H200 scaling curve

### Evidence

| concurrency | profile_request_count | coverage_ratio | distinct_exact_source_key_count | ttft_mean_ms | ttft_median_ms | ttft_p90_ms | ttft_p95_ms | itl_sample_count | weighted_itl_ms | weighted_decode_tps | e2e_median_ms | e2e_p90_ms | wall_span_s | wall_output_tps | output_tokens_total | ttft_inflation_vs_c8 | tps_retention_vs_c8 | wall_throughput_ratio_vs_c8 | weighting |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | 119 | 1 | 119 | 2709.92 | 1080.57 | 3326.14 | 6497.04 | 119 | 11.0553 | 90.4544 | 3604.66 | 8113.73 | 482.691 | 77.9692 | 37635 | 1 | 1 | 1 | output-transition-token-weighted ITL; wall output TPS is parallel-system rate |
| 12 | 112 | 0.941176 | 112 | 7037.98 | 1729.72 | 17659.2 | 27469.3 | 112 | 11.3219 | 88.3243 | 4614.45 | 22447.9 | 836.789 | 38.0921 | 31875 | 1.60075 | 0.976452 | 0.488553 | output-transition-token-weighted ITL; wall output TPS is parallel-system rate |
| 16 | 13 | 0.109244 | 13 | 18173.7 | 1647.92 | 41057.6 | 73862.1 | 13 | 11.4114 | 87.6317 | 7859.8 | 41702.7 | 301.854 | 13.003 | 3925 | 1.52505 | 0.968795 | 0.166771 | output-transition-token-weighted ITL; wall output TPS is parallel-system rate |

- TTFT inflation is relative to ID03 c8. TPS retention is based on output-transition-token-weighted ITL; wall output TPS is a parallel-system rate and is intentionally distinct.

### Inference

- c12/c16 preserve much of the observed active decode TPS for the covered keys, whereas TTFT and wall-output outcomes are more coverage- and scheduling-sensitive. This is not an apples-to-apples local scaling conclusion.

### Unknown

- No per-ID GPU allocation, GPU utilization, or fixed worker affinity follows from this curve; the public run is a shared 32×H200 system.

## c8 latency and workload-shape reference

### Evidence

| summary_type | metric | bucket | quantile | value | sample_count | weighting | ttft_median_ms | ttft_p90_ms | weighted_itl_ms | weighted_decode_tps | output_tokens_total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| latency_quantile | ttft_ms |  | P10 | 797.231 | 119 | request-level quantile |  |  |  |  |  |
| latency_quantile | ttft_ms |  | P25 | 938.143 | 119 | request-level quantile |  |  |  |  |  |
| latency_quantile | ttft_ms |  | P50 | 1080.57 | 119 | request-level quantile |  |  |  |  |  |
| latency_quantile | ttft_ms |  | P75 | 1655.56 | 119 | request-level quantile |  |  |  |  |  |
| latency_quantile | ttft_ms |  | P90 | 3326.14 | 119 | request-level quantile |  |  |  |  |  |
| latency_quantile | ttft_ms |  | P95 | 6497.04 | 119 | request-level quantile |  |  |  |  |  |
| latency_quantile | ttft_ms |  | P99 | 37471.2 | 119 | request-level quantile |  |  |  |  |  |
| latency_quantile | itl_ms |  | P10 | 10.4626 | 119 | request-level quantile |  |  |  |  |  |
| latency_quantile | itl_ms |  | P25 | 10.6352 | 119 | request-level quantile |  |  |  |  |  |
| latency_quantile | itl_ms |  | P50 | 10.8978 | 119 | request-level quantile |  |  |  |  |  |
| latency_quantile | itl_ms |  | P75 | 11.8085 | 119 | request-level quantile |  |  |  |  |  |
| latency_quantile | itl_ms |  | P90 | 12.3406 | 119 | request-level quantile |  |  |  |  |  |
| latency_quantile | itl_ms |  | P95 | 13.6424 | 119 | request-level quantile |  |  |  |  |  |
| latency_quantile | itl_ms |  | P99 | 15.8699 | 119 | request-level quantile |  |  |  |  |  |
| latency_quantile | e2e_ms |  | P10 | 2449.8 | 119 | request-level quantile |  |  |  |  |  |
| latency_quantile | e2e_ms |  | P25 | 2931.77 | 119 | request-level quantile |  |  |  |  |  |
| latency_quantile | e2e_ms |  | P50 | 3604.66 | 119 | request-level quantile |  |  |  |  |  |
| latency_quantile | e2e_ms |  | P75 | 5065.28 | 119 | request-level quantile |  |  |  |  |  |
| latency_quantile | e2e_ms |  | P90 | 8113.73 | 119 | request-level quantile |  |  |  |  |  |
| latency_quantile | e2e_ms |  | P95 | 18720.8 | 119 | request-level quantile |  |  |  |  |  |
| latency_quantile | e2e_ms |  | P99 | 46319.8 | 119 | request-level quantile |  |  |  |  |  |
| output_length_bucket | mixed_latency_and_decode | 1 |  |  | 0 | ITL is output-transition-token weighted within bucket |  |  |  |  |  |
| output_length_bucket | mixed_latency_and_decode | 2-32 |  |  | 1 | ITL is output-transition-token weighted within bucket | 6376.33 | 6376.33 | 34.2579 | 29.1903 | 2 |
| output_length_bucket | mixed_latency_and_decode | 33-128 |  |  | 21 | ITL is output-transition-token weighted within bucket | 1505.41 | 3306.62 | 11.8463 | 84.4146 | 2326 |
| output_length_bucket | mixed_latency_and_decode | 129-512 |  |  | 90 | ITL is output-transition-token weighted within bucket | 1036.38 | 3021.43 | 11.1828 | 89.4233 | 20698 |
| output_length_bucket | mixed_latency_and_decode | 513-2048 |  |  | 4 | ITL is output-transition-token weighted within bucket | 1510.65 | 2115.9 | 11.134 | 89.815 | 3698 |
| output_length_bucket | mixed_latency_and_decode | >2048 |  |  | 3 | ITL is output-transition-token weighted within bucket | 869.968 | 1098.21 | 10.6185 | 94.175 | 10911 |

### Source-workload input proxy buckets

| source_input_token_bucket | request_count | source_input_tokens_min | source_input_tokens_max | ttft_median_ms | ttft_p90_ms | weighted_itl_ms | weighted_decode_tps | output_tokens_total | metric_scope |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <32k | 3 | 30784 | 30912 | 765.674 | 1378.13 | 10.8128 | 92.4832 | 432 | source-workload input proxy; not target GLM logical context |
| 32-64k | 26 | 33088 | 62336 | 903.985 | 2509.08 | 10.5575 | 94.7194 | 13377 | source-workload input proxy; not target GLM logical context |
| 64-128k | 90 | 64704 | 117696 | 1121.28 | 3996.7 | 11.3397 | 88.1859 | 23826 | source-workload input proxy; not target GLM logical context |
| 128-192k | 0 |  |  |  |  |  |  |  | source-workload input proxy; not target GLM logical context |
| 192-256k | 0 |  |  |  |  |  |  |  | source-workload input proxy; not target GLM logical context |
| 256k+ | 0 |  |  |  |  |  |  |  | source-workload input proxy; not target GLM logical context |

- The plotted c8 ordinal curves are in ../figures/id03_source_input_vs_ordinal.png, ../figures/id03_ttft_vs_ordinal.png, ../figures/id03_itl_vs_ordinal.png, and ../figures/id03_output_tokens_vs_ordinal.png.
- Source input tokens are a workload proxy only. They are not target GLM logical context tokens or a measured GPU prefill-throughput denominator.

## 202,752-context compatible subset

### Evidence

| context_202752_subset_status | reason | logical_prompt_metric_observed_row_count | forbidden_proxies | required_future_evidence |
| --- | --- | --- | --- | --- |
| unavailable_exact_target_tokenization | no_request_level_target_model_logical_prompt_metric_in_public_profile_or_join | 0 | input_sequence_length; source_input_tokens | exact target logical prompt tokens + requested output limit + documented loader/server fit rule |

- The companion CSV ../processed/id03_context_202752_compatible_requests.csv is intentionally header-only when the exact target-tokenization fit condition cannot be evaluated.

### Inference

- A future local comparison must use exact local target logical prompt tokens plus requested output limit, or the documented loader/server fit rule, before declaring a public request compatible with max_model_len 202752.

### Unknown

- No request-level target-model logical prompt metric, requested output limit, or joinable frontend metric exists in the public profile package. input_sequence_length and source_input_tokens must not be substituted for that missing condition.

## Why ID03 is the primary local-comparison candidate

### Evidence

- ID03 has whole-trace c8 profiling coverage, 119 ITL-valid c8 observations, per-source-key c8/c12/c16 exact-match exports, and c8 latency/output-shape distributions.
- The canonical public request reference is ../processed/id03_h200_reference_requests.csv.

### Inference

- This makes ID03 the strongest available public H200 reference for a later local cpy comparison, provided the local extractor demonstrates matching source keys and workload semantics.

### Unknown

- It does not make public c8 equivalent to local cpy8: public c8 is mixed-root global concurrency on 2P2D 32×H200 with MTP, whereas the meaning of local cpy labels still requires raw local configuration and request evidence.
