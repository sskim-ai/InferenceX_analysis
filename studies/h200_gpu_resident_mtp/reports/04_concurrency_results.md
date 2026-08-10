# 04. c8 / c12 / c16 concurrency results

## Evidence

| concurrency | profiled_request_count | root_id_count | input_sequence_length_total | output_tokens_total | wall_span_s | ttft_mean_ms | ttft_median_ms | ttft_p90_ms | weighted_decode_tps | wall_output_tps | itl_sample_count | error_count_all_rows | cancellation_count_all_rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | 957 | 14 | 7.91149e+07 | 760694 | 3613.67 | 6399.09 | 1471.05 | 18344.2 | 92.4771 | 210.505 | 853 | 0 | 0 |
| 12 | 1072 | 19 | 9.3451e+07 | 875495 | 3603.61 | 14039.5 | 4337.19 | 37845.8 | 91.2868 | 242.949 | 916 | 0 | 0 |
| 16 | 969 | 24 | 8.72659e+07 | 859611 | 3628.38 | 34544.1 | 22688.7 | 86235.6 | 91.6733 | 236.913 | 853 | 0 | 0 |

### Source-root vs source-subagent origin

| concurrency | source_branch_type | profiled_request_count | root_id_count | input_sequence_length_total | output_tokens_total | ttft_median_ms | ttft_p90_ms | itl_weighted_ms | weighted_decode_tps | e2e_median_ms | wall_output_tps | scope |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | root | 518 | 14 | 4.56052e+07 | 497789 | 2194.89 | 20816.7 | 10.7587 | 92.9482 | 10146.4 | 137.752 | source branch origin joined through loader metadata; not replay suffix taxonomy |
| 8 | subagent | 439 | 7 | 3.35097e+07 | 262905 | 1195.63 | 10757.9 | 10.9173 | 91.5975 | 5590.29 | 82.1089 | source branch origin joined through loader metadata; not replay suffix taxonomy |
| 12 | root | 623 | 19 | 5.84804e+07 | 624173 | 7637.54 | 42368 | 10.9045 | 91.705 | 17099.4 | 173.208 | source branch origin joined through loader metadata; not replay suffix taxonomy |
| 12 | subagent | 449 | 7 | 3.49706e+07 | 251322 | 1976.78 | 30964 | 11.0786 | 90.2638 | 6409.4 | 76.7299 | source branch origin joined through loader metadata; not replay suffix taxonomy |
| 16 | root | 640 | 24 | 6.13655e+07 | 654980 | 24643.3 | 88062 | 10.8961 | 91.776 | 33776.2 | 180.516 | source branch origin joined through loader metadata; not replay suffix taxonomy |
| 16 | subagent | 329 | 8 | 2.59004e+07 | 204631 | 16451.6 | 82170.9 | 10.9474 | 91.3457 | 22800.1 | 57.4769 | source branch origin joined through loader metadata; not replay suffix taxonomy |

## Inference

- Cross-concurrency changes are interpreted only after observed source-ID coverage and source-key matching; fixed-duration replay can change workload coverage.

## Unknown

- No individual conversation ID is assigned a fixed GPU, GPU count, or hardware affinity.
