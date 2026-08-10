# 분석 대상

- Public InferenceX run `31235207041`의 GLM-5.2 FP8 H200 replay를 분석했다. source Claude label은 workload provenance이며 target model이 아니다.

# H200 환경 검증

| field | value | classification | source |
| --- | --- | --- | --- |
| target_model | zai-org/GLM-5.2-FP8 | Evidence | at-run recipe |
| hardware | H200 | Evidence | at-run recipe and server logs |
| total_gpus | 32 backend H200 (2×8 prefill + 2×8 decode; 40 configured GPUs includes non-backend allocation) | Evidence | server logs/resource snapshot |
| serving | P/D disaggregated with Mooncake | Evidence | at-run recipe and server logs |
| kv_cache_dtype | fp8_e4m3 | Evidence | runtime decode ServerArgs |
| kv_offloading | none (CPU offload=0; decode KV offload=false; LMCache=false) | Evidence | runtime decode ServerArgs |
| hisparse | OFF (enable_hisparse=false) | Evidence | runtime decode ServerArgs |
| context_length | 1048576 | Evidence | at-run recipe and server logs |
| decode_page_size | 64 | Evidence | runtime decode ServerArgs |
| decode_max_running_requests | 200 | Evidence | at-run recipe |
| mtp | EAGLE steps=3 topk=1 draft_tokens=4 | Evidence | at-run recipe and server logs |
| simulated_acceptance | 2.99; match-expected; real-draft-token | Evidence | runtime server log |
| runtime_backend_gpu_count | 32 | Evidence | backend GPU count |
| runtime_prefill_workers | 2 | Evidence | server log |
| runtime_decode_workers | 2 | Evidence | server log |
| runtime_prefill_tp_size | 8 | Evidence | server log resolves matrix/recipe discrepancy |
| runtime_prefill_attn_cp_size | 8 | Evidence | server log |
| runtime_decode_kv_dtype | fp8_e4m3 | Evidence | server log |
| runtime_enable_hisparse | False | Evidence | server log |
| runtime_cpu_offload_gb | 0 | Evidence | server log |
| runtime_decode_kv_offload | False | Evidence | server log |

# 데이터와 ID 연결 방식

- **Evidence:** profile metadata의 `source_trace_id`와 `source_outer_idx`를 source table에 연결했다. prefix ID는 strict `startswith()` 후보가 하나일 때만 full ID로 확정했다.
- **Unknown:** conversation ID는 GPU affinity나 ID별 GPU 수를 뜻하지 않는다.

# ID coverage

| id_label | requested_value | requested_value_type | resolved_full_source_trace_id | resolution_match_count | resolution_status | candidate_full_ids | present_c8 | present_c12 | present_c16 | present_hisparse_c8 | notes | all_request_count_c8 | warmup_request_count_c8 | profiling_phase_count_c8 | successful_profile_request_count_c8 | error_count_c8 | cancellation_count_c8 | all_request_count_c12 | warmup_request_count_c12 | profiling_phase_count_c12 | successful_profile_request_count_c12 | error_count_c12 | cancellation_count_c12 | all_request_count_c16 | warmup_request_count_c16 | profiling_phase_count_c16 | successful_profile_request_count_c16 | error_count_c16 | cancellation_count_c16 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ID01 | 0196085d85d2075a50b74cd8795ffbdcea9a | full | 0196085d85d2075a50b74cd8795ffbdcea9a | 1 | unique | 0196085d85d2075a50b74cd8795ffbdcea9a | True | True | True | True | Evidence: full ID resolved by strict startswith() over source/H200 ID universe. | 69 | 11 | 58 | 58 | 0 | 0 | 56 | 11 | 45 | 45 | 0 | 0 | 49 | 11 | 38 | 38 | 0 | 0 |
| ID02 | 02bc0afb13f7a2d9efa86c28511261d85c0e | full | 02bc0afb13f7a2d9efa86c28511261d85c0e | 1 | unique | 02bc0afb13f7a2d9efa86c28511261d85c0e | False | False | False | True | Evidence: full ID resolved by strict startswith() over source/H200 ID universe. | 8 | 8 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 0 |
| ID03 | 07dd405 | prefix | 07dd40536557a1d6440a923557c3129dc929 | 1 | unique | 07dd40536557a1d6440a923557c3129dc929 | True | True | True | False | Evidence: full ID resolved by strict startswith() over source/H200 ID universe. | 119 | 0 | 119 | 119 | 0 | 0 | 119 | 7 | 112 | 112 | 0 | 0 | 26 | 13 | 13 | 13 | 0 | 0 |
| ID04 | 264478 | prefix | 264478eebbb2068593da2293ea8b67b31d4e | 1 | unique | 264478eebbb2068593da2293ea8b67b31d4e | False | False | False | False | Evidence: full ID resolved by strict startswith() over source/H200 ID universe. | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ID05 | debc7f6 | prefix | debc7f69e2c2fb94909ecdca600b0a4abd48 | 1 | unique | debc7f69e2c2fb94909ecdca600b0a4abd48 | False | False | False | False | Evidence: full ID resolved by strict startswith() over source/H200 ID universe. | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

