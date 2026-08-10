# 08. User-reported 2-GPU contextual reference

## Evidence

| system_id | system_label | root_trace_id | source | verification_status | raw_local_logs_available | gpu_count | topology | concurrency | max_model_len | hisparse_status | kv_residency_status | mtp_speculative_status | successful_profiling_requests | aiperf_transmitted_requests | termination | termination_position | input_tokens | output_tokens | wall_span_s | average_ttft_ms | weighted_decode_tps | interpretation_limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| system_a_local_2gpu | User-reported 2-GPU aggregated reference | 0196085d85d2075a50b74cd8795ffbdcea9a | user_reported | user_reported_unverified | False | 2 | aggregated | 1 | 202752 | inference_off_unverified | inference_gpu_resident_unverified | unknown | 43 | 44 | Context overflow | 9/198 | 4511748 | 72723 | 1396.66 | 6039.89 | 80.38 | Evidence scope is limited to values supplied by the user; no local raw logs were available. Not request-level evidence and not apples-to-apples with public 32xH200 MTP replay. |
| system_a_local_2gpu | User-reported 2-GPU aggregated reference | 02bc0afb13f7a2d9efa86c28511261d85c0e | user_reported | user_reported_unverified | False | 2 | aggregated | 1 | 202752 | inference_off_unverified | inference_gpu_resident_unverified | unknown | 201 | 202 | Context overflow | 63/254 | 14852880 | 148475 | 3726.76 | 827.832 | 90.864 | Evidence scope is limited to values supplied by the user; no local raw logs were available. Not request-level evidence and not apples-to-apples with public 32xH200 MTP replay. |

## Inference

- These two rows are a provenance-labelled user-reported aggregate reference, useful for later review but not request-level evidence.

## Unknown

- No direct apples-to-apples conclusion is possible against 32×H200, 2P2D, MTP-enabled public replay without local raw logs and configuration evidence.
