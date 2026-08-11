# Codex → ChatGPT handoff: H200 GPU-resident MTP

## Git / Run Provenance

- Analysis repository: `https://github.com/sskim-ai/InferenceX_analysis`
- Analysis branch: `analysis/h200-gpu-resident-mtp`
- Analysis starting commit: `5411307f0be9e481a37a80d5ee477faf81c16c8c`
- InferenceX Actions run: `31235207041`
- Canonical run SHA: `48ec5aa103dbf8e671580cd191eeef7e7186c802`
- PR: `#2529`

## Downloaded Artifacts

| concurrency | category | artifact_id | artifact_name | github_digest | download_status | zip_validation | expired |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | aggregate | 9017975161 | bmk_agentic_glm5.2_p2x1_d2x8_conc8_fp8_dynamo-sglang_prefill-tp1-pp1-dcp1-pcp8-ep1-dpfalse-nw2_decode-tp8-pp1-dcp1-pcp1-ep1-dptrue-nw2_disagg-true_spec-mtp_conc8_h200-dgxc-slurm_7 | sha256:081ea77a9ed524f9acb794b5d4f4d92bf2ef7e2cf17d93ccdf2980a503655cf8 | downloaded_and_verified | github_digest_match_and_zip_crc_pass | False |
| 8 | raw_result | 9017979109 | agentic_glm5.2_p2x1_d2x8_conc8_fp8_dynamo-sglang_prefill-tp1-pp1-dcp1-pcp8-ep1-dpfalse-nw2_decode-tp8-pp1-dcp1-pcp1-ep1-dptrue-nw2_disagg-true_spec-mtp_conc8_h200-dgxc-slurm_7 | sha256:fbcb6b7763a8cec8be37bc13e3e305c8f667286ac7229fad41f4b6802ed44f8b | downloaded_and_verified | github_digest_match_and_zip_crc_pass | False |
| 8 | server_logs | 9017974866 | multinode_server_logs_glm5.2_p2x1_d2x8_conc8_fp8_dynamo-sglang_prefill-tp1-pp1-dcp1-pcp8-ep1-dpfalse-nw2_decode-tp8-pp1-dcp1-pcp1-ep1-dptrue-nw2_disagg-true_spec-mtp_conc8_h200-dgxc-slurm_7 | sha256:a0f8ce452f6f082b5a15604a034b50cfdeaf60132c4d36d6e0ff15c0570147da | downloaded_and_verified | github_digest_match_and_zip_crc_pass | False |
| 12 | aggregate | 9019205268 | bmk_agentic_glm5.2_p2x1_d2x8_conc12_fp8_dynamo-sglang_prefill-tp1-pp1-dcp1-pcp8-ep1-dpfalse-nw2_decode-tp8-pp1-dcp1-pcp1-ep1-dptrue-nw2_disagg-true_spec-mtp_conc12_h200-dgxc-slurm_6 | sha256:063689cc6bd0297cad573046f1427fbc4ffcb08179e013abef2c5cd083b39269 | downloaded_and_verified | github_digest_match_and_zip_crc_pass | False |
| 12 | raw_result | 9019209525 | agentic_glm5.2_p2x1_d2x8_conc12_fp8_dynamo-sglang_prefill-tp1-pp1-dcp1-pcp8-ep1-dpfalse-nw2_decode-tp8-pp1-dcp1-pcp1-ep1-dptrue-nw2_disagg-true_spec-mtp_conc12_h200-dgxc-slurm_6 | sha256:30c60b1d0abb044aa1707f2b12e15a4b17d3e743007f7a7296798e606cfd59cf | downloaded_and_verified | github_digest_match_and_zip_crc_pass | False |
| 12 | server_logs | 9019204997 | multinode_server_logs_glm5.2_p2x1_d2x8_conc12_fp8_dynamo-sglang_prefill-tp1-pp1-dcp1-pcp8-ep1-dpfalse-nw2_decode-tp8-pp1-dcp1-pcp1-ep1-dptrue-nw2_disagg-true_spec-mtp_conc12_h200-dgxc-slurm_6 | sha256:2b42bf400bc980613de2276258b82ab8c412deb0e31a4267b176c7d1397ff78d | downloaded_and_verified | github_digest_match_and_zip_crc_pass | False |
| 16 | aggregate | 9020480067 | bmk_agentic_glm5.2_p2x1_d2x8_conc16_fp8_dynamo-sglang_prefill-tp1-pp1-dcp1-pcp8-ep1-dpfalse-nw2_decode-tp8-pp1-dcp1-pcp1-ep1-dptrue-nw2_disagg-true_spec-mtp_conc16_h200-dgxc-slurm_11 | sha256:09d6fa6d20d50efcb7fe3ad3663d1b1cafe57e028562a3809f019e6c47878f30 | downloaded_and_verified | github_digest_match_and_zip_crc_pass | False |
| 16 | raw_result | 9020484364 | agentic_glm5.2_p2x1_d2x8_conc16_fp8_dynamo-sglang_prefill-tp1-pp1-dcp1-pcp8-ep1-dpfalse-nw2_decode-tp8-pp1-dcp1-pcp1-ep1-dptrue-nw2_disagg-true_spec-mtp_conc16_h200-dgxc-slurm_11 | sha256:6068553b427c0f196aeae5401e685779286aad692854549d383f1fd794ccc23f | downloaded_and_verified | github_digest_match_and_zip_crc_pass | False |
| 16 | server_logs | 9020479786 | multinode_server_logs_glm5.2_p2x1_d2x8_conc16_fp8_dynamo-sglang_prefill-tp1-pp1-dcp1-pcp8-ep1-dpfalse-nw2_decode-tp8-pp1-dcp1-pcp1-ep1-dptrue-nw2_disagg-true_spec-mtp_conc16_h200-dgxc-slurm_11 | sha256:363cecd0eef29d48152e6df275fc9379ab1d8124d6f205347a50ba88cc3f9cef | downloaded_and_verified | github_digest_match_and_zip_crc_pass | False |

- **Evidence:** each selected archive has `expired=false`, local SHA-256 matching the GitHub digest, and a passing ZIP CRC check. Full local paths/checksums are in `../manifests/artifact_inventory.csv`.

## Confirmed Architecture

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

## Runtime KV Findings

| component | observed allocation | scope | classification |
| --- | --- | --- | --- |
| prefill runtime | logical token limit 1,048,576; scheduler 16,384 blocks × page 64; 6.93–7.70 GiB primary + 0.77 GiB secondary allocation records | individual logged ATTN_CP/TP rank in one 8-GPU prefill worker; logical pool is per worker, not a 16-GPU/global total | Evidence |
| decode runtime | runtime-profiled token value 218,560; 12.51 GiB primary + 0.16 GiB secondary allocation records; page 64 / FP8 E4M3 | individual logged DP/TP rank in one decode worker; do not sum or multiply into cluster physical capacity | Evidence |

