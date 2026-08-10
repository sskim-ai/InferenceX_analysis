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

| root_trace_id | concurrency | all_request_count | warmup_count | profiled_request_count | output_tokens_total | ttft_mean_ms | ttft_median_ms | ttft_p90_ms | itl_sample_count | weighted_decode_tps | e2e_median_ms | wall_span_s | wall_output_tps | error_count | cancellation_count | sample_quality |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0196085d85d2075a50b74cd8795ffbdcea9a | 8 | 69 | 11 | 58 | 941 | 13250.4 | 9300.9 | 31640.6 | 1 | 93.4123 | 9649.18 | 3276.51 | 0.287196 | 0 | 0 | observed |
| 0196085d85d2075a50b74cd8795ffbdcea9a | 12 | 56 | 11 | 45 | 45 | 29698.6 | 29178.2 | 41582.9 | 0 |  | 29178.2 | 3290.48 | 0.0136758 | 0 | 0 | observed |
| 0196085d85d2075a50b74cd8795ffbdcea9a | 16 | 49 | 11 | 38 | 38 | 44346.4 | 32193.5 | 86996.6 | 0 |  | 32193.5 | 3276.45 | 0.0115979 | 0 | 0 | observed |

## ID02 Key Metrics

| root_trace_id | concurrency | all_request_count | warmup_count | profiled_request_count | output_tokens_total | ttft_mean_ms | ttft_median_ms | ttft_p90_ms | itl_sample_count | weighted_decode_tps | e2e_median_ms | wall_span_s | wall_output_tps | error_count | cancellation_count | sample_quality |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 02bc0afb13f7a2d9efa86c28511261d85c0e | 8 | 8 | 8 | 0 |  |  |  |  | 0 |  |  |  |  | 0 | 0 | sparse |
| 02bc0afb13f7a2d9efa86c28511261d85c0e | 12 | 8 | 8 | 0 |  |  |  |  | 0 |  |  |  |  | 0 | 0 | sparse |
| 02bc0afb13f7a2d9efa86c28511261d85c0e | 16 | 8 | 8 | 0 |  |  |  |  | 0 |  |  |  |  | 0 | 0 | sparse |

- **Scope warning:** full per-ID CSVs retain `usage_prompt_cache_read_tokens` as an observed raw counter, but neither it nor `cache_load_tps` is a validated logical-prompt or physical-KV metric.


## HiSparse c8 vs GPU-resident c8

| comparison_scope | metric | hisparse_c8_value | gpu_resident_mtp_c8_value | gpu_resident_over_hisparse_ratio | sample_count | caveat |
| --- | --- | --- | --- | --- | --- | --- |
| run_level_unpaired_observed_system_difference | ttft_median_ms | 228708 | 1471.05 | 0.00643201 | 219 | 16→32 GPUs, 1P1D→2P2D, KV mode/dtype, MTP, and software may differ; not a causal HiSparse estimate. |
| run_level_unpaired_observed_system_difference | weighted_decode_tps | 32.5161 | 92.4771 | 2.84404 | 219 | 16→32 GPUs, 1P1D→2P2D, KV mode/dtype, MTP, and software may differ; not a causal HiSparse estimate. |
| run_level_unpaired_observed_system_difference | wall_output_tps | 23.5666 | 210.505 | 8.93234 | 219 | 16→32 GPUs, 1P1D→2P2D, KV mode/dtype, MTP, and software may differ; not a causal HiSparse estimate. |
| run_level_unpaired_observed_system_difference | output_tokens_total | 84618 | 760694 | 8.98974 | 219 | 16→32 GPUs, 1P1D→2P2D, KV mode/dtype, MTP, and software may differ; not a causal HiSparse estimate. |
| source_key_matched_median_observed_system_ratio | ttft_ratio_gpu_resident_over_hisparse |  | 0.00880767 | 0.00880767 | 83 | Source-key matching controls workload identity only; it does not isolate a single architecture change. |
| source_key_matched_median_observed_system_ratio | itl_ratio_gpu_resident_over_hisparse |  | 0.353382 | 0.353382 | 64 | Source-key matching controls workload identity only; it does not isolate a single architecture change. |
| source_key_matched_median_observed_system_ratio | e2e_ratio_gpu_resident_over_hisparse |  | 0.0482293 | 0.0482293 | 83 | Source-key matching controls workload identity only; it does not isolate a single architecture change. |

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