# ID별 성능 핵심 결과

### ID01

| root_trace_id | concurrency | profiled_request_count | ttft_median_ms | ttft_p90_ms | weighted_decode_tps | wall_output_tps | output_tokens_total | error_count | cancellation_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0196085d85d2075a50b74cd8795ffbdcea9a | 8 | 58 | 9300.9 | 31640.6 | 93.4123 | 0.287196 | 941 | 0 | 0 |
| 0196085d85d2075a50b74cd8795ffbdcea9a | 12 | 45 | 29178.2 | 41582.9 |  | 0.0136758 | 45 | 0 | 0 |
| 0196085d85d2075a50b74cd8795ffbdcea9a | 16 | 38 | 32193.5 | 86996.6 |  | 0.0115979 | 38 | 0 | 0 |

### ID02

| root_trace_id | concurrency | profiled_request_count | ttft_median_ms | ttft_p90_ms | weighted_decode_tps | wall_output_tps | output_tokens_total | error_count | cancellation_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 02bc0afb13f7a2d9efa86c28511261d85c0e | 8 | 0 |  |  |  |  |  | 0 | 0 |
| 02bc0afb13f7a2d9efa86c28511261d85c0e | 12 | 0 |  |  |  |  |  | 0 | 0 |
| 02bc0afb13f7a2d9efa86c28511261d85c0e | 16 | 0 |  |  |  |  |  | 0 | 0 |

### ID03

| root_trace_id | concurrency | profiled_request_count | ttft_median_ms | ttft_p90_ms | weighted_decode_tps | wall_output_tps | output_tokens_total | error_count | cancellation_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 07dd40536557a1d6440a923557c3129dc929 | 8 | 119 | 1080.57 | 3326.14 | 90.4544 | 77.9692 | 37635 | 0 | 0 |
| 07dd40536557a1d6440a923557c3129dc929 | 12 | 112 | 1729.72 | 17659.2 | 88.3243 | 38.0921 | 31875 | 0 | 0 |
| 07dd40536557a1d6440a923557c3129dc929 | 16 | 13 | 1647.92 | 41057.6 | 87.6317 | 13.003 | 3925 | 0 | 0 |

### ID04

- **Unknown:** no public profiling rows or no unique resolution.


### ID05

- **Unknown:** no public profiling rows or no unique resolution.


- **Scope warning:** raw `usage_prompt_cache_read_tokens` is retained in full per-ID CSVs, but it is not a validated logical-cache ratio, physical KV-load metric, or `cache_load_tps` basis.

# Concurrency c8 / c12 / c16 비교

- 이 study의 public run은 c8/c12/c16이며, 고정 시간 replay이므로 coverage를 동반해 비교한다.
| concurrency | profiled_request_count | ttft_median_ms | weighted_decode_tps | wall_output_tps |
| --- | --- | --- | --- | --- |
| 8 | 957 | 1471.05 | 92.4771 | 210.505 |
| 12 | 1072 | 4337.19 | 91.2868 | 242.949 |
| 16 | 969 | 22688.7 | 91.6733 | 236.913 |

# Root agent와 subagent 비교