| concurrency | component | field | value | scope | classification | source |
| --- | --- | --- | --- | --- | --- | --- |
| configured | configured_decode | kv_cache_dtype | fp8_e4m3 | configured recipe | Evidence |  |
| configured | configured_decode | kv_offloading | none | configured matrix | Evidence |  |
| configured | configured_decode | page_size | 64 | configured recipe | Evidence |  |
| configured | configured_decode | max_running_requests | 200 | configured recipe | Evidence |  |
| 12;16;8 | backend_hardware_and_pd_topology | gpu_type | H200 | Each sweep log reports 32 backend GPUs and 40 configured GPUs on five nodes, then starts four worker processes and waits for 2 prefills plus 2 decodes. The c8 resource snapshot separately assigns 8 backend GPUs to each of four backend nodes. | Evidence | c8:sweep_67841.log:111-117, 130-146, 173-175; c12:sweep_67842.log:111-117, 130-146, 173-175; c16:sweep_67843.log:112-118, 131-147, 174-176 |
| 12;16;8 | backend_hardware_and_pd_topology | backend_gpu_count | 32 | Each sweep log reports 32 backend GPUs and 40 configured GPUs on five nodes, then starts four worker processes and waits for 2 prefills plus 2 decodes. The c8 resource snapshot separately assigns 8 backend GPUs to each of four backend nodes. | Evidence | c8:sweep_67841.log:111-117, 130-146, 173-175; c12:sweep_67842.log:111-117, 130-146, 173-175; c16:sweep_67843.log:112-118, 131-147, 174-176 |
| 12;16;8 | backend_hardware_and_pd_topology | configured_gpu_count_in_resource_snapshot | 40 | Each sweep log reports 32 backend GPUs and 40 configured GPUs on five nodes, then starts four worker processes and waits for 2 prefills plus 2 decodes. The c8 resource snapshot separately assigns 8 backend GPUs to each of four backend nodes. | Evidence | c8:sweep_67841.log:111-117, 130-146, 173-175; c12:sweep_67842.log:111-117, 130-146, 173-175; c16:sweep_67843.log:112-118, 131-147, 174-176 |
| 12;16;8 | backend_hardware_and_pd_topology | backend_workers | 4 | Each sweep log reports 32 backend GPUs and 40 configured GPUs on five nodes, then starts four worker processes and waits for 2 prefills plus 2 decodes. The c8 resource snapshot separately assigns 8 backend GPUs to each of four backend nodes. | Evidence | c8:sweep_67841.log:111-117, 130-146, 173-175; c12:sweep_67842.log:111-117, 130-146, 173-175; c16:sweep_67843.log:112-118, 131-147, 174-176 |
| 12;16;8 | backend_hardware_and_pd_topology | prefill_workers | 2 | Each sweep log reports 32 backend GPUs and 40 configured GPUs on five nodes, then starts four worker processes and waits for 2 prefills plus 2 decodes. The c8 resource snapshot separately assigns 8 backend GPUs to each of four backend nodes. | Evidence | c8:sweep_67841.log:111-117, 130-146, 173-175; c12:sweep_67842.log:111-117, 130-146, 173-175; c16:sweep_67843.log:112-118, 131-147, 174-176 |
| 12;16;8 | backend_hardware_and_pd_topology | decode_workers | 2 | Each sweep log reports 32 backend GPUs and 40 configured GPUs on five nodes, then starts four worker processes and waits for 2 prefills plus 2 decodes. The c8 resource snapshot separately assigns 8 backend GPUs to each of four backend nodes. | Evidence | c8:sweep_67841.log:111-117, 130-146, 173-175; c12:sweep_67842.log:111-117, 130-146, 173-175; c16:sweep_67843.log:112-118, 131-147, 174-176 |
| 12;16;8 | backend_hardware_and_pd_topology | backend_gpus_per_worker | 8 | Each sweep log reports 32 backend GPUs and 40 configured GPUs on five nodes, then starts four worker processes and waits for 2 prefills plus 2 decodes. The c8 resource snapshot separately assigns 8 backend GPUs to each of four backend nodes. | Evidence | c8:sweep_67841.log:111-117, 130-146, 173-175; c12:sweep_67842.log:111-117, 130-146, 173-175; c16:sweep_67843.log:112-118, 131-147, 174-176 |
| 12;16;8;all | effective_prefill_server_flags | disaggregation_mode | prefill | The actual launcher command and resulting ServerArgs agree for the named flags on both prefill workers in every concurrency. | Evidence | c8:sweep_67841.log:130-136; c12:sweep_67842.log:130-136; c16:sweep_67843.log:131-137 |
| 12;16;8;all | effective_prefill_server_flags | transfer_backend | mooncake | The actual launcher command and resulting ServerArgs agree for the named flags on both prefill workers in every concurrency. | Evidence | c8:sweep_67841.log:130-136; c12:sweep_67842.log:130-136; c16:sweep_67843.log:131-137 |
| 12;16;8;all | effective_prefill_server_flags | tp_size | 8 | The actual launcher command and resulting ServerArgs agree for the named flags on both prefill workers in every concurrency. | Evidence | c8:sweep_67841.log:130-136; c12:sweep_67842.log:130-136; c16:sweep_67843.log:131-137 |
| 12;16;8;all | effective_prefill_server_flags | attn_cp_size | 8 | The actual launcher command and resulting ServerArgs agree for the named flags on both prefill workers in every concurrency. | Evidence | c8:sweep_67841.log:130-136; c12:sweep_67842.log:130-136; c16:sweep_67843.log:131-137 |
| 12;16;8;all | effective_prefill_server_flags | enable_prefill_cp | True | The actual launcher command and resulting ServerArgs agree for the named flags on both prefill workers in every concurrency. | Evidence | c8:sweep_67841.log:130-136; c12:sweep_67842.log:130-136; c16:sweep_67843.log:131-137 |
| 12;16;8;all | effective_prefill_server_flags | kv_cache_dtype | fp8_e4m3 | The actual launcher command and resulting ServerArgs agree for the named flags on both prefill workers in every concurrency. | Evidence | c8:sweep_67841.log:130-136; c12:sweep_67842.log:130-136; c16:sweep_67843.log:131-137 |
| 12;16;8;all | effective_prefill_server_flags | context_length | 1048576 | The actual launcher command and resulting ServerArgs agree for the named flags on both prefill workers in every concurrency. | Evidence | c8:sweep_67841.log:130-136; c12:sweep_67842.log:130-136; c16:sweep_67843.log:131-137 |
| 12;16;8;all | effective_prefill_server_flags | max_total_tokens | 1048576 | The actual launcher command and resulting ServerArgs agree for the named flags on both prefill workers in every concurrency. | Evidence | c8:sweep_67841.log:130-136; c12:sweep_67842.log:130-136; c16:sweep_67843.log:131-137 |
| 12;16;8;all | effective_prefill_server_flags | max_running_requests | 32 | The actual launcher command and resulting ServerArgs agree for the named flags on both prefill workers in every concurrency. | Evidence | c8:sweep_67841.log:130-136; c12:sweep_67842.log:130-136; c16:sweep_67843.log:131-137 |
| 12;16;8;all | effective_prefill_server_flags | speculative_algorithm | EAGLE | The actual launcher command and resulting ServerArgs agree for the named flags on both prefill workers in every concurrency. | Evidence | c8:sweep_67841.log:130-136; c12:sweep_67842.log:130-136; c16:sweep_67843.log:131-137 |
| 12;16;8;all | effective_prefill_server_flags | speculative_num_steps | 3 | The actual launcher command and resulting ServerArgs agree for the named flags on both prefill workers in every concurrency. | Evidence | c8:sweep_67841.log:130-136; c12:sweep_67842.log:130-136; c16:sweep_67843.log:131-137 |
| 12;16;8;all | effective_prefill_server_flags | speculative_eagle_topk | 1 | The actual launcher command and resulting ServerArgs agree for the named flags on both prefill workers in every concurrency. | Evidence | c8:sweep_67841.log:130-136; c12:sweep_67842.log:130-136; c16:sweep_67843.log:131-137 |
| 12;16;8;all | effective_prefill_server_flags | speculative_num_draft_tokens | 4 | The actual launcher command and resulting ServerArgs agree for the named flags on both prefill workers in every concurrency. | Evidence | c8:sweep_67841.log:130-136; c12:sweep_67842.log:130-136; c16:sweep_67843.log:131-137 |
| 12;16;8;all | effective_decode_server_flags_and_kv_residency_controls | disaggregation_mode | decode | The startup logs are direct runtime evidence that HiSparse is disabled and that the configured CPU/offload and LMCache paths are disabled. They also record that the decode server forces the KV cache to chunk-cache mode. | Evidence | c8:sweep_67841.log:138-145; c12:sweep_67842.log:138-145; c16:sweep_67843.log:139-146 |
| 12;16;8;all | effective_decode_server_flags_and_kv_residency_controls | transfer_backend | mooncake | The startup logs are direct runtime evidence that HiSparse is disabled and that the configured CPU/offload and LMCache paths are disabled. They also record that the decode server forces the KV cache to chunk-cache mode. | Evidence | c8:sweep_67841.log:138-145; c12:sweep_67842.log:138-145; c16:sweep_67843.log:139-146 |
| 12;16;8;all | effective_decode_server_flags_and_kv_residency_controls | tp_size | 8 | The startup logs are direct runtime evidence that HiSparse is disabled and that the configured CPU/offload and LMCache paths are disabled. They also record that the decode server forces the KV cache to chunk-cache mode. | Evidence | c8:sweep_67841.log:138-145; c12:sweep_67842.log:138-145; c16:sweep_67843.log:139-146 |
| 12;16;8;all | effective_decode_server_flags_and_kv_residency_controls | dp_size | 8 | The startup logs are direct runtime evidence that HiSparse is disabled and that the configured CPU/offload and LMCache paths are disabled. They also record that the decode server forces the KV cache to chunk-cache mode. | Evidence | c8:sweep_67841.log:138-145; c12:sweep_67842.log:138-145; c16:sweep_67843.log:139-146 |
| 12;16;8;all | effective_decode_server_flags_and_kv_residency_controls | enable_dp_attention | True | The startup logs are direct runtime evidence that HiSparse is disabled and that the configured CPU/offload and LMCache paths are disabled. They also record that the decode server forces the KV cache to chunk-cache mode. | Evidence | c8:sweep_67841.log:138-145; c12:sweep_67842.log:138-145; c16:sweep_67843.log:139-146 |
| 12;16;8;all | effective_decode_server_flags_and_kv_residency_controls | kv_cache_dtype | fp8_e4m3 | The startup logs are direct runtime evidence that HiSparse is disabled and that the configured CPU/offload and LMCache paths are disabled. They also record that the decode server forces the KV cache to chunk-cache mode. | Evidence | c8:sweep_67841.log:138-145; c12:sweep_67842.log:138-145; c16:sweep_67843.log:139-146 |

- Table is truncated to 30 rows.

## MTP Findings

| concurrency | configured_algorithm | configured_simulated_acceptance_length | configured_draft_tokens | mtp_draft_tokens_total | mtp_accepted_tokens_total | mtp_acceptance_rate_mean | mtp_acceptance_length_mean | request_metric_status | tps_interpretation | evidence_classification | runtime_sample_acceptance_length_range | runtime_sample_acceptance_rate_range | runtime_configured_simulated_acceptance_length | runtime_configured_acceptance_method | runtime_configured_acceptance_token_mode | runtime_log_status | runtime_evidence_classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | EAGLE | 2.99 | 4 |  |  |  |  | not_exported_in_profile_rows | weighted decode TPS includes configured MTP behavior; it is not non-MTP hardware TPS | Unknown | [2.98, 3.0] | [0.66, 0.67] | 2.99 | match-expected | real-draft-token | sampled_decode_batch_evidence_not_request_weighted | Evidence |
| 12 | EAGLE | 2.99 | 4 |  |  |  |  | not_exported_in_profile_rows | weighted decode TPS includes configured MTP behavior; it is not non-MTP hardware TPS | Unknown | [2.98, 3.0] | [0.66, 0.67] | 2.99 | match-expected | real-draft-token | sampled_decode_batch_evidence_not_request_weighted | Evidence |
| 16 | EAGLE | 2.99 | 4 |  |  |  |  | not_exported_in_profile_rows | weighted decode TPS includes configured MTP behavior; it is not non-MTP hardware TPS | Unknown | [2.98, 3.0] | [0.66, 0.67] | 2.99 | match-expected | real-draft-token | sampled_decode_batch_evidence_not_request_weighted | Evidence |

## Routing / Worker Distribution

- **Evidence:** frontend logs select both prefill workers and both decode workers across decode DP ranks.
- **Unknown:** profile `worker_id` is an observed request field, not proof of a fixed backend worker or GPU affinity. See `../processed/worker_distribution.csv`.


## c8/c12/c16 Key Metrics

| concurrency | profiled_request_count | ttft_mean_ms | ttft_median_ms | ttft_p90_ms | itl_weighted_ms | weighted_decode_tps | wall_output_tps | output_tokens_total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | 957 | 6399.09 | 1471.05 | 18344.2 | 10.8135 | 92.4771 | 210.505 | 760694 |
| 12 | 1072 | 14039.5 | 4337.19 | 37845.8 | 10.9545 | 91.2868 | 242.949 | 875495 |
| 16 | 969 | 34544.1 | 22688.7 | 86235.6 | 10.9083 | 91.6733 | 236.913 | 859611 |

## Requested ID Resolution

| id_label | requested_value | requested_value_type | resolved_full_source_trace_id | resolution_match_count | resolution_status | candidate_full_ids | present_c8 | present_c12 | present_c16 | present_hisparse_c8 | notes | all_request_count_c8 | warmup_request_count_c8 | profiling_phase_count_c8 | successful_profile_request_count_c8 | error_count_c8 | cancellation_count_c8 | all_request_count_c12 | warmup_request_count_c12 | profiling_phase_count_c12 | successful_profile_request_count_c12 | error_count_c12 | cancellation_count_c12 | all_request_count_c16 | warmup_request_count_c16 | profiling_phase_count_c16 | successful_profile_request_count_c16 | error_count_c16 | cancellation_count_c16 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ID01 | 0196085d85d2075a50b74cd8795ffbdcea9a | full | 0196085d85d2075a50b74cd8795ffbdcea9a | 1 | unique | 0196085d85d2075a50b74cd8795ffbdcea9a | True | True | True | True | Evidence: full ID resolved by strict startswith() over source/H200 ID universe. | 69 | 11 | 58 | 58 | 0 | 0 | 56 | 11 | 45 | 45 | 0 | 0 | 49 | 11 | 38 | 38 | 0 | 0 |
| ID02 | 02bc0afb13f7a2d9efa86c28511261d85c0e | full | 02bc0afb13f7a2d9efa86c28511261d85c0e | 1 | unique | 02bc0afb13f7a2d9efa86c28511261d85c0e | False | False | False | True | Evidence: full ID resolved by strict startswith() over source/H200 ID universe. | 8 | 8 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 0 |
| ID03 | 07dd405 | prefix | 07dd40536557a1d6440a923557c3129dc929 | 1 | unique | 07dd40536557a1d6440a923557c3129dc929 | True | True | True | False | Evidence: full ID resolved by strict startswith() over source/H200 ID universe. | 119 | 0 | 119 | 119 | 0 | 0 | 119 | 7 | 112 | 112 | 0 | 0 | 26 | 13 | 13 | 13 | 0 | 0 |
| ID04 | 264478 | prefix | 264478eebbb2068593da2293ea8b67b31d4e | 1 | unique | 264478eebbb2068593da2293ea8b67b31d4e | False | False | False | False | Evidence: full ID resolved by strict startswith() over source/H200 ID universe. | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ID05 | debc7f6 | prefix | debc7f69e2c2fb94909ecdca600b0a4abd48 | 1 | unique | debc7f69e2c2fb94909ecdca600b0a4abd48 | False | False | False | False | Evidence: full ID resolved by strict startswith() over source/H200 ID universe. | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## ID01 Key Metrics

