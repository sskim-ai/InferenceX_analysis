# 05. Requested ID analysis

## Evidence

| id_label | requested_value | requested_value_type | resolved_full_source_trace_id | resolution_match_count | resolution_status | candidate_full_ids | present_c8 | present_c12 | present_c16 | present_hisparse_c8 | notes | all_request_count_c8 | warmup_request_count_c8 | profiling_phase_count_c8 | successful_profile_request_count_c8 | error_count_c8 | cancellation_count_c8 | all_request_count_c12 | warmup_request_count_c12 | profiling_phase_count_c12 | successful_profile_request_count_c12 | error_count_c12 | cancellation_count_c12 | all_request_count_c16 | warmup_request_count_c16 | profiling_phase_count_c16 | successful_profile_request_count_c16 | error_count_c16 | cancellation_count_c16 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ID01 | 0196085d85d2075a50b74cd8795ffbdcea9a | full | 0196085d85d2075a50b74cd8795ffbdcea9a | 1 | unique | 0196085d85d2075a50b74cd8795ffbdcea9a | True | True | True | True | Evidence: full ID resolved by strict startswith() over source/H200 ID universe. | 69 | 11 | 58 | 58 | 0 | 0 | 56 | 11 | 45 | 45 | 0 | 0 | 49 | 11 | 38 | 38 | 0 | 0 |
| ID02 | 02bc0afb13f7a2d9efa86c28511261d85c0e | full | 02bc0afb13f7a2d9efa86c28511261d85c0e | 1 | unique | 02bc0afb13f7a2d9efa86c28511261d85c0e | False | False | False | True | Evidence: full ID resolved by strict startswith() over source/H200 ID universe. | 8 | 8 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 0 |
| ID03 | 07dd405 | prefix | 07dd40536557a1d6440a923557c3129dc929 | 1 | unique | 07dd40536557a1d6440a923557c3129dc929 | True | True | True | False | Evidence: full ID resolved by strict startswith() over source/H200 ID universe. | 119 | 0 | 119 | 119 | 0 | 0 | 119 | 7 | 112 | 112 | 0 | 0 | 26 | 13 | 13 | 13 | 0 | 0 |
| ID04 | 264478 | prefix | 264478eebbb2068593da2293ea8b67b31d4e | 1 | unique | 264478eebbb2068593da2293ea8b67b31d4e | False | False | False | False | Evidence: full ID resolved by strict startswith() over source/H200 ID universe. | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ID05 | debc7f6 | prefix | debc7f69e2c2fb94909ecdca600b0a4abd48 | 1 | unique | debc7f69e2c2fb94909ecdca600b0a4abd48 | False | False | False | False | Evidence: full ID resolved by strict startswith() over source/H200 ID universe. | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### ID01

| root_trace_id | concurrency | profiled_request_count | ttft_median_ms | ttft_p90_ms | weighted_decode_tps | wall_output_tps | output_tokens_total | error_count | cancellation_count | decode_tps_comparison_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0196085d85d2075a50b74cd8795ffbdcea9a | 8 | 58 | 9300.9 | 31640.6 | 93.4123 | 0.287196 | 941 | 0 | 0 | suppressed_n_lt_3_descriptive_only |
| 0196085d85d2075a50b74cd8795ffbdcea9a | 12 | 45 | 29178.2 | 41582.9 |  | 0.0136758 | 45 | 0 | 0 | suppressed_n_lt_3_descriptive_only |
| 0196085d85d2075a50b74cd8795ffbdcea9a | 16 | 38 | 32193.5 | 86996.6 |  | 0.0115979 | 38 | 0 | 0 | suppressed_n_lt_3_descriptive_only |

### ID02

| root_trace_id | concurrency | profiled_request_count | ttft_median_ms | ttft_p90_ms | weighted_decode_tps | wall_output_tps | output_tokens_total | error_count | cancellation_count | decode_tps_comparison_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 02bc0afb13f7a2d9efa86c28511261d85c0e | 8 | 0 |  |  |  |  |  | 0 | 0 | suppressed_n_lt_3_descriptive_only |
| 02bc0afb13f7a2d9efa86c28511261d85c0e | 12 | 0 |  |  |  |  |  | 0 | 0 | suppressed_n_lt_3_descriptive_only |
| 02bc0afb13f7a2d9efa86c28511261d85c0e | 16 | 0 |  |  |  |  |  | 0 | 0 | suppressed_n_lt_3_descriptive_only |

### ID03

| root_trace_id | concurrency | profiled_request_count | ttft_median_ms | ttft_p90_ms | weighted_decode_tps | wall_output_tps | output_tokens_total | error_count | cancellation_count | decode_tps_comparison_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 07dd40536557a1d6440a923557c3129dc929 | 8 | 119 | 1080.57 | 3326.14 | 90.4544 | 77.9692 | 37635 | 0 | 0 | comparative_sample_size_available |
| 07dd40536557a1d6440a923557c3129dc929 | 12 | 112 | 1729.72 | 17659.2 | 88.3243 | 38.0921 | 31875 | 0 | 0 | comparative_sample_size_available |
| 07dd40536557a1d6440a923557c3129dc929 | 16 | 13 | 1647.92 | 41057.6 | 87.6317 | 13.003 | 3925 | 0 | 0 | comparative_sample_size_available |

### ID04

- **Unknown:** no public profiling rows or no unique resolution.


### ID05

- **Unknown:** no public profiling rows or no unique resolution.


- **Scope warning:** raw `usage_prompt_cache_read_tokens` is retained in full per-ID CSVs, and `raw_profile_cache_counter_tps`, where present, is an unvalidated raw-profile-counter rate. Neither is a logical-cache ratio, physical KV-load metric, or cache-load throughput.

### ID03 follow-up

- The resolved 07dd405 ID is analysed at request/source-key level in [11_id03_deep_dive.md](11_id03_deep_dive.md). Its c8/c12/c16 coverage and strict matching are deliberately kept separate from the all-ID aggregate tables above.
- **Evidence:** ID01 c8 has one ITL-valid request in the current public table; its weighted TPS is marked descriptive only and is suppressed from comparative TPS plots.


## Inference

- Prefixes are only used as canonical IDs after strict `startswith()` resolution is unique.

## Unknown

- A not-observed ID is not evidence that it was never eligible for replay; run duration, warmup, recycling, and routing affect coverage.
