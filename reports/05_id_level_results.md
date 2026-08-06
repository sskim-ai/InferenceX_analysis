# 05. ID-level observed H200 replay results

## Evidence

- **Evidence:** valid profiling rows `2,491` are summarized into `57` root-ID × concurrency rows. `session_num` groups are retained as opaque/unvalidated metadata and are not treated as independent replay instances.

| weighting | sample_count | median_ttft_ms | median_itl_ms | median_e2e_ms |
|---|---|---|---|---|
| request_weighted | 2491 | 3647.66 | 31.4302 | 25045.1 |
| root_id_weighted | 57 | 103299 | 31.4717 | 135321 |
| session_num_group_weighted_unvalidated | 2491 | 3647.66 | 31.4302 | 25045.1 |
| output_token_weighted_itl | 1365 |  | 31.9766 |  |
- **Evidence:** ID-concurrency table (trace IDs are shortened only in reports; full public IDs remain in CSV/Parquet):

| root_trace_id | concurrency | distinct_replay_instances | session_num_group_count | session_num_unique_row_rate | replay_instance_identity_status | profiled_request_count | root_request_count | subagent_request_count | median_ttft_ms | median_itl_ms | median_e2e_ms | wall_clock_output_rate | sample_quality_flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0196085d85d2… | 1 | 90 | 90 | 1 | unvalidated_session_num_group | 90 | 85 | 5 | 3031.4 | 29.445 | 3088.83 | 5.17004 | session_num_unique_per_profiled_row |
| 02bc0afb13f7… | 1 | 265 | 265 | 1 | unvalidated_session_num_group | 265 | 13 | 252 | 1045.6 | 30.2385 | 4091.29 | 44.0201 | session_num_unique_per_profiled_row |
| 0196085d85d2… | 2 | 88 | 88 | 1 | unvalidated_session_num_group | 88 | 83 | 5 | 3257.14 | 30.4596 | 3257.14 | 2.5595 | session_num_unique_per_profiled_row |
| 02bc0afb13f7… | 2 | 177 | 177 | 1 | unvalidated_session_num_group | 177 | 0 | 177 | 2173.75 | 29.0788 | 2189.82 | 1.11235 | session_num_unique_per_profiled_row |
| 03e110ac6921… | 2 | 86 | 86 | 1 | unvalidated_session_num_group | 86 | 37 | 49 | 1256.14 | 32.2096 | 10327.1 | 42.1208 | session_num_unique_per_profiled_row |
| 0470d446a451… | 2 | 44 | 44 | 1 | unvalidated_session_num_group | 44 | 44 | 0 | 1032.39 | 31.865 | 19310.6 | 29.1281 | session_num_unique_per_profiled_row |
| 0196085d85d2… | 3 | 107 | 107 | 1 | unvalidated_session_num_group | 107 | 102 | 5 | 3100.31 | 29.8246 | 3100.31 | 2.10462 | session_num_unique_per_profiled_row |
| 02bc0afb13f7… | 3 | 188 | 188 | 1 | unvalidated_session_num_group | 188 | 0 | 188 | 2343.94 | 32.305 | 2369.13 | 0.901539 | session_num_unique_per_profiled_row |
| 03e110ac6921… | 3 | 42 | 42 | 1 | unvalidated_session_num_group | 42 | 4 | 38 | 5284.9 | 29.4652 | 30176.6 | 23.451 | session_num_unique_per_profiled_row |
| 0470d446a451… | 3 | 50 | 50 | 1 | unvalidated_session_num_group | 50 | 50 | 0 | 1117.13 | 31.3897 | 27745.2 | 20.1499 | session_num_unique_per_profiled_row |
| 04dba6fe6213… | 3 | 25 | 25 | 1 | unvalidated_session_num_group | 25 | 7 | 18 | 52355.6 | 31.007 | 95170.6 | 60.7636 | session_num_unique_per_profiled_row |
| 05c249572509… | 3 | 21 | 21 | 1 | unvalidated_session_num_group | 21 | 19 | 2 | 1269.67 | 31.1596 | 19132.8 | 30.5029 | session_num_unique_per_profiled_row |
| 05f72f78a037… | 3 | 22 | 22 | 1 | unvalidated_session_num_group | 22 | 22 | 0 | 887.245 | 32.0529 | 18582.6 | 26.6816 | session_num_unique_per_profiled_row |
| 002001296e8a… | 4 | 31 | 31 | 1 | unvalidated_session_num_group | 31 | 31 | 0 | 66687.3 |  | 66687.3 | 0.014497 | session_num_unique_per_profiled_row |
| 0196085d85d2… | 4 | 59 | 59 | 1 | unvalidated_session_num_group | 59 | 54 | 5 | 12517.8 | 33.8361 | 17796.7 | 1.64638 | session_num_unique_per_profiled_row |
| 02bc0afb13f7… | 4 | 108 | 108 | 1 | unvalidated_session_num_group | 108 | 5 | 103 | 3806.75 | 33.6736 | 18427.4 | 25.5289 | session_num_unique_per_profiled_row |
| 03e110ac6921… | 4 | 73 | 73 | 1 | unvalidated_session_num_group | 73 | 31 | 42 | 36498.3 | 32.0632 | 52322.7 | 13.2102 | session_num_unique_per_profiled_row |
| 0470d446a451… | 4 | 46 | 46 | 1 | unvalidated_session_num_group | 46 | 46 | 0 | 1125.87 | 34.5484 | 25321.5 | 24.9079 | session_num_unique_per_profiled_row |
| 04dba6fe6213… | 4 | 25 | 25 | 1 | unvalidated_session_num_group | 25 | 7 | 18 | 2002.34 | 38.6387 | 65843.1 | 76.0121 | session_num_unique_per_profiled_row |
| 05c249572509… | 4 | 21 | 21 | 1 | unvalidated_session_num_group | 21 | 19 | 2 | 1078.05 | 33.9108 | 20397.1 | 31.7066 | session_num_unique_per_profiled_row |
| 05f72f78a037… | 4 | 16 | 16 | 1 | unvalidated_session_num_group | 16 | 16 | 0 | 888.138 | 35.219 | 16463.2 | 24.3559 | session_num_unique_per_profiled_row |
| 002001296e8a… | 5 | 24 | 24 | 1 | unvalidated_session_num_group | 24 | 18 | 6 | 155334 | 32.7302 | 179871 | 2.40251 | session_num_unique_per_profiled_row |
| 006c98de37d8… | 5 | 11 | 11 | 1 | unvalidated_session_num_group | 11 | 11 | 0 | 78366.8 | 30.248 | 100132 | 7.34376 | session_num_unique_per_profiled_row |
| 00ca01c4aaec… | 5 | 4 | 4 | 1 | unvalidated_session_num_group | 4 | 4 | 0 | 90445.1 |  | 90445.1 | 0.00987439 | session_num_unique_per_profiled_row |
| 0196085d85d2… | 5 | 48 | 48 | 1 | unvalidated_session_num_group | 48 | 47 | 1 | 3643.32 | 32.0254 | 3643.32 | 0.266509 | session_num_unique_per_profiled_row |
- **Evidence:** Replay branch taxonomy is parsed from H200 conversation-ID suffixes; source-origin taxonomy is inherited from mapped nested source traces. They are separate dimensions, not interchangeable root/subagent labels.