| concurrency | source_branch_type | profiled_request_count | root_id_count | input_sequence_length_total | output_tokens_total | ttft_median_ms | ttft_p90_ms | itl_weighted_ms | weighted_decode_tps | e2e_median_ms | wall_output_tps | scope |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | root | 518 | 14 | 4.56052e+07 | 497789 | 2194.89 | 20816.7 | 10.7587 | 92.9482 | 10146.4 | 137.752 | source branch origin joined through loader metadata; not replay suffix taxonomy |
| 8 | subagent | 439 | 7 | 3.35097e+07 | 262905 | 1195.63 | 10757.9 | 10.9173 | 91.5975 | 5590.29 | 82.1089 | source branch origin joined through loader metadata; not replay suffix taxonomy |
| 12 | root | 623 | 19 | 5.84804e+07 | 624173 | 7637.54 | 42368 | 10.9045 | 91.705 | 17099.4 | 173.208 | source branch origin joined through loader metadata; not replay suffix taxonomy |
| 12 | subagent | 449 | 7 | 3.49706e+07 | 251322 | 1976.78 | 30964 | 11.0786 | 90.2638 | 6409.4 | 76.7299 | source branch origin joined through loader metadata; not replay suffix taxonomy |
| 16 | root | 640 | 24 | 6.13655e+07 | 654980 | 24643.3 | 88062 | 10.8961 | 91.776 | 33776.2 | 180.516 | source branch origin joined through loader metadata; not replay suffix taxonomy |
| 16 | subagent | 329 | 8 | 2.59004e+07 | 204631 | 16451.6 | 82170.9 | 10.9474 | 91.3457 | 22800.1 | 57.4769 | source branch origin joined through loader metadata; not replay suffix taxonomy |

# Context 및 theoretical cache reuse 영향

- **Evidence:** profile cache counter와 aggregate frontend-cache metrics는 별도 scope로 보존했다.
- **Unknown:** theoretical source prefix reuse는 actual H200 cache residency/hit와 동일하지 않다.

| concurrency | relationship | sample_count | spearman_rho | interpretation |
| --- | --- | --- | --- | --- |
| 8 | source_input_tokens_vs_ttft_ms | 957 | 0.435952 | source workload input token count; may differ from AIPerf input sequence length |
| 8 | theoretical_new_tokens_vs_ttft_ms | 932 | 0.116459 | source-workload theoretical cache shape; not actual H200 cache residency |
| 8 | theoretical_cache_ratio_vs_ttft_ms | 932 | 0.123554 | source-workload theoretical cache shape; not actual H200 cache residency |
| 12 | source_input_tokens_vs_ttft_ms | 1072 | 0.249121 | source workload input token count; may differ from AIPerf input sequence length |
| 12 | theoretical_new_tokens_vs_ttft_ms | 1050 | 0.0277677 | source-workload theoretical cache shape; not actual H200 cache residency |
| 12 | theoretical_cache_ratio_vs_ttft_ms | 1050 | 0.0995059 | source-workload theoretical cache shape; not actual H200 cache residency |
| 16 | source_input_tokens_vs_ttft_ms | 969 | 0.179308 | source workload input token count; may differ from AIPerf input sequence length |
| 16 | theoretical_new_tokens_vs_ttft_ms | 947 | -0.00418548 | source-workload theoretical cache shape; not actual H200 cache residency |
| 16 | theoretical_cache_ratio_vs_ttft_ms | 947 | 0.10071 | source-workload theoretical cache shape; not actual H200 cache residency |

# 가장 부담이 큰 trace IDs

| concurrency | root_trace_id | profiled_request_count | input_sequence_length_total | output_tokens_total | ttft_median_ms |
| --- | --- | --- | --- | --- | --- |
| 8 | 0470d446a4514dfe0c6ad0be92853bd13287 | 173 | 1.83611e+07 | 77132 | 1201.45 |
| 8 | 069d7bf5f1efb4e76e3c84510367e6af78a5 | 162 | 1.31653e+07 | 195870 | 1358.82 |
| 8 | 085411a4cc4b15108dd9b50007261a2efb65 | 92 | 1.01632e+07 | 100152 | 1943.18 |
| 8 | 07dd40536557a1d6440a923557c3129dc929 | 119 | 9.91528e+06 | 37635 | 1080.57 |
| 8 | 085aacf44ac5428ad3c6b4f6cd431e083832 | 59 | 7.47745e+06 | 88917 | 4255.43 |
| 8 | 063179eb93f4337a662e859c5a2c5638e03f | 71 | 4.50626e+06 | 35251 | 1021.18 |
| 8 | 05f72f78a037cfa5cd4e4541960a574701d9 | 47 | 4.2557e+06 | 42388 | 1112.51 |
| 8 | 05c249572509162371b7b82339674db64b5d | 30 | 3.55942e+06 | 59305 | 1341.76 |
| 8 | 077ea9e6554f45bbad9c24a8462bae9a8512 | 31 | 2.33442e+06 | 48194 | 1213.49 |
| 8 | 03e110ac6921c2fe9ac7772a9654314a2beb | 52 | 2.2921e+06 | 39500 | 1318.28 |
| 8 | 006c98de37d819e95b0840e25426bb7ca99d | 18 | 1.93356e+06 | 17679 | 5012.98 |
| 8 | 0a279af1bec84c6ab033bb03f5d8bfd6b08d | 11 | 1.0317e+06 | 17696 | 3251.44 |
| 8 | 0196085d85d2075a50b74cd8795ffbdcea9a | 58 | 119423 | 941 | 9300.9 |
| 8 | 002001296e8a8c38ad9d7cc436d691afc602 | 34 | 34 | 34 | 11559.3 |
| 12 | 0470d446a4514dfe0c6ad0be92853bd13287 | 168 | 1.77754e+07 | 75905 | 1621.67 |
| 12 | 0b7f3ca692f15ae2651a310d9411d70794aa | 96 | 1.17532e+07 | 68206 | 4213.53 |
| 12 | 085aacf44ac5428ad3c6b4f6cd431e083832 | 148 | 1.10822e+07 | 128456 | 2121.57 |
| 12 | 085411a4cc4b15108dd9b50007261a2efb65 | 96 | 1.10587e+07 | 114259 | 5729.53 |
| 12 | 07dd40536557a1d6440a923557c3129dc929 | 112 | 9.54724e+06 | 31875 | 1729.72 |
| 12 | 0bc9c4f798d321286bf39f2543c0c4e4c059 | 95 | 8.89062e+06 | 108781 | 3137.38 |

