# 01. Runtime architecture

## Evidence

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

- **Evidence:** `backend_hardware_and_pd_topology` = `{'gpu_type': 'H200', 'backend_gpu_count': 32, 'configured_gpu_count_in_resource_snapshot': 40, 'backend_workers': 4, 'prefill_workers': 2, 'decode_workers': 2, 'backend_gpus_per_worker': 8}` (server log).
- **Evidence:** `effective_prefill_server_flags` = `{'disaggregation_mode': 'prefill', 'transfer_backend': 'mooncake', 'tp_size': 8, 'attn_cp_size': 8, 'enable_prefill_cp': True, 'kv_cache_dtype': 'fp8_e4m3', 'context_length': 1048576, 'max_total_tokens': 1048576, 'max_running_requests': 32, 'speculative_algorithm': 'EAGLE', 'speculative_num_steps': 3, 'speculative_eagle_topk': 1, 'speculative_num_draft_tokens': 4}` (server log).
- **Evidence:** `effective_decode_server_flags_and_kv_residency_controls` = `{'disaggregation_mode': 'decode', 'transfer_backend': 'mooncake', 'tp_size': 8, 'dp_size': 8, 'enable_dp_attention': True, 'kv_cache_dtype': 'fp8_e4m3', 'page_size': 64, 'context_length': 1048576, 'max_total_tokens': 1048576, 'max_running_requests': 200, 'disable_radix_cache': True, 'enable_hisparse': False, 'cpu_offload_gb': 0, 'enable_lmcache': False, 'disaggregation_decode_enable_offload_kvcache': False, 'decode_cache_mode_logged': 'chunk cache'}` (server log).
- **Evidence:** `prefill_kv_runtime_allocation` = `{'dtype_recorded': 'torch.float8_e4m3fn', 'logical_token_limit': 1048576, 'scheduler_kv_blocks': 16384, 'page_size': 64, 'max_running_requests': 32, 'observed_primary_rank_allocation_gb': [6.93, 7.7], 'observed_secondary_rank_allocation_gb': 0.77, 'post_allocation_available_memory_gb_observed_range': [24.42, 26.44]}` (server log).
- **Evidence:** `decode_kv_runtime_allocation` = `{'dtype_recorded': 'torch.float8_e4m3fn', 'configured_max_total_tokens': 1048576, 'runtime_profiled_token_value': 218560, 'observed_primary_rank_allocation_gb': 12.51, 'observed_secondary_rank_allocation_gb': 0.16, 'post_allocation_available_memory_gb_observed_range': [18.98, 19.38]}` (server log).
- **Evidence:** `mtp_launch_and_runtime_behavior` = `{'algorithm': 'EAGLE', 'speculative_num_steps': 3, 'speculative_eagle_topk': 1, 'speculative_num_draft_tokens': 4, 'simulate_acceptance_length': '2.99', 'simulate_acceptance_method': 'match-expected', 'simulate_acceptance_token_mode': 'real-draft-token', 'runtime_decode_batch_sample_accept_length_range': [2.98, 3.0], 'runtime_decode_batch_sample_accept_rate_range': [0.66, 0.67]}` (server log).
- **Evidence:** `dynamic_worker_routing` = `{'router': 'Dynamo KV router', 'observable_fields': ['prefill worker ID', 'decode worker ID', 'decode dp_rank', 'effective cached blocks', 'host_pinned blocks', 'disk blocks'], 'routing_behavior': 'frontend logs select both prefill workers and both decode workers; decode selections span DP ranks'}` (server log).
- **Evidence:** `aiperf_cache_read_telemetry_availability` = `{'usage_prompt_tokens_details_cached_tokens_observed': False, 'aiperf_warning_present': True, 'enable_cache_report_in_server_args': True}` (server log).

## Inference

- The runtime logs resolve the prefill TP discrepancy in favor of TP=8 with attention-CP=8. The shared 32×H200 backend allocation is not a per-ID hardware assignment.

## Unknown

- The 40-GPU resource-snapshot count includes non-backend allocation; it is not the benchmark backend GPU total. Per-request GPU affinity is not exposed.