| root_trace_id | concurrency | all_request_count | warmup_count | profiled_request_count | output_tokens_total | ttft_mean_ms | ttft_median_ms | ttft_p90_ms | itl_sample_count | weighted_decode_tps | e2e_median_ms | wall_span_s | wall_output_tps | error_count | cancellation_count | sample_quality | decode_tps_comparison_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0196085d85d2075a50b74cd8795ffbdcea9a | 8 | 69 | 11 | 58 | 941 | 13250.4 | 9300.9 | 31640.6 | 1 | 93.4123 | 9649.18 | 3276.51 | 0.287196 | 0 | 0 | observed | suppressed_n_lt_3_descriptive_only |
| 0196085d85d2075a50b74cd8795ffbdcea9a | 12 | 56 | 11 | 45 | 45 | 29698.6 | 29178.2 | 41582.9 | 0 |  | 29178.2 | 3290.48 | 0.0136758 | 0 | 0 | observed | suppressed_n_lt_3_descriptive_only |
| 0196085d85d2075a50b74cd8795ffbdcea9a | 16 | 49 | 11 | 38 | 38 | 44346.4 | 32193.5 | 86996.6 | 0 |  | 32193.5 | 3276.45 | 0.0115979 | 0 | 0 | observed | suppressed_n_lt_3_descriptive_only |

- **Evidence:** ID01 c8 has one ITL-valid request. Its weighted decode TPS is descriptive only (n=1) and is excluded from the default comparative TPS figure.


## ID02 Key Metrics

| root_trace_id | concurrency | all_request_count | warmup_count | profiled_request_count | output_tokens_total | ttft_mean_ms | ttft_median_ms | ttft_p90_ms | itl_sample_count | weighted_decode_tps | e2e_median_ms | wall_span_s | wall_output_tps | error_count | cancellation_count | sample_quality | decode_tps_comparison_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 02bc0afb13f7a2d9efa86c28511261d85c0e | 8 | 8 | 8 | 0 |  |  |  |  | 0 |  |  |  |  | 0 | 0 | sparse | suppressed_n_lt_3_descriptive_only |
| 02bc0afb13f7a2d9efa86c28511261d85c0e | 12 | 8 | 8 | 0 |  |  |  |  | 0 |  |  |  |  | 0 | 0 | sparse | suppressed_n_lt_3_descriptive_only |
| 02bc0afb13f7a2d9efa86c28511261d85c0e | 16 | 8 | 8 | 0 |  |  |  |  | 0 |  |  |  |  | 0 | 0 | sparse | suppressed_n_lt_3_descriptive_only |

## ID03 Deep Dive

### Evidence

- Canonical ID: 07dd40536557a1d6440a923557c3129dc929.
### Public c8/c12/c16 coverage

| concurrency | profiling_phase_count | successful_profiling_count | distinct_exact_source_key_count_profile | source_coverage_ratio_profile | warmup_count |
| --- | --- | --- | --- | --- | --- |
| 8 | 119 | 119 | 119 | 1 | 0 |
| 12 | 112 | 112 | 112 | 0.941176 | 7 |
| 16 | 13 | 13 | 13 | 0.109244 | 13 |

### TTFT / TPS scaling

| concurrency | ttft_median_ms | ttft_p90_ms | weighted_decode_tps | itl_sample_count | ttft_inflation_vs_c8 | tps_retention_vs_c8 | wall_throughput_ratio_vs_c8 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | 1080.57 | 3326.14 | 90.4544 | 119 | 1 | 1 | 1 |
| 12 | 1729.72 | 17659.2 | 88.3243 | 112 | 1.60075 | 0.976452 | 0.488553 |
| 16 | 1647.92 | 41057.6 | 87.6317 | 13 | 1.52505 | 0.968795 | 0.166771 |

### Exact overlap

| pair | matched_source_key_count | same_output_length_count | strict_ttft_count | strict_decode_count | median_ttft_ratio_right_over_left | weighted_itl_ratio_right_over_left | coverage_overlap_ratio_jaccard |
| --- | --- | --- | --- | --- | --- | --- | --- |
| c8_c12 | 112 | 112 | 112 | 112 | 1.45117 | 1.01475 | 0.941176 |
| c8_c16 | 13 | 13 | 13 | 13 | 1.28084 | 1.041 | 0.109244 |
| c12_c16 | 13 | 13 | 13 | 13 | 0.32583 | 1.0058 | 0.116071 |

### Context/token metric limitation

| context_202752_subset_status | reason | logical_prompt_metric_observed_row_count | forbidden_proxies | required_future_evidence |
| --- | --- | --- | --- | --- |
| unavailable_exact_target_tokenization | no_request_level_target_model_logical_prompt_metric_in_public_profile_or_join | 0 | input_sequence_length; source_input_tokens | exact target logical prompt tokens + requested output limit + documented loader/server fit rule |

- Raw AIPerf log scheduling evidence is in processed/id03_replay_scheduling_evidence.csv; it documents time-limited profiling, randomized starts, warmup handoff, and recycling without claiming a single causal mechanism.
### Inference

- c8 is the primary public reference because it has full observed ID03 source-key profiling coverage and enough ITL-valid requests for a reviewable decode-TPS distribution; c12/c16 retain narrower matched subsets.

### Unknown

- The public package has no request-level target logical prompt token metric or requested output limit, so a 202,752-compatible exact subset is unavailable.
- Public c8 is mixed-root global concurrency on 2P2D 32×H200 with MTP. It is not established as equivalent to any local cpyN label.

### Files for ID03 comparison

1. studies/h200_gpu_resident_mtp/reports/11_id03_deep_dive.md
2. studies/h200_gpu_resident_mtp/reports/12_id03_local_cpy_comparison_plan.md
3. studies/h200_gpu_resident_mtp/processed/id03_h200_reference_requests.csv
4. studies/h200_gpu_resident_mtp/processed/id03_source_coverage_by_concurrency.csv
5. studies/h200_gpu_resident_mtp/processed/id03_cross_concurrency_summary.csv
6. studies/h200_gpu_resident_mtp/processed/id03_exact_match_c8_c12.csv
7. studies/h200_gpu_resident_mtp/processed/id03_exact_match_c8_c16.csv
8. studies/h200_gpu_resident_mtp/processed/id03_exact_match_c12_c16.csv
9. studies/h200_gpu_resident_mtp/handoff/id03_local_join_contract.md


## c8 Concurrency / Scheduler Reconstruction

### Evidence

- **AgentX root lanes:** c8 configures eight root-trajectory lanes. It is not a declaration of eight HTTP or SGLang-running requests.
- **HTTP/client interval overlap:** max=11; time-weighted mean=3.968259088179123; P90=7.0; P95=8.0. These are `[request_start_ns, request_end_ns)` profile intervals with end-before-start tie handling, never relabelled as GPU or scheduler running concurrency.
- **Root/subagent overlap:** maximum root=7; maximum subagent=7. Branch origin is not backend worker or GPU affinity.
- **ID03 c8 load relation:** unadjusted Spearman HTTP-overlap-at-start vs TTFT: ρ=0.0239237, p=0.796207, n=119.
- **Observed scheduler counters:** prefill rank-series maximum running/waiting=5.0/5.0; decode rank-series maximum running/waiting=2.0/0.0. These are explicit AIPerf public server-metrics export series, not summed worker or cluster totals.

| metric | value | status | evidence_scope | notes |
| --- | --- | --- | --- | --- |
| agentx_root_concurrency_configured | 8 | Evidence | AIPerf c8 command / trajectory lanes | Configured root-trajectory lane count; not HTTP or scheduler running count. |
| http_max_inflight | 11 | Evidence | 957 successful profiling request [start,end) intervals | HTTP/client-observed overlap; never interpreted as scheduler running or GPU concurrency. |
| http_time_weighted_mean_inflight | 3.968259088179123 | Evidence | 957 successful profiling request [start,end) intervals | HTTP/client-observed overlap; never interpreted as scheduler running or GPU concurrency. |
| http_time_weighted_p50_inflight | 4.0 | Evidence | 957 successful profiling request [start,end) intervals | HTTP/client-observed overlap; never interpreted as scheduler running or GPU concurrency. |
| http_time_weighted_p75_inflight | 5.0 | Evidence | 957 successful profiling request [start,end) intervals | HTTP/client-observed overlap; never interpreted as scheduler running or GPU concurrency. |
| http_time_weighted_p90_inflight | 7.0 | Evidence | 957 successful profiling request [start,end) intervals | HTTP/client-observed overlap; never interpreted as scheduler running or GPU concurrency. |
| http_time_weighted_p95_inflight | 8.0 | Evidence | 957 successful profiling request [start,end) intervals | HTTP/client-observed overlap; never interpreted as scheduler running or GPU concurrency. |
| http_time_weighted_p99_inflight | 9.0 | Evidence | 957 successful profiling request [start,end) intervals | HTTP/client-observed overlap; never interpreted as scheduler running or GPU concurrency. |
| http_max_root_inflight | 7 | Evidence | 957 successful profiling request [start,end) intervals | HTTP/client-observed overlap; never interpreted as scheduler running or GPU concurrency. |
| http_max_subagent_inflight | 7 | Evidence | 957 successful profiling request [start,end) intervals | HTTP/client-observed overlap; never interpreted as scheduler running or GPU concurrency. |
| http_time_weighted_mean_root_inflight | 2.587678942023965 | Evidence | 957 successful profiling request [start,end) intervals | HTTP/client-observed overlap; never interpreted as scheduler running or GPU concurrency. |
| http_time_weighted_mean_subagent_inflight | 1.3805801461551577 | Evidence | 957 successful profiling request [start,end) intervals | HTTP/client-observed overlap; never interpreted as scheduler running or GPU concurrency. |
| http_fraction_time_inflight_ge_8 | 0.05264858957537656 | Evidence | 957 successful profiling request [start,end) intervals | HTTP/client-observed overlap; never interpreted as scheduler running or GPU concurrency. |
| http_fraction_time_inflight_ge_12 | 0.0 | Evidence | 957 successful profiling request [start,end) intervals | HTTP/client-observed overlap; never interpreted as scheduler running or GPU concurrency. |
| http_fraction_time_inflight_ge_16 | 0.0 | Evidence | 957 successful profiling request [start,end) intervals | HTTP/client-observed overlap; never interpreted as scheduler running or GPU concurrency. |
| http_fraction_time_inflight_ge_24 | 0.0 | Evidence | 957 successful profiling request [start,end) intervals | HTTP/client-observed overlap; never interpreted as scheduler running or GPU concurrency. |
| http_fraction_time_inflight_ge_32 | 0.0 | Evidence | 957 successful profiling request [start,end) intervals | HTTP/client-observed overlap; never interpreted as scheduler running or GPU concurrency. |
| prefill_configured_max_running | 32 | Evidence | public startup ServerArgs / runtime evidence | Configured capacity, not observed runtime running-request count. |
| decode_configured_max_running | 200 | Evidence | public startup ServerArgs / runtime evidence | Configured capacity, not observed runtime running-request count. |
| prefill_observed_max_running | 5.0 | Evidence | AIPerf profiling-window 1-second server-metrics timeslices; maximum across endpoint/rank-export series | Rank-export series are not summed to a worker or cluster total; this is not a global scheduler total. |
| prefill_observed_max_waiting | 5.0 | Evidence | AIPerf profiling-window 1-second server-metrics timeslices; maximum across endpoint/rank-export series | Rank-export series are not summed to a worker or cluster total; this is not a global scheduler total. |
| decode_observed_max_running | 2.0 | Evidence | AIPerf profiling-window 1-second server-metrics timeslices; maximum across endpoint/rank-export series | Rank-export series are not summed to a worker or cluster total; this is not a global scheduler total. |
| decode_observed_max_waiting | 0.0 | Evidence | AIPerf profiling-window 1-second server-metrics timeslices; maximum across endpoint/rank-export series | Rank-export series are not summed to a worker or cluster total; this is not a global scheduler total. |
| router_queue_wait_checkpoint_profile_request_count | 18 | Evidence | exact frontend router request ID -> x_request_id -> profiling row join | Long-wait refresh checkpoints are not final scheduler queue time. |
| router_queue_wait_checkpoint_max_ms | 27520.0 | Evidence | exact frontend router request ID -> x_request_id -> profiling row join | Long-wait refresh checkpoint, not full per-request queue decomposition. |
| h200_explicit_queue_time | aggregate_scheduler_histogram_and_router_checkpoints_available | Evidence | SGLang queue_time_seconds rank-series histogram plus exact long-wait router checkpoint events | No complete request-level scheduler lifecycle join exists; TTFT cannot be decomposed into queue versus execution. |
| routing_exact_profile_join_count | 957 | Evidence | raw profile x_request_id -> frontend request-completed log | Dynamo worker routing only, not GPU affinity. |