Replay branch summary:

| concurrency | branch_type | profiled_request_count | distinct_root_ids | median_input_tokens | median_ttft_ms | median_itl_ms | median_e2e_ms | error_count | cancellation_count |
|---|---|---|---|---|---|---|---|---|---|
| 1 | auxiliary | 1 | 1 | 1 | 3919.41 |  | 3919.41 | 0 | 0 |
| 1 | fanout | 101 | 2 | 1 | 1404.14 | 30.9067 | 1572.22 | 0 | 0 |
| 1 | root | 98 | 2 | 1 | 3004.81 | 28.852 | 3125.17 | 0 | 0 |
| 1 | subagent_main | 155 | 1 | 52834 | 804.809 | 30.197 | 4466.14 | 0 | 0 |
| 2 | auxiliary | 4 | 2 | 1 | 9220.42 | 31.8433 | 9220.42 | 0 | 0 |
| 2 | fanout | 179 | 2 | 1 | 2176.5 | 29.6917 | 2208.44 | 0 | 0 |
| 2 | root | 164 | 3 | 1 | 2801.69 | 31.865 | 3722.25 | 0 | 0 |
| 2 | subagent_main | 48 | 1 | 47888.5 | 914.888 | 32.3786 | 12627.2 | 0 | 0 |
| 3 | auxiliary | 18 | 3 | 2967 | 63332.3 | 29.6251 | 113321 | 0 | 0 |
| 3 | fanout | 190 | 2 | 1 | 2359.9 | 31.0814 | 2386.34 | 0 | 0 |
| 3 | root | 204 | 6 | 1 | 2779.36 | 31.4785 | 8017.72 | 0 | 0 |
| 3 | subagent_main | 43 | 2 | 54802 | 4535.92 | 29.5304 | 38602.9 | 0 | 0 |
| 4 | auxiliary | 17 | 4 | 2966 | 2002.34 | 39.185 | 83237.5 | 0 | 0 |
| 4 | fanout | 26 | 2 | 130568 | 2870.89 | 34.1113 | 42304 | 0 | 0 |
| 4 | root | 209 | 8 | 1 | 3446.71 | 34.1707 | 27821.3 | 0 | 0 |
| 4 | subagent_main | 127 | 3 | 47896 | 2985.58 | 32.8571 | 25556.1 | 0 | 0 |
| 5 | fanout | 53 | 2 | 1 | 10289.3 | 32.5647 | 10289.3 | 0 | 0 |
| 5 | root | 110 | 6 | 1 | 70698.2 | 31.4636 | 83582.2 | 0 | 0 |
| 5 | subagent_main | 87 | 3 | 70400 | 68000.1 | 31.9283 | 85465.9 | 0 | 0 |
| 6 | auxiliary | 13 | 1 | 2966 | 107031 | 32.2112 | 180695 | 0 | 0 |
| 6 | fanout | 19 | 1 | 1 | 200324 |  | 200324 | 0 | 0 |
| 6 | root | 89 | 8 | 1 | 155291 | 31.7291 | 161799 | 0 | 0 |
| 6 | subagent_main | 76 | 4 | 47415.5 | 107613 | 31.8989 | 127823 | 0 | 0 |
| 7 | auxiliary | 13 | 1 | 2966 | 160827 | 29.6382 | 217534 | 0 | 0 |
| 7 | fanout | 29 | 2 | 93900 | 243324 | 31.2756 | 273444 | 0 | 0 |
| 7 | root | 65 | 7 | 1 | 209388 | 31.5134 | 215444 | 0 | 0 |
| 7 | subagent_main | 134 | 5 | 48573 | 183394 | 31.0607 | 193418 | 0 | 0 |
| 8 | auxiliary | 1 | 1 | 2581 | 245552 | 33.7951 | 246228 | 0 | 0 |
| 8 | fanout | 31 | 3 | 93901 | 232982 | 30.8597 | 237863 | 0 | 0 |
| 8 | root | 78 | 9 | 236.5 | 256454 | 30.7186 | 266210 | 0 | 0 |
| 8 | subagent_main | 109 | 4 | 48444 | 216214 | 30.6395 | 229750 | 0 | 0 |