# Aggregate 결과 재현 검증

| concurrency | validation_status | metric_count |
| --- | --- | --- |
| 8 | pass | 30 |
| 12 | pass | 30 |
| 16 | pass | 30 |

# 확인된 사실

- **Evidence:** raw profile rows와 published aggregate의 request count, tokens, TTFT, ITL, E2E, throughput은 validation table 범위에서 대조된다.

# 추론

- **Inference (high confidence):** runtime log는 FP8 KV allocation record와 HiSparse/OFFload 비활성화를 직접 보인다. 다만 rank-scoped GiB를 cluster 전체 physical capacity로 합산하지 않는다.

# 확인할 수 없는 것

- **Unknown:** HiSparse 단독 효과, ID별 GPU attribution, 사내 2-GPU의 request-level behavior, and unsupported cache/MTP counter semantics.

# 데이터 한계

- warmup/recycling, shared system, repeated source IDs, MTP output variance, and cache metric scope prevent naïve request-independence or apples-to-apples conclusions.

# 재현 방법

```sh
make mtp-analyze
make mtp-report
```

# 기존 HiSparse c8와의 observed difference

| comparison_scope | metric | hisparse_c8_value | gpu_resident_mtp_c8_value | gpu_resident_over_hisparse_ratio | sample_count | caveat |
| --- | --- | --- | --- | --- | --- | --- |
| run_level_unpaired_observed_system_difference | ttft_median_ms | 228708 | 1471.05 | 0.00643201 | 219 | 16→32 GPUs, 1P1D→2P2D, KV mode/dtype, MTP, and software may differ; not a causal HiSparse estimate. |
| run_level_unpaired_observed_system_difference | weighted_decode_tps | 32.5161 | 92.4771 | 2.84404 | 219 | 16→32 GPUs, 1P1D→2P2D, KV mode/dtype, MTP, and software may differ; not a causal HiSparse estimate. |
| run_level_unpaired_observed_system_difference | wall_output_tps | 23.5666 | 210.505 | 8.93234 | 219 | 16→32 GPUs, 1P1D→2P2D, KV mode/dtype, MTP, and software may differ; not a causal HiSparse estimate. |
| run_level_unpaired_observed_system_difference | output_tokens_total | 84618 | 760694 | 8.98974 | 219 | 16→32 GPUs, 1P1D→2P2D, KV mode/dtype, MTP, and software may differ; not a causal HiSparse estimate. |
| source_key_matched_median_observed_system_ratio | ttft_ratio_gpu_resident_over_hisparse |  | 0.00880767 | 0.00880767 | 83 | Source-key matching controls workload identity only; it does not isolate a single architecture change. |
| source_key_matched_median_observed_system_ratio | itl_ratio_gpu_resident_over_hisparse |  | 0.353382 | 0.353382 | 64 | Source-key matching controls workload identity only; it does not isolate a single architecture change. |
| source_key_matched_median_observed_system_ratio | e2e_ratio_gpu_resident_over_hisparse |  | 0.0482293 | 0.0482293 | 83 | Source-key matching controls workload identity only; it does not isolate a single architecture change. |