| valid_interval_request_count | max_inflight | time_weighted_mean_inflight | time_weighted_p90_inflight | time_weighted_p95_inflight | same_timestamp_policy |
| --- | --- | --- | --- | --- | --- |
| 957 | 11 | 3.96826 | 7 | 8 | all end events before starts; start context includes all same-timestamp starts |

| scope | source_branch_type | request_count | ttft_median_ms | ttft_p90_ms | e2e_median_ms | e2e_p90_ms | weighted_itl_ms | weighted_decode_tps | system_inflight_at_start_median | system_inflight_at_start_p90 | metric_scope |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_c8 | root | 518 | 2194.89 | 20816.7 | 10146.4 | 40657.5 | 10.7587 | 92.9482 | 4 | 7 | source branch origin; not backend worker/GPU affinity |
| all_c8 | subagent | 439 | 1195.63 | 10757.9 | 5590.29 | 25176.3 | 10.9173 | 91.5975 | 5 | 8 | source branch origin; not backend worker/GPU affinity |
| id03_c8 | root | 9 | 1155.27 | 3317.08 | 4624.45 | 44713.3 | 10.5072 | 95.1732 | 3 | 4.4 | source branch origin; not backend worker/GPU affinity |
| id03_c8 | subagent | 110 | 1071.77 | 3316.38 | 3503.7 | 7217.62 | 11.2503 | 88.8866 | 5 | 8 | source branch origin; not backend worker/GPU affinity |

| predictor | outcome | sample_count | spearman_rho | p_value | classification | notes |
| --- | --- | --- | --- | --- | --- | --- |
| system_inflight_at_start | ttft_ms | 119 | 0.0239237 | 0.796207 | Evidence | Spearman on ID03 public c8 profile rows; HTTP interval overlap at request start, not an SGLang scheduler counter or causal estimate |
| system_inflight_at_start | e2e_ms | 119 | 0.0220144 | 0.812158 | Evidence | Spearman on ID03 public c8 profile rows; HTTP interval overlap at request start, not an SGLang scheduler counter or causal estimate |
| system_inflight_at_start | itl_ms | 119 | 0.514686 | 2.12318e-09 | Evidence | Spearman on ID03 public c8 profile rows; HTTP interval overlap at request start, not an SGLang scheduler counter or causal estimate |
| root_inflight_at_start | ttft_ms | 119 | -0.129642 | 0.159949 | Evidence | Spearman on ID03 public c8 profile rows; HTTP interval overlap at request start, not an SGLang scheduler counter or causal estimate |
| subagent_inflight_at_start | ttft_ms | 119 | 0.0634474 | 0.493019 | Evidence | Spearman on ID03 public c8 profile rows; HTTP interval overlap at request start, not an SGLang scheduler counter or causal estimate |

| component | endpoint_url | worker_id | metric | rank_series_count | timeslice_sample_count_total | observed_min_across_rank_series | observed_max_across_rank_series | rank_series_median_avg | rank_series_median_p50 | rank_series_median_p90 | rank_series_median_p95 | rank_series_min_of_max | rank_series_max_of_max | description | scope_note | summary_sampling | classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| prefill | http://10.49.123.178:7501/metrics | 694d9fdfb4d8ee15 | sglang:num_decode_prealloc_queue_reqs | 8 | 28976 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | The number of requests in the decode prealloc queue. | AIPerf public server-metrics profiling export; explicit SGLang metric; prefill endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| prefill | http://10.49.14.237:7500/metrics | 694d9fdfb4d8ee13 | sglang:num_decode_prealloc_queue_reqs | 8 | 28920 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | The number of requests in the decode prealloc queue. | AIPerf public server-metrics profiling export; explicit SGLang metric; prefill endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| prefill | http://10.49.123.178:7501/metrics | 694d9fdfb4d8ee15 | sglang:num_decode_transfer_queue_reqs | 8 | 28976 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | The number of requests in the decode transfer queue. | AIPerf public server-metrics profiling export; explicit SGLang metric; prefill endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| prefill | http://10.49.14.237:7500/metrics | 694d9fdfb4d8ee13 | sglang:num_decode_transfer_queue_reqs | 8 | 28920 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | The number of requests in the decode transfer queue. | AIPerf public server-metrics profiling export; explicit SGLang metric; prefill endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| prefill | http://10.49.123.178:7501/metrics | 694d9fdfb4d8ee15 | sglang:num_prefill_bootstrap_queue_reqs | 8 | 28976 | 0 | 2 | 0.166713 | 0 | 1 | 1 | 2 | 2 | The number of requests in the prefill bootstrap queue. | AIPerf public server-metrics profiling export; explicit SGLang metric; prefill endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| prefill | http://10.49.14.237:7500/metrics | 694d9fdfb4d8ee13 | sglang:num_prefill_bootstrap_queue_reqs | 8 | 28920 | 0 | 5 | 0.257953 | 0 | 1 | 1 | 5 | 5 | The number of requests in the prefill bootstrap queue. | AIPerf public server-metrics profiling export; explicit SGLang metric; prefill endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| prefill | http://10.49.123.178:7501/metrics | 694d9fdfb4d8ee15 | sglang:num_prefill_inflight_queue_reqs | 8 | 28976 | 0 | 4 | 0.148353 | 0 | 1 | 1 | 4 | 4 | The number of requests in the prefill inflight queue. | AIPerf public server-metrics profiling export; explicit SGLang metric; prefill endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| prefill | http://10.49.14.237:7500/metrics | 694d9fdfb4d8ee13 | sglang:num_prefill_inflight_queue_reqs | 8 | 28920 | 0 | 3 | 0.202951 | 0 | 1 | 1 | 3 | 3 | The number of requests in the prefill inflight queue. | AIPerf public server-metrics profiling export; explicit SGLang metric; prefill endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| prefill | http://10.49.123.178:7501/metrics | 694d9fdfb4d8ee15 | sglang:num_queue_reqs | 8 | 28976 | 0 | 5 | 0.116648 | 0 | 0 | 1 | 5 | 5 | The number of requests in the waiting queue. | AIPerf public server-metrics profiling export; explicit SGLang metric; prefill endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| prefill | http://10.49.14.237:7500/metrics | 694d9fdfb4d8ee13 | sglang:num_queue_reqs | 8 | 28920 | 0 | 5 | 0.117012 | 0 | 0 | 1 | 5 | 5 | The number of requests in the waiting queue. | AIPerf public server-metrics profiling export; explicit SGLang metric; prefill endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| prefill | http://10.49.123.178:7501/metrics | 694d9fdfb4d8ee15 | sglang:num_running_reqs | 8 | 28976 | 0 | 5 | 0.268912 | 0 | 1 | 1 | 5 | 5 | The number of running requests. | AIPerf public server-metrics profiling export; explicit SGLang metric; prefill endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| prefill | http://10.49.14.237:7500/metrics | 694d9fdfb4d8ee13 | sglang:num_running_reqs | 8 | 28920 | 0 | 4 | 0.356846 | 0 | 1 | 1 | 4 | 4 | The number of running requests. | AIPerf public server-metrics profiling export; explicit SGLang metric; prefill endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| prefill | http://10.49.123.178:7501/metrics | 694d9fdfb4d8ee15 | sglang:queue_time_seconds | 8 |  |  |  | 1.89882 | 0.00242168 | 5.91515 | 16.0662 |  |  | Histogram of queueing time in seconds. | AIPerf public server-metrics profiling export; explicit SGLang metric; prefill endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | aggregate AIPerf histogram/export statistics; no usable gauge timeslice value for this metric | Evidence |
| prefill | http://10.49.14.237:7500/metrics | 694d9fdfb4d8ee13 | sglang:queue_time_seconds | 8 |  |  |  | 1.33629 | 0.00272312 | 4.18158 | 9.12922 |  |  | Histogram of queueing time in seconds. | AIPerf public server-metrics profiling export; explicit SGLang metric; prefill endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | aggregate AIPerf histogram/export statistics; no usable gauge timeslice value for this metric | Evidence |

