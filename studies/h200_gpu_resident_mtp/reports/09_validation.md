# 09. Aggregate validation

## Evidence

| concurrency | validation_status | metric_count |
| --- | --- | --- |
| 8 | pass | 30 |
| 12 | pass | 30 |
| 16 | pass | 30 |

| concurrency | metric | raw_value | published_value | validation_status | validation_note |
| --- | --- | --- | --- | --- | --- |
| 8 | successful_profiled_request_count | 957 | 957.0 | pass |  |
| 8 | total_input_tokens | 79114864.0 | 79114863.99795 | pass | Evidence: derived from request_metrics.tokens.input.mean × num_requests_successful; published mean is rounded; validation uses an explicit rounding tolerance. |
| 8 | total_output_tokens | 760694.0 | 760693.99692 | pass | Evidence: derived from request_metrics.tokens.output_actual.mean × num_requests_successful; published mean is rounded; validation uses an explicit rounding tolerance. |
| 8 | mean_ttft_ms | 6399.0914568787875 | 6399.09 | pass |  |
| 8 | p50_ttft_ms | 1471.051316 | 1471.05 | pass |  |
| 8 | p75_ttft_ms | 5576.799265 | 5576.8 | pass |  |
| 8 | p90_ttft_ms | 18344.230512799997 | 18344.23 | pass |  |
| 8 | p95_ttft_ms | 26937.007524399993 | 26937.010000000002 | pass |  |
| 8 | mean_itl_ms | 11.744407782351972 | 11.74 | pass |  |
| 8 | p50_itl_ms | 10.716642911290323 | 10.72 | pass |  |
| 8 | p75_itl_ms | 11.064679986651836 | 11.06 | pass |  |
| 8 | p90_itl_ms | 11.90085407663384 | 11.9 | pass |  |
| 8 | p95_itl_ms | 12.35691664877551 | 12.36 | pass |  |
| 8 | mean_e2e_ms | 14983.636024176592 | 14983.64 | pass |  |
| 8 | p50_e2e_ms | 7539.518526999999 | 7539.52 | pass |  |
| 8 | p75_e2e_ms | 16806.900174 | 16806.899999999998 | pass |  |
| 8 | p90_e2e_ms | 33029.463884799996 | 33029.46 | pass |  |
| 8 | p95_e2e_ms | 49615.78091599998 | 49615.78 | pass |  |
| 8 | input_throughput_tps | 21893.24000818215 | 21893.24001 | pass |  |
| 8 | output_throughput_tps | 210.50477082010926 | 210.50477 | pass |  |
| 8 | total_throughput_tps | 22103.74477900226 | 22103.74478 | pass |  |
| 8 | duration_s | 3613.666317568 | 3613.66632 | pass |  |
| 8 | gpu_count | 32.0 | 32.0 | pass |  |
| 8 | per_gpu_input_throughput_tps | 684.1637502556922 | 684.16375 | pass | Raw value divides reconstructed shared-system throughput by recorded GPU count. |
| 8 | per_gpu_output_throughput_tps | 6.578274088128414 | 6.57827 | pass | Raw value divides reconstructed shared-system throughput by recorded GPU count. |
| 8 | per_gpu_total_throughput_tps | 690.7420243438206 | 690.74202 | pass | Raw value divides reconstructed shared-system throughput by recorded GPU count. |
| 8 | target_model | zai-org/GLM-5.2-FP8 | zai-org/GLM-5.2-FP8 | pass | Metadata comparison; raw context provenance must be checked separately from numeric reconstruction. |
| 8 | precision | FP8 | fp8 | pass | Metadata comparison; raw context provenance must be checked separately from numeric reconstruction. |
| 8 | framework | Dynamo + SGLang | dynamo-sglang | pass | Metadata comparison; raw context provenance must be checked separately from numeric reconstruction. |
| 8 | metadata_concurrency | 8 | 8.0 | pass |  |

- Table is truncated to 30 rows.

## Inference

- A pass is limited to the documented filtering, units, percentile convention, and available aggregate metric path.

## Unknown

- A not-comparable aggregate field is not a validation pass.