Source-origin branch summary:

| concurrency | source_origin_branch_type | profiled_request_count | distinct_root_ids | median_input_tokens | median_ttft_ms | median_itl_ms | median_e2e_ms | error_count | cancellation_count |
|---|---|---|---|---|---|---|---|---|---|
| 1 | root | 200 | 2 | 1 | 2338.22 | 30.3997 | 2909.22 | 0 | 0 |
| 1 | subagent | 155 | 1 | 52834 | 804.809 | 30.197 | 4466.14 | 0 | 0 |
| 2 | root | 347 | 4 | 1 | 2399.18 | 31.6942 | 2868.78 | 0 | 0 |
| 2 | subagent | 48 | 1 | 47888.5 | 914.888 | 32.3786 | 12627.2 | 0 | 0 |
| 3 | root | 399 | 7 | 1 | 2575.72 | 31.4993 | 3217.84 | 0 | 0 |
| 3 | subagent | 56 | 2 | 45364.5 | 10470.3 | 29.5564 | 60194.4 | 0 | 0 |
| 4 | root | 239 | 8 | 7506 | 3446.71 | 34.1717 | 30971.8 | 0 | 0 |
| 4 | subagent | 140 | 3 | 44307.5 | 2356.96 | 33.3676 | 31796.6 | 0 | 0 |
| 5 | root | 163 | 7 | 1 | 57473.9 | 31.6183 | 67656.6 | 0 | 0 |
| 5 | subagent | 87 | 3 | 70400 | 68000.1 | 31.9283 | 85465.9 | 0 | 0 |
| 6 | root | 108 | 9 | 1 | 161618 | 31.7291 | 185243 | 0 | 0 |
| 6 | subagent | 89 | 4 | 43794 | 107348 | 31.955 | 137091 | 0 | 0 |
| 7 | root | 94 | 9 | 1 | 218041 | 31.3272 | 225007 | 0 | 0 |
| 7 | subagent | 147 | 5 | 45912 | 179287 | 31.0545 | 194431 | 0 | 0 |
| 8 | root | 110 | 11 | 2581 | 240815 | 30.7946 | 261117 | 0 | 0 |
| 8 | subagent | 109 | 4 | 48444 | 216214 | 30.6395 | 229750 | 0 | 0 |
- **Evidence:** `session_num` is retained as a replay grouping field; its observed uniqueness is diagnostic, not evidence that rows are independent replay instances.