| component | endpoint_url | worker_id | metric | rank_series_count | timeslice_sample_count_total | observed_min_across_rank_series | observed_max_across_rank_series | rank_series_median_avg | rank_series_median_p50 | rank_series_median_p90 | rank_series_median_p95 | rank_series_min_of_max | rank_series_max_of_max | description | scope_note | summary_sampling | classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| decode | http://10.49.115.1:7503/metrics | 694d9fdfb4d8ee1b | sglang:num_decode_prealloc_queue_reqs | 8 | 28992 | 0 | 4 | 0.0108996 | 0 | 0 | 0 | 1 | 4 | The number of requests in the decode prealloc queue. | AIPerf public server-metrics profiling export; explicit SGLang metric; decode endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| decode | http://10.49.62.108:7502/metrics | 694d9fdfb4d8ee18 | sglang:num_decode_prealloc_queue_reqs | 8 | 28856 | 0 | 4 | 0.0104196 | 0 | 0 | 0 | 1 | 4 | The number of requests in the decode prealloc queue. | AIPerf public server-metrics profiling export; explicit SGLang metric; decode endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| decode | http://10.49.115.1:7503/metrics | 694d9fdfb4d8ee1b | sglang:num_decode_transfer_queue_reqs | 8 | 28992 | 0 | 2 | 0.0116584 | 0 | 0 | 0 | 0 | 2 | The number of requests in the decode transfer queue. | AIPerf public server-metrics profiling export; explicit SGLang metric; decode endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| decode | http://10.49.62.108:7502/metrics | 694d9fdfb4d8ee18 | sglang:num_decode_transfer_queue_reqs | 8 | 28856 | 0 | 2 | 0.00764717 | 0 | 0 | 0 | 0 | 2 | The number of requests in the decode transfer queue. | AIPerf public server-metrics profiling export; explicit SGLang metric; decode endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| decode | http://10.49.115.1:7503/metrics | 694d9fdfb4d8ee1b | sglang:num_prefill_bootstrap_queue_reqs | 8 | 28992 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | The number of requests in the prefill bootstrap queue. | AIPerf public server-metrics profiling export; explicit SGLang metric; decode endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| decode | http://10.49.62.108:7502/metrics | 694d9fdfb4d8ee18 | sglang:num_prefill_bootstrap_queue_reqs | 8 | 28856 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | The number of requests in the prefill bootstrap queue. | AIPerf public server-metrics profiling export; explicit SGLang metric; decode endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| decode | http://10.49.115.1:7503/metrics | 694d9fdfb4d8ee1b | sglang:num_prefill_inflight_queue_reqs | 8 | 28992 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | The number of requests in the prefill inflight queue. | AIPerf public server-metrics profiling export; explicit SGLang metric; decode endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| decode | http://10.49.62.108:7502/metrics | 694d9fdfb4d8ee18 | sglang:num_prefill_inflight_queue_reqs | 8 | 28856 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | The number of requests in the prefill inflight queue. | AIPerf public server-metrics profiling export; explicit SGLang metric; decode endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| decode | http://10.49.115.1:7503/metrics | 694d9fdfb4d8ee1b | sglang:num_queue_reqs | 8 | 28992 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | The number of requests in the waiting queue. | AIPerf public server-metrics profiling export; explicit SGLang metric; decode endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| decode | http://10.49.62.108:7502/metrics | 694d9fdfb4d8ee18 | sglang:num_queue_reqs | 8 | 28856 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | The number of requests in the waiting queue. | AIPerf public server-metrics profiling export; explicit SGLang metric; decode endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| decode | http://10.49.115.1:7503/metrics | 694d9fdfb4d8ee1b | sglang:num_running_reqs | 8 | 28992 | 0 | 2 | 0.292081 | 0 | 1 | 1 | 1 | 2 | The number of running requests. | AIPerf public server-metrics profiling export; explicit SGLang metric; decode endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| decode | http://10.49.62.108:7502/metrics | 694d9fdfb4d8ee18 | sglang:num_running_reqs | 8 | 28856 | 0 | 2 | 0.346918 | 0 | 1 | 1 | 2 | 2 | The number of running requests. | AIPerf public server-metrics profiling export; explicit SGLang metric; decode endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | profiling-window 1-second AIPerf timeslice samples; per-rank series are summarized but never summed | Evidence |
| decode | http://10.49.115.1:7503/metrics | 694d9fdfb4d8ee1b | sglang:queue_time_seconds | 8 |  |  |  | 0.000178409 | 0.000172711 | 0.000326799 | 0.000345477 |  |  | Histogram of queueing time in seconds. | AIPerf public server-metrics profiling export; explicit SGLang metric; decode endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | aggregate AIPerf histogram/export statistics; no usable gauge timeslice value for this metric | Evidence |
| decode | http://10.49.62.108:7502/metrics | 694d9fdfb4d8ee18 | sglang:queue_time_seconds | 8 |  |  |  | 0.000196121 | 0.000185756 | 0.000366957 | 0.000389268 |  |  | Histogram of queueing time in seconds. | AIPerf public server-metrics profiling export; explicit SGLang metric; decode endpoint/rank-series scope. Values across rank exports are not summed into a worker or cluster count. | aggregate AIPerf histogram/export statistics; no usable gauge timeslice value for this metric | Evidence |

### Inference

- c8 does **not** imply only eight simultaneous HTTP requests: the observed interval maximum exceeds eight. It also cannot be converted into actual SGLang batch size, per-worker active request total, or GPU sequence count.
- The public counters provide evidence of rank-series pressure and occasional prefill waiting, but not a cluster-global scheduler-saturation conclusion. Configured prefill/decode limits (32/200) remain capacity settings, not observed runtime totals.
- The public ID03 relation is descriptive only: it neither proves a queueing cause nor controls for workload shape, route, cache state, or MTP behavior.

### Unknown

- Global scheduler saturation is unknown. Rank-series counters require topology/ownership validation; the later worker/cluster reconstruction validates decode DP-shard aggregation only, while prefill and unique P/D global totals remain Unknown.
- A complete per-request H200 queue time is unavailable. The package has aggregate SGLang queue-time evidence and a limited set of exact Dynamo router long-wait checkpoints, but no request-correlated accepted→queued→running→first-token lifecycle. TTFT cannot be decomposed into queueing versus execution from these data alone.
- Selected Dynamo worker routing is not backend GPU affinity; no per-request prefill/decode scheduler-pressure join is established.

### Files ChatGPT should read for c8 concurrency

1. `studies/h200_gpu_resident_mtp/reports/13_c8_concurrency_scheduler_reconstruction.md`
2. `studies/h200_gpu_resident_mtp/processed/c8_concurrency_reconstruction_summary.csv`
3. `studies/h200_gpu_resident_mtp/processed/c8_http_concurrency_summary.csv`
4. `studies/h200_gpu_resident_mtp/processed/c8_requests_with_inflight_context.csv`
5. `studies/h200_gpu_resident_mtp/processed/id03_c8_with_system_load.csv`
6. `studies/h200_gpu_resident_mtp/processed/id03_c8_backend_pressure.csv`
7. `studies/h200_gpu_resident_mtp/processed/id03_c8_load_latency_relationship.csv`
8. `studies/h200_gpu_resident_mtp/processed/id03_c8_load_buckets.csv`
9. `studies/h200_gpu_resident_mtp/processed/c8_scheduler_metric_inventory.csv`
10. `studies/h200_gpu_resident_mtp/processed/c8_prefill_scheduler_summary.csv`
11. `studies/h200_gpu_resident_mtp/processed/c8_decode_scheduler_summary.csv`
12. `studies/h200_gpu_resident_mtp/processed/c8_backend_worker_routing_summary.csv`
13. `studies/h200_gpu_resident_mtp/processed/c8_router_queue_wait_checkpoint_summary.csv`


## c8 Worker/Cluster Scheduler Reconstruction

### Evidence

- **Prefill TP verdict:** TP8/ATTN_CP8 metrics are CP-rank local scheduler views. Raw series are highly synchronized but not perfectly identical; neither TP8 multiplication nor a unique-worker gauge is proven.
- **Prefill rank envelopes:** running maxima are 5.0 and 4.0; these are pressure evidence, not unique worker request counts.
- **Decode DP verdict:** TP8/DP8 DP-attention exposes independent rank-local scheduler shards. Exact source semantics plus complete raw grids validate summing ranks within a decode worker.
- **Decode cluster:** exact endpoint-interval intersection gives running max=17.0, P90=10.0 (Validated reconstruction); generic `sglang:num_queue_reqs` is zero in every observed decode DP-rank sample.
- **Dynamo cross-check:** component inflight is correlated with but not equal to SGLang running; frontend/request-plane counters remain separate layers.

| metric | value | status | scope | notes |
| --- | --- | --- | --- | --- |
| http_max_inflight | 11 | Evidence | HTTP/client [request_start_ns, request_end_ns) profile overlap | Not an SGLang scheduler running-request count. |
| http_time_weighted_mean | 3.968259088179123 | Evidence | HTTP/client [request_start_ns, request_end_ns) profile overlap | Not an SGLang scheduler running-request count. |
| http_p90 | 7.0 | Evidence | HTTP/client [request_start_ns, request_end_ns) profile overlap | Not an SGLang scheduler running-request count. |
| http_p95 | 8.0 | Evidence | HTTP/client [request_start_ns, request_end_ns) profile overlap | Not an SGLang scheduler running-request count. |
| prefill_worker_0_max_running | Unknown | Unknown | unique logical requests at one CP8 prefill worker | The rank envelope is recorded separately; neither rank sum nor a unique worker count is proven. |
| prefill_worker_0_rank_envelope_max_running | 5.0 | Strong inference | rank-envelope running requests | Pressure evidence only, not a unique logical worker request count. |
| prefill_worker_0_max_waiting | Unknown | Unknown | unique logical requests at one CP8 prefill worker | The rank envelope is recorded separately; neither rank sum nor a unique worker count is proven. |
| prefill_worker_0_rank_envelope_max_waiting | 5.0 | Strong inference | rank-envelope queue requests | Pressure evidence only, not a unique logical worker request count. |
| prefill_worker_1_max_running | Unknown | Unknown | unique logical requests at one CP8 prefill worker | The rank envelope is recorded separately; neither rank sum nor a unique worker count is proven. |
| prefill_worker_1_rank_envelope_max_running | 4.0 | Strong inference | rank-envelope running requests | Pressure evidence only, not a unique logical worker request count. |
| prefill_worker_1_max_waiting | Unknown | Unknown | unique logical requests at one CP8 prefill worker | The rank envelope is recorded separately; neither rank sum nor a unique worker count is proven. |
| prefill_worker_1_rank_envelope_max_waiting | 5.0 | Strong inference | rank-envelope queue requests | Pressure evidence only, not a unique logical worker request count. |
| prefill_cluster_max_running | Unknown | Unknown | two prefill workers' unique logical request union | Do not sum TP ranks or strong-inference rank envelopes across workers. |
| prefill_cluster_p50_running | Unknown | Unknown | two prefill workers' unique logical request union | Unknown is intentionally not converted to zero. |
| prefill_cluster_p90_running | Unknown | Unknown | two prefill workers' unique logical request union | Unknown is intentionally not converted to zero. |
| prefill_cluster_p95_running | Unknown | Unknown | two prefill workers' unique logical request union | Unknown is intentionally not converted to zero. |
| prefill_cluster_max_waiting | Unknown | Unknown | two prefill workers' unique logical request union | Do not sum TP ranks or strong-inference rank envelopes across workers. |
| prefill_cluster_p50_waiting | Unknown | Unknown | two prefill workers' unique logical request union | Unknown is intentionally not converted to zero. |
| prefill_cluster_p90_waiting | Unknown | Unknown | two prefill workers' unique logical request union | Unknown is intentionally not converted to zero. |
| prefill_cluster_p95_waiting | Unknown | Unknown | two prefill workers' unique logical request union | Unknown is intentionally not converted to zero. |
| prefill_cluster_waiting_positive_fraction | Unknown | Unknown | two prefill workers' unique logical request union | Rank-local positive queue evidence exists but cluster positive fraction is not reconstructable. |
| decode_worker_0_max_running | 9.0 | Validated reconstruction | one decode worker, sum of complete DP8 rank-local scheduler shards | A logical request is assigned to one DP shard under the validated source mapping. |
| decode_worker_0_max_waiting | 0.0 | Validated reconstruction | one decode worker, sum of complete DP8 rank-local scheduler shards | A logical request is assigned to one DP shard under the validated source mapping. |
| decode_worker_1_max_running | 10.0 | Validated reconstruction | one decode worker, sum of complete DP8 rank-local scheduler shards | A logical request is assigned to one DP shard under the validated source mapping. |
| decode_worker_1_max_waiting | 0.0 | Validated reconstruction | one decode worker, sum of complete DP8 rank-local scheduler shards | A logical request is assigned to one DP shard under the validated source mapping. |
| decode_cluster_max_running | 17.0 | Validated reconstruction | two decode workers, sum only over exact overlapping raw endpoint intervals | This is decode-stage cluster occupancy, not P/D unique system-global running. |
| decode_cluster_p50_running | 4.0 | Validated reconstruction | two decode workers, sum only over exact overlapping raw endpoint intervals | This is decode-stage cluster occupancy, not P/D unique system-global running. |
| decode_cluster_p90_running | 10.0 | Validated reconstruction | two decode workers, sum only over exact overlapping raw endpoint intervals | This is decode-stage cluster occupancy, not P/D unique system-global running. |
| decode_cluster_p95_running | 12.0 | Validated reconstruction | two decode workers, sum only over exact overlapping raw endpoint intervals | This is decode-stage cluster occupancy, not P/D unique system-global running. |
| decode_cluster_max_waiting | 0.0 | Validated reconstruction | two decode workers, sum only over exact overlapping raw endpoint intervals | This is decode-stage cluster occupancy, not P/D unique system-global running. |

- Table is truncated to 30 rows.

| component | worker_id | metric | timeslice_sample_count | rank_envelope_max_of_min | rank_envelope_p50_of_median | rank_envelope_p90_of_median | rank_envelope_p95_of_median | rank_envelope_max | unique_worker_value | status | rank_semantics_verdict | reconstruction_method | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| prefill | 694d9fdfb4d8ee13 | rank-envelope running requests | 3615 | 4 | 0 | 1 | 1 | 4 | Unknown | Strong inference | unresolved | TP/CP rank envelope (min/median/max); no rank sum or worker unique union | Do not read rank_envelope_max as a validated logical worker request count. |
| prefill | 694d9fdfb4d8ee13 | rank-envelope waiting/queue requests | 3615 | 5 | 0 | 0 | 1 | 5 | Unknown | Strong inference | unresolved | TP/CP rank envelope (min/median/max); no rank sum or worker unique union | Do not read rank_envelope_max as a validated logical worker request count. |
| prefill | 694d9fdfb4d8ee13 | rank-envelope prefill bootstrap queue | 3615 | 5 | 0 | 1 | 1 | 5 | Unknown | Strong inference | unresolved | TP/CP rank envelope (min/median/max); no rank sum or worker unique union | Do not read rank_envelope_max as a validated logical worker request count. |
| prefill | 694d9fdfb4d8ee13 | rank-envelope prefill inflight queue | 3615 | 3 | 0 | 1 | 1 | 3 | Unknown | Strong inference | unresolved | TP/CP rank envelope (min/median/max); no rank sum or worker unique union | Do not read rank_envelope_max as a validated logical worker request count. |
| prefill | 694d9fdfb4d8ee15 | rank-envelope running requests | 3622 | 5 | 0 | 1 | 1 | 5 | Unknown | Strong inference | unresolved | TP/CP rank envelope (min/median/max); no rank sum or worker unique union | Do not read rank_envelope_max as a validated logical worker request count. |
| prefill | 694d9fdfb4d8ee15 | rank-envelope waiting/queue requests | 3622 | 5 | 0 | 0 | 1 | 5 | Unknown | Strong inference | unresolved | TP/CP rank envelope (min/median/max); no rank sum or worker unique union | Do not read rank_envelope_max as a validated logical worker request count. |
| prefill | 694d9fdfb4d8ee15 | rank-envelope prefill bootstrap queue | 3622 | 2 | 0 | 1 | 1 | 2 | Unknown | Strong inference | unresolved | TP/CP rank envelope (min/median/max); no rank sum or worker unique union | Do not read rank_envelope_max as a validated logical worker request count. |
| prefill | 694d9fdfb4d8ee15 | rank-envelope prefill inflight queue | 3622 | 4 | 0 | 1 | 1 | 4 | Unknown | Strong inference | unresolved | TP/CP rank envelope (min/median/max); no rank sum or worker unique union | Do not read rank_envelope_max as a validated logical worker request count. |

| component | worker_id | metric | timeslice_sample_count | max | p50 | p90 | p95 | positive_fraction | status | reconstruction_method | notes | dp_semantics | decode_waiting_all_zero_raw_rank_series |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| decode | 694d9fdfb4d8ee18 | running_requests | 3607 | 10 | 2 | 7 | 8 | 0.747436 | Validated reconstruction | sum of validated independent rank-local scheduler shards | Raw one-second exporter samples; no null-to-zero conversion. DP rank sum requires complete raw 8-rank grids. | validated independent scheduler shards (TP8/DP8/DP attention) |  |
| decode | 694d9fdfb4d8ee18 | waiting_requests | 3607 | 0 | 0 | 0 | 0 | 0 | Validated reconstruction | sum of validated independent rank-local scheduler shards | Raw one-second exporter samples; no null-to-zero conversion. DP rank sum requires complete raw 8-rank grids. | validated independent scheduler shards (TP8/DP8/DP attention) | True |
| decode | 694d9fdfb4d8ee18 | decode_prealloc_queue_requests | 3607 | 4 | 0 | 2 | 3 | 0.207929 | Validated reconstruction | sum of validated independent rank-local scheduler shards | Raw one-second exporter samples; no null-to-zero conversion. DP rank sum requires complete raw 8-rank grids. | validated independent scheduler shards (TP8/DP8/DP attention) |  |
| decode | 694d9fdfb4d8ee18 | decode_transfer_queue_requests | 3607 | 2 | 0 | 0 | 1 | 0.0629332 | Validated reconstruction | sum of validated independent rank-local scheduler shards | Raw one-second exporter samples; no null-to-zero conversion. DP rank sum requires complete raw 8-rank grids. | validated independent scheduler shards (TP8/DP8/DP attention) |  |
| decode | 694d9fdfb4d8ee1b | running_requests | 3624 | 9 | 1 | 7 | 8 | 0.665287 | Validated reconstruction | sum of validated independent rank-local scheduler shards | Raw one-second exporter samples; no null-to-zero conversion. DP rank sum requires complete raw 8-rank grids. | validated independent scheduler shards (TP8/DP8/DP attention) |  |
| decode | 694d9fdfb4d8ee1b | waiting_requests | 3624 | 0 | 0 | 0 | 0 | 0 | Validated reconstruction | sum of validated independent rank-local scheduler shards | Raw one-second exporter samples; no null-to-zero conversion. DP rank sum requires complete raw 8-rank grids. | validated independent scheduler shards (TP8/DP8/DP attention) | True |
| decode | 694d9fdfb4d8ee1b | decode_prealloc_queue_requests | 3624 | 4 | 0 | 1 | 1 | 0.143488 | Validated reconstruction | sum of validated independent rank-local scheduler shards | Raw one-second exporter samples; no null-to-zero conversion. DP rank sum requires complete raw 8-rank grids. | validated independent scheduler shards (TP8/DP8/DP attention) |  |
| decode | 694d9fdfb4d8ee1b | decode_transfer_queue_requests | 3624 | 3 | 0 | 0 | 1 | 0.0706402 | Validated reconstruction | sum of validated independent rank-local scheduler shards | Raw one-second exporter samples; no null-to-zero conversion. DP rank sum requires complete raw 8-rank grids. | validated independent scheduler shards (TP8/DP8/DP attention) |  |

| component | metric | worker_a | worker_b | overlap_segment_count | common_worker_overlap_s | common_worker_overlap_fraction_of_profile | max | time_weighted_mean | p50 | p75 | p90 | p95 | p99 | positive_fraction | status | reconstruction_method | decode_waiting_all_zero_raw_rank_series | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| decode | running_requests | 694d9fdfb4d8ee1b | 694d9fdfb4d8ee18 | 7185 | 3592.85 | 0.987046 | 17 | 5.14057 | 4 | 8 | 10 | 12 | 15 | 0.917739 | Validated reconstruction | sum of validated worker scheduler counts over exact endpoint interval intersections |  | sum of validated worker scheduler counts over exact endpoint interval intersections; DP rank sums are valid only because source topology and complete grids are both verified. |
| decode | waiting_requests | 694d9fdfb4d8ee1b | 694d9fdfb4d8ee18 | 7185 | 3592.85 | 0.987046 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Validated reconstruction | sum of validated worker scheduler counts over exact endpoint interval intersections | True | sum of validated worker scheduler counts over exact endpoint interval intersections; DP rank sums are valid only because source topology and complete grids are both verified. |
| decode | decode_prealloc_queue_requests | 694d9fdfb4d8ee1b | 694d9fdfb4d8ee18 | 7185 | 3592.85 | 0.987046 | 5 | 0.541441 | 0 | 1 | 2 | 3 | 4 | 0.325967 | Validated reconstruction | sum of validated worker scheduler counts over exact endpoint interval intersections |  | sum of validated worker scheduler counts over exact endpoint interval intersections; DP rank sums are valid only because source topology and complete grids are both verified. |
| decode | decode_transfer_queue_requests | 694d9fdfb4d8ee1b | 694d9fdfb4d8ee18 | 7185 | 3592.85 | 0.987046 | 4 | 0.143479 | 0 | 0 | 1 | 1 | 2 | 0.123454 | Validated reconstruction | sum of validated worker scheduler counts over exact endpoint interval intersections |  | sum of validated worker scheduler counts over exact endpoint interval intersections; DP rank sums are valid only because source topology and complete grids are both verified. |

### Unknown

- Prefill worker/cluster **unique** running and waiting remain Unknown: no CP-rank request-ID union is exported.
- Prefill + decode cannot become unique system-global running: request-correlated P/D handoff and cross-stage deduplication are absent.
- Decode `num_queue_reqs=0` is the named generic queue only, not a statement that PD prealloc/transfer queues are zero.

### Files ChatGPT should read next