| scope | concurrency | profiled_request_count | non_null_session_num_count | distinct_session_num | distinct_concurrency_session_num | duplicate_concurrency_session_num_row_count | session_num_unique_row_rate | session_num_uniqueness_key | session_num_semantics | replay_instance_identity_status | cross_concurrency_cluster_unit |
|---|---|---|---|---|---|---|---|---|---|---|---|
| all_profiled_rows |  | 2491 | 2491 | 455 | 2491 | 0 | 1 | (concurrency, session_num) | Unknown: session_num is unique per profiling row within observed concurrencies, but the profile export does not establish it as a replay-instance identifier. | unvalidated_session_num_group | root_trace_id |
| per_concurrency | 1 | 355 | 355 | 355 | 355 | 0 | 1 | (concurrency, session_num) | Unknown: session_num is unique per profiling row within observed concurrencies, but the profile export does not establish it as a replay-instance identifier. | unvalidated_session_num_group | root_trace_id |
| per_concurrency | 2 | 395 | 395 | 395 | 395 | 0 | 1 | (concurrency, session_num) | Unknown: session_num is unique per profiling row within observed concurrencies, but the profile export does not establish it as a replay-instance identifier. | unvalidated_session_num_group | root_trace_id |
| per_concurrency | 3 | 455 | 455 | 455 | 455 | 0 | 1 | (concurrency, session_num) | Unknown: session_num is unique per profiling row within observed concurrencies, but the profile export does not establish it as a replay-instance identifier. | unvalidated_session_num_group | root_trace_id |
| per_concurrency | 4 | 379 | 379 | 379 | 379 | 0 | 1 | (concurrency, session_num) | Unknown: session_num is unique per profiling row within observed concurrencies, but the profile export does not establish it as a replay-instance identifier. | unvalidated_session_num_group | root_trace_id |
| per_concurrency | 5 | 250 | 250 | 250 | 250 | 0 | 1 | (concurrency, session_num) | Unknown: session_num is unique per profiling row within observed concurrencies, but the profile export does not establish it as a replay-instance identifier. | unvalidated_session_num_group | root_trace_id |
| per_concurrency | 6 | 197 | 197 | 197 | 197 | 0 | 1 | (concurrency, session_num) | Unknown: session_num is unique per profiling row within observed concurrencies, but the profile export does not establish it as a replay-instance identifier. | unvalidated_session_num_group | root_trace_id |
| per_concurrency | 7 | 241 | 241 | 241 | 241 | 0 | 1 | (concurrency, session_num) | Unknown: session_num is unique per profiling row within observed concurrencies, but the profile export does not establish it as a replay-instance identifier. | unvalidated_session_num_group | root_trace_id |
| per_concurrency | 8 | 219 | 219 | 219 | 219 | 0 | 1 | (concurrency, session_num) | Unknown: session_num is unique per profiling row within observed concurrencies, but the profile export does not establish it as a replay-instance identifier. | unvalidated_session_num_group | root_trace_id |

## Inference

- **Inference:** request-weighted and root-ID-weighted values answer different questions. They must not be compared as interchangeable estimates, especially when replay coverage is uneven. Root trace ID, rather than session number, is the conservative cluster unit for paired bootstrap reporting.

## Unknown

- **Unknown:** `session_num` semantic identity is not validated as a de-correlated replay-instance identifier. A conversation ID remains a workload identifier; no available table supports per-ID GPU count, utilization, or hardware-affinity attribution.