1. `studies/h200_gpu_resident_mtp/reports/15_c8_scheduler_worker_cluster_reconstruction.md`
2. `studies/h200_gpu_resident_mtp/processed/c8_cluster_scheduler_reconstruction.csv`
3. `studies/h200_gpu_resident_mtp/processed/c8_scheduler_rank_semantics_validation.csv`
4. `studies/h200_gpu_resident_mtp/processed/c8_prefill_worker_scheduler_summary.csv`
5. `studies/h200_gpu_resident_mtp/processed/c8_prefill_cluster_scheduler_summary.csv`
6. `studies/h200_gpu_resident_mtp/processed/c8_decode_rank_scheduler_summary.csv`
7. `studies/h200_gpu_resident_mtp/processed/c8_decode_worker_scheduler_summary.csv`
8. `studies/h200_gpu_resident_mtp/processed/c8_decode_cluster_scheduler_summary.csv`
9. `studies/h200_gpu_resident_mtp/processed/c8_dynamo_sglang_concurrency_crosscheck.csv`
10. `studies/h200_gpu_resident_mtp/processed/c8_scheduler_source_semantics.csv`


- **Scope warning:** full per-ID CSVs retain `usage_prompt_cache_read_tokens` only as a raw profile counter; `raw_profile_cache_counter_tps` is not a validated logical-prompt or physical-KV metric.


## HiSparse c8 vs GPU-resident c8

| comparison_scope | metric | hisparse_c8_value | gpu_resident_mtp_c8_value | gpu_resident_over_hisparse_ratio | hisparse_request_count | gpu_resident_request_count | exact_matched_source_key_count | strict_ttft_count | strict_decode_count | caveat |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| run_level_unpaired_observed_system_difference | ttft_median_ms | 228708 | 1471.05 | 0.00643201 | 219 | 957 |  |  |  | 16→32 GPUs, 1P1D→2P2D, KV mode/dtype, MTP, and software may differ; not a causal HiSparse estimate. |
| run_level_unpaired_observed_system_difference | weighted_decode_tps | 32.5161 | 92.4771 | 2.84404 | 219 | 957 |  |  |  | 16→32 GPUs, 1P1D→2P2D, KV mode/dtype, MTP, and software may differ; not a causal HiSparse estimate. |
| run_level_unpaired_observed_system_difference | wall_output_tps | 23.5666 | 210.505 | 8.93234 | 219 | 957 |  |  |  | 16→32 GPUs, 1P1D→2P2D, KV mode/dtype, MTP, and software may differ; not a causal HiSparse estimate. |
| run_level_unpaired_observed_system_difference | output_tokens_total | 84618 | 760694 | 8.98974 | 219 | 957 |  |  |  | 16→32 GPUs, 1P1D→2P2D, KV mode/dtype, MTP, and software may differ; not a causal HiSparse estimate. |
| source_key_matched_median_observed_system_ratio | ttft_ratio_gpu_resident_over_hisparse |  | 0.00880767 | 0.00880767 | 83 | 83 | 83 | 83 | 64 | Source-key matching controls workload identity only; it does not isolate a single architecture change. |
| source_key_matched_median_observed_system_ratio | itl_ratio_gpu_resident_over_hisparse |  | 0.353382 | 0.353382 | 83 | 83 | 83 | 83 | 64 | Source-key matching controls workload identity only; it does not isolate a single architecture change. |
| source_key_matched_median_observed_system_ratio | e2e_ratio_gpu_resident_over_hisparse |  | 0.0482293 | 0.0482293 | 83 | 83 | 83 | 83 | 64 | Source-key matching controls workload identity only; it does not isolate a single architecture change. |

## Approximate worker-normalized H200 context

| comparison_label | comparison_kind | comparison_scope | hisparse_concurrency | gpu_resident_mtp_concurrency | hisparse_decode_worker_count | gpu_resident_mtp_decode_worker_count | metric | hisparse_value | gpu_resident_mtp_value | gpu_resident_over_hisparse_ratio | hisparse_request_count | gpu_resident_request_count | hisparse_root_id_count | gpu_resident_root_id_count | hisparse_itl_sample_count | gpu_resident_itl_sample_count | exact_matched_source_key_count | same_output_length_count | strict_ttft_count | strict_decode_count | matching_method | worker_normalization_basis | caveat |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| approximate_worker_normalized_hisparse_c4_vs_gpu_resident_mtp_c8 | approximate_worker_normalized_observed_system_ratio | run_level_unpaired_observed_system_difference | 4 | 8 | 1 | 2 | ttft_median_ms | 3319.23 | 1471.05 | 0.44319 | 379 | 957 | 8 | 14 | 267 | 853 |  |  |  |  |  | 1 HiSparse decode worker at c4 versus 2 GPU-resident MTP decode workers at c8; concurrency ratio is architectural context, not a demonstrated per-worker load match | Approximate worker-normalized mixed-workload comparison only: public HiSparse uses 1 decode worker and GPU-resident MTP uses 2 decode workers. This does not establish equal routing or active concurrency per worker; observed worker_id is request metadata, not backend GPU-affinity evidence. Other architecture, GPU-count, KV-mode/dtype, MTP, and software differences remain confounded. |
| approximate_worker_normalized_hisparse_c4_vs_gpu_resident_mtp_c8 | approximate_worker_normalized_observed_system_ratio | run_level_unpaired_observed_system_difference | 4 | 8 | 1 | 2 | itl_weighted_ms | 34.7805 | 10.8135 | 0.310907 | 379 | 957 | 8 | 14 | 267 | 853 |  |  |  |  |  | 1 HiSparse decode worker at c4 versus 2 GPU-resident MTP decode workers at c8; concurrency ratio is architectural context, not a demonstrated per-worker load match | Approximate worker-normalized mixed-workload comparison only: public HiSparse uses 1 decode worker and GPU-resident MTP uses 2 decode workers. This does not establish equal routing or active concurrency per worker; observed worker_id is request metadata, not backend GPU-affinity evidence. Other architecture, GPU-count, KV-mode/dtype, MTP, and software differences remain confounded. |
| approximate_worker_normalized_hisparse_c4_vs_gpu_resident_mtp_c8 | approximate_worker_normalized_observed_system_ratio | run_level_unpaired_observed_system_difference | 4 | 8 | 1 | 2 | weighted_decode_tps | 28.7518 | 92.4771 | 3.2164 | 379 | 957 | 8 | 14 | 267 | 853 |  |  |  |  |  | 1 HiSparse decode worker at c4 versus 2 GPU-resident MTP decode workers at c8; concurrency ratio is architectural context, not a demonstrated per-worker load match | Approximate worker-normalized mixed-workload comparison only: public HiSparse uses 1 decode worker and GPU-resident MTP uses 2 decode workers. This does not establish equal routing or active concurrency per worker; observed worker_id is request metadata, not backend GPU-affinity evidence. Other architecture, GPU-count, KV-mode/dtype, MTP, and software differences remain confounded. |
| approximate_worker_normalized_hisparse_c4_vs_gpu_resident_mtp_c8 | approximate_worker_normalized_observed_system_ratio | run_level_unpaired_observed_system_difference | 4 | 8 | 1 | 2 | wall_output_tps | 67.038 | 210.505 | 3.14008 | 379 | 957 | 8 | 14 | 267 | 853 |  |  |  |  |  | 1 HiSparse decode worker at c4 versus 2 GPU-resident MTP decode workers at c8; concurrency ratio is architectural context, not a demonstrated per-worker load match | Approximate worker-normalized mixed-workload comparison only: public HiSparse uses 1 decode worker and GPU-resident MTP uses 2 decode workers. This does not establish equal routing or active concurrency per worker; observed worker_id is request metadata, not backend GPU-affinity evidence. Other architecture, GPU-count, KV-mode/dtype, MTP, and software differences remain confounded. |
| approximate_worker_normalized_hisparse_c4_vs_gpu_resident_mtp_c8 | approximate_worker_normalized_observed_system_ratio | run_level_unpaired_observed_system_difference | 4 | 8 | 1 | 2 | output_tokens_total | 243209 | 760694 | 3.12774 | 379 | 957 | 8 | 14 | 267 | 853 |  |  |  |  |  | 1 HiSparse decode worker at c4 versus 2 GPU-resident MTP decode workers at c8; concurrency ratio is architectural context, not a demonstrated per-worker load match | Approximate worker-normalized mixed-workload comparison only: public HiSparse uses 1 decode worker and GPU-resident MTP uses 2 decode workers. This does not establish equal routing or active concurrency per worker; observed worker_id is request metadata, not backend GPU-affinity evidence. Other architecture, GPU-count, KV-mode/dtype, MTP, and software differences remain confounded. |
| approximate_worker_normalized_hisparse_c4_vs_gpu_resident_mtp_c8 | approximate_worker_normalized_observed_system_ratio | source_key_matched_median_observed_system_ratio | 4 | 8 | 1 | 2 | ttft_ratio_gpu_resident_over_hisparse |  | 0.495075 | 0.495075 | 379 | 957 | 8 | 14 | 267 | 853 | 120 | 120 | 120 | 68 | source_trace_id+source_outer_idx+source_inner_idx | 1 HiSparse decode worker at c4 versus 2 GPU-resident MTP decode workers at c8; concurrency ratio is architectural context, not a demonstrated per-worker load match | Approximate worker-normalized mixed-workload comparison only: public HiSparse uses 1 decode worker and GPU-resident MTP uses 2 decode workers. This does not establish equal routing or active concurrency per worker; observed worker_id is request metadata, not backend GPU-affinity evidence. Other architecture, GPU-count, KV-mode/dtype, MTP, and software differences remain confounded. |
| approximate_worker_normalized_hisparse_c4_vs_gpu_resident_mtp_c8 | approximate_worker_normalized_observed_system_ratio | source_key_matched_median_observed_system_ratio | 4 | 8 | 1 | 2 | itl_ratio_gpu_resident_over_hisparse |  | 0.337038 | 0.337038 | 379 | 957 | 8 | 14 | 267 | 853 | 120 | 120 | 120 | 68 | source_trace_id+source_outer_idx+source_inner_idx | 1 HiSparse decode worker at c4 versus 2 GPU-resident MTP decode workers at c8; concurrency ratio is architectural context, not a demonstrated per-worker load match | Approximate worker-normalized mixed-workload comparison only: public HiSparse uses 1 decode worker and GPU-resident MTP uses 2 decode workers. This does not establish equal routing or active concurrency per worker; observed worker_id is request metadata, not backend GPU-affinity evidence. Other architecture, GPU-count, KV-mode/dtype, MTP, and software differences remain confounded. |
| approximate_worker_normalized_hisparse_c4_vs_gpu_resident_mtp_c8 | approximate_worker_normalized_observed_system_ratio | source_key_matched_median_observed_system_ratio | 4 | 8 | 1 | 2 | e2e_ratio_gpu_resident_over_hisparse |  | 0.318269 | 0.318269 | 379 | 957 | 8 | 14 | 267 | 853 | 120 | 120 | 120 | 68 | source_trace_id+source_outer_idx+source_inner_idx | 1 HiSparse decode worker at c4 versus 2 GPU-resident MTP decode workers at c8; concurrency ratio is architectural context, not a demonstrated per-worker load match | Approximate worker-normalized mixed-workload comparison only: public HiSparse uses 1 decode worker and GPU-resident MTP uses 2 decode workers. This does not establish equal routing or active concurrency per worker; observed worker_id is request metadata, not backend GPU-affinity evidence. Other architecture, GPU-count, KV-mode/dtype, MTP, and software differences remain confounded. |
| approximate_worker_normalized_hisparse_c8_vs_gpu_resident_mtp_c16 | approximate_worker_normalized_observed_system_ratio | run_level_unpaired_observed_system_difference | 8 | 16 | 1 | 2 | ttft_median_ms | 228708 | 22688.7 | 0.0992037 | 219 | 969 | 11 | 24 | 167 | 853 |  |  |  |  |  | 1 HiSparse decode worker at c8 versus 2 GPU-resident MTP decode workers at c16; concurrency ratio is architectural context, not a demonstrated per-worker load match | Approximate worker-normalized mixed-workload comparison only: public HiSparse uses 1 decode worker and GPU-resident MTP uses 2 decode workers. This does not establish equal routing or active concurrency per worker; observed worker_id is request metadata, not backend GPU-affinity evidence. Other architecture, GPU-count, KV-mode/dtype, MTP, and software differences remain confounded. |
| approximate_worker_normalized_hisparse_c8_vs_gpu_resident_mtp_c16 | approximate_worker_normalized_observed_system_ratio | run_level_unpaired_observed_system_difference | 8 | 16 | 1 | 2 | itl_weighted_ms | 30.754 | 10.9083 | 0.354696 | 219 | 969 | 11 | 24 | 167 | 853 |  |  |  |  |  | 1 HiSparse decode worker at c8 versus 2 GPU-resident MTP decode workers at c16; concurrency ratio is architectural context, not a demonstrated per-worker load match | Approximate worker-normalized mixed-workload comparison only: public HiSparse uses 1 decode worker and GPU-resident MTP uses 2 decode workers. This does not establish equal routing or active concurrency per worker; observed worker_id is request metadata, not backend GPU-affinity evidence. Other architecture, GPU-count, KV-mode/dtype, MTP, and software differences remain confounded. |
| approximate_worker_normalized_hisparse_c8_vs_gpu_resident_mtp_c16 | approximate_worker_normalized_observed_system_ratio | run_level_unpaired_observed_system_difference | 8 | 16 | 1 | 2 | weighted_decode_tps | 32.5161 | 91.6733 | 2.81932 | 219 | 969 | 11 | 24 | 167 | 853 |  |  |  |  |  | 1 HiSparse decode worker at c8 versus 2 GPU-resident MTP decode workers at c16; concurrency ratio is architectural context, not a demonstrated per-worker load match | Approximate worker-normalized mixed-workload comparison only: public HiSparse uses 1 decode worker and GPU-resident MTP uses 2 decode workers. This does not establish equal routing or active concurrency per worker; observed worker_id is request metadata, not backend GPU-affinity evidence. Other architecture, GPU-count, KV-mode/dtype, MTP, and software differences remain confounded. |
| approximate_worker_normalized_hisparse_c8_vs_gpu_resident_mtp_c16 | approximate_worker_normalized_observed_system_ratio | run_level_unpaired_observed_system_difference | 8 | 16 | 1 | 2 | wall_output_tps | 23.5666 | 236.913 | 10.0529 | 219 | 969 | 11 | 24 | 167 | 853 |  |  |  |  |  | 1 HiSparse decode worker at c8 versus 2 GPU-resident MTP decode workers at c16; concurrency ratio is architectural context, not a demonstrated per-worker load match | Approximate worker-normalized mixed-workload comparison only: public HiSparse uses 1 decode worker and GPU-resident MTP uses 2 decode workers. This does not establish equal routing or active concurrency per worker; observed worker_id is request metadata, not backend GPU-affinity evidence. Other architecture, GPU-count, KV-mode/dtype, MTP, and software differences remain confounded. |
| approximate_worker_normalized_hisparse_c8_vs_gpu_resident_mtp_c16 | approximate_worker_normalized_observed_system_ratio | run_level_unpaired_observed_system_difference | 8 | 16 | 1 | 2 | output_tokens_total | 84618 | 859611 | 10.1587 | 219 | 969 | 11 | 24 | 167 | 853 |  |  |  |  |  | 1 HiSparse decode worker at c8 versus 2 GPU-resident MTP decode workers at c16; concurrency ratio is architectural context, not a demonstrated per-worker load match | Approximate worker-normalized mixed-workload comparison only: public HiSparse uses 1 decode worker and GPU-resident MTP uses 2 decode workers. This does not establish equal routing or active concurrency per worker; observed worker_id is request metadata, not backend GPU-affinity evidence. Other architecture, GPU-count, KV-mode/dtype, MTP, and software differences remain confounded. |
| approximate_worker_normalized_hisparse_c8_vs_gpu_resident_mtp_c16 | approximate_worker_normalized_observed_system_ratio | source_key_matched_median_observed_system_ratio | 8 | 16 | 1 | 2 | ttft_ratio_gpu_resident_over_hisparse |  | 0.110806 | 0.110806 | 219 | 969 | 11 | 24 | 167 | 853 | 54 | 54 | 54 | 35 | source_trace_id+source_outer_idx+source_inner_idx | 1 HiSparse decode worker at c8 versus 2 GPU-resident MTP decode workers at c16; concurrency ratio is architectural context, not a demonstrated per-worker load match | Approximate worker-normalized mixed-workload comparison only: public HiSparse uses 1 decode worker and GPU-resident MTP uses 2 decode workers. This does not establish equal routing or active concurrency per worker; observed worker_id is request metadata, not backend GPU-affinity evidence. Other architecture, GPU-count, KV-mode/dtype, MTP, and software differences remain confounded. |
| approximate_worker_normalized_hisparse_c8_vs_gpu_resident_mtp_c16 | approximate_worker_normalized_observed_system_ratio | source_key_matched_median_observed_system_ratio | 8 | 16 | 1 | 2 | itl_ratio_gpu_resident_over_hisparse |  | 0.355862 | 0.355862 | 219 | 969 | 11 | 24 | 167 | 853 | 54 | 54 | 54 | 35 | source_trace_id+source_outer_idx+source_inner_idx | 1 HiSparse decode worker at c8 versus 2 GPU-resident MTP decode workers at c16; concurrency ratio is architectural context, not a demonstrated per-worker load match | Approximate worker-normalized mixed-workload comparison only: public HiSparse uses 1 decode worker and GPU-resident MTP uses 2 decode workers. This does not establish equal routing or active concurrency per worker; observed worker_id is request metadata, not backend GPU-affinity evidence. Other architecture, GPU-count, KV-mode/dtype, MTP, and software differences remain confounded. |
| approximate_worker_normalized_hisparse_c8_vs_gpu_resident_mtp_c16 | approximate_worker_normalized_observed_system_ratio | source_key_matched_median_observed_system_ratio | 8 | 16 | 1 | 2 | e2e_ratio_gpu_resident_over_hisparse |  | 0.114997 | 0.114997 | 219 | 969 | 11 | 24 | 167 | 853 | 54 | 54 | 54 | 35 | source_trace_id+source_outer_idx+source_inner_idx | 1 HiSparse decode worker at c8 versus 2 GPU-resident MTP decode workers at c16; concurrency ratio is architectural context, not a demonstrated per-worker load match | Approximate worker-normalized mixed-workload comparison only: public HiSparse uses 1 decode worker and GPU-resident MTP uses 2 decode workers. This does not establish equal routing or active concurrency per worker; observed worker_id is request metadata, not backend GPU-affinity evidence. Other architecture, GPU-count, KV-mode/dtype, MTP, and software differences remain confounded. |

- **Inference:** these rows align one HiSparse decode worker with two GPU-resident MTP decode workers only as an architectural context. Routing and active load are not proven equal, and every other system difference remains confounded.


## User 2GPU Contextual Comparison

| system_id | system_label | root_trace_id | source | verification_status | raw_local_logs_available | gpu_count | topology | concurrency | max_model_len | hisparse_status | kv_residency_status | mtp_speculative_status | successful_profiling_requests | aiperf_transmitted_requests | termination | termination_position | input_tokens | output_tokens | wall_span_s | average_ttft_ms | weighted_decode_tps | interpretation_limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| system_a_local_2gpu | User-reported 2-GPU aggregated reference | 0196085d85d2075a50b74cd8795ffbdcea9a | user_reported | user_reported_unverified | False | 2 | aggregated | 1 | 202752 | inference_off_unverified | inference_gpu_resident_unverified | unknown | 43 | 44 | Context overflow | 9/198 | 4511748 | 72723 | 1396.66 | 6039.89 | 80.38 | Evidence scope is limited to values supplied by the user; no local raw logs were available. Not request-level evidence and not apples-to-apples with public 32xH200 MTP replay. |
| system_a_local_2gpu | User-reported 2-GPU aggregated reference | 02bc0afb13f7a2d9efa86c28511261d85c0e | user_reported | user_reported_unverified | False | 2 | aggregated | 1 | 202752 | inference_off_unverified | inference_gpu_resident_unverified | unknown | 201 | 202 | Context overflow | 63/254 | 14852880 | 148475 | 3726.76 | 827.832 | 90.864 | Evidence scope is limited to values supplied by the user; no local raw logs were available. Not request-level evidence and not apples-to-apples with public 32xH200 MTP replay. |

## Evidence

- Public artifacts, their checksums, aggregate validation, and recipe/runtime-log findings are versioned in this study.

## Inference

- GPU-resident versus HiSparse c8 findings are observed system-level ratios, not isolated causal effects.

## Unknown

- Do not infer per-ID GPU attribution, physical KV allocation beyond log scope, or request-level local-server behavior without private raw evidence.

## Important Caveats

- Source workload model labels are not target-model labels.
- MTP changes output behavior; strict decode ratios require matching output lengths.
- Cache metrics have explicit scope labels; do not conflate a frontend/cache counter with physical KV residency.
- Server logs show dynamic routing across two prefill and two decode workers. Request `worker_id` is not demonstrated GPU or backend-worker affinity; see `../processed/worker_distribution.csv`.

## Files ChatGPT Should Read Next

1. `studies/h200_gpu_resident_mtp/reports/results_summary_ko.md`
2. `studies/h200_gpu_resident_mtp/processed/concurrency_summary.csv`
3. `studies/h200_gpu_resident_mtp/processed/schema_mapping.csv`
4. `studies/h200_gpu_resident_mtp/processed/profile_field_inventory.csv`
5. `studies/h200_gpu_resident_mtp/processed/profile_metric_inventory.csv`
6. `studies/h200_gpu_resident_mtp/processed/requested_id_resolution.csv`
7. `studies/h200_gpu_resident_mtp/processed/h200_c8_hisparse_vs_gpu_resident.csv`
8. `studies/h200_gpu_resident_mtp/processed/exact_match_c8_summary.csv`
9. `studies/h200_gpu_resident_mtp/processed/kv_cache_runtime.csv`
10. `studies/h200_gpu_resident_mtp/processed/worker_distribution.csv`
11. `studies/h200_gpu_resident_mtp/manifests/provenance.json`
12. `studies/h200_gpu_resident_mtp/handoff/local_server_evidence_needed.md`
