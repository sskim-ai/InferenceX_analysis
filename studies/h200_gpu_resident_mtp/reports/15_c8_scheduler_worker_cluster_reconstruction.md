# 15. c8 SGLang worker / cluster scheduler reconstruction

## Scope

- This analysis uses only public c8 run 31235207041 server-metrics and server-log evidence. Backend scheduler exports are AIPerf one-second timeslice bins within the profiling window; the selected raw field is audited below rather than assumed to be an instantaneous scrape.
- `HTTP in-flight`, Dynamo work-handler inflight, SGLang scheduler waiting/running, and GPU/DP-rank scope are deliberately separate quantities.

## Why rank series could not initially be summed

### Evidence

- The public runtime is 2 prefill workers × TP8/ATTN_CP8 and 2 decode workers × TP8/DP8 with DP attention. Source mapping uses the exact public `SGLANG_BUILD_COMMIT` recorded in startup logs.

| runtime_container_tag | source_tag | source_commit | source_url | runtime_log_reference | mapping_status | mapping_caveat | topic | source_reference | source_finding | reconstruction_implication | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lmsysorg/sglang:v0.5.16-cu130 | v0.5.16 | fdebc938f7f4d16fe6b9f55dcd9a767cf0899ea1 | https://github.com/sgl-project/sglang/tree/fdebc938f7f4d16fe6b9f55dcd9a767cf0899ea1 | multinode_server_logs.tar.gz:fingerprint_prefill_w0.json:91; fingerprint_prefill_w1.json:91; fingerprint_decode_w0.json:91; fingerprint_decode_w1.json:91 | Evidence | Public decode startup logs record SGLANG_BUILD_COMMIT=fdebc938f7f4d16fe6b9f55dcd9a767cf0899ea1; the container digest itself remains unrecorded. | prefill_tp_cp_metrics | python/sglang/srt/observability/metrics_collector.py:1048-1070; python/sglang/srt/layers/dp_attention.py:293-307; python/sglang/srt/managers/scheduler_components/metrics_reporter.py:641-650 | Metric labels are emitted by attention-TP logging ranks; with TP8, DP1, ATTN_CP8, attention-TP size is one so all CP ranks are logging ranks. Running derives from local batch.reqs and queue from local waiting_queue. | Do not sum TP/CP rank counters. Near-equality is supporting pressure evidence but does not establish a unique logical-request union. | Evidence + Strong inference |
| lmsysorg/sglang:v0.5.16-cu130 | v0.5.16 | fdebc938f7f4d16fe6b9f55dcd9a767cf0899ea1 | https://github.com/sgl-project/sglang/tree/fdebc938f7f4d16fe6b9f55dcd9a767cf0899ea1 | multinode_server_logs.tar.gz:fingerprint_prefill_w0.json:91; fingerprint_prefill_w1.json:91; fingerprint_decode_w0.json:91; fingerprint_decode_w1.json:91 | Evidence | Public decode startup logs record SGLANG_BUILD_COMMIT=fdebc938f7f4d16fe6b9f55dcd9a767cf0899ea1; the container digest itself remains unrecorded. | decode_dp_attention_metrics | python/sglang/srt/layers/dp_attention.py:293-307; python/sglang/srt/managers/scheduler_components/dp_attn.py:218-360; python/sglang/srt/managers/scheduler_components/metrics_reporter.py:845-906; python/sglang/srt/managers/data_parallel_controller.py:350-425,734-805; python/sglang/srt/observability/metrics_collector.py:1048-1088 | With TP8/DP8/CP1, attention-TP size is one and each physical rank is a DP shard. The data-parallel controller tracks num_running_reqs + num_waiting_reqs per dp_rank, dispatches to a selected DP rank, and reports PD preallocation/transfer queues separately. | Complete same-timeslice DP rank counters can be summed by their named decode-worker scope; generic waiting, PD preallocation, and PD transfer queues remain separate counters. | Validated reconstruction |

### Inference

- Equal-looking aggregate max values are insufficient evidence for a worker sum. The reconstruction therefore tests every same raw start/end timeslice first.

## Prefill TP-rank duplication test

### Evidence

| worker_id | metric | aligned_timeslice_count | all_8_ranks_exactly_equal_ratio | overall_max_rank_difference | timestamp_alignment_status |
| --- | --- | --- | --- | --- | --- |
| 694d9fdfb4d8ee13 | sglang:num_prefill_bootstrap_queue_reqs | 3615 | 1 | 0 | exact_all_rank_timestamp_alignment |
| 694d9fdfb4d8ee13 | sglang:num_prefill_inflight_queue_reqs | 3615 | 0.998617 | 1 | exact_all_rank_timestamp_alignment |
| 694d9fdfb4d8ee13 | sglang:num_queue_reqs | 3615 | 1 | 0 | exact_all_rank_timestamp_alignment |
| 694d9fdfb4d8ee13 | sglang:num_running_reqs | 3615 | 0.99917 | 1 | exact_all_rank_timestamp_alignment |
| 694d9fdfb4d8ee15 | sglang:num_prefill_bootstrap_queue_reqs | 3622 | 0.999724 | 1 | exact_all_rank_timestamp_alignment |
| 694d9fdfb4d8ee15 | sglang:num_prefill_inflight_queue_reqs | 3622 | 0.999172 | 1 | exact_all_rank_timestamp_alignment |
| 694d9fdfb4d8ee15 | sglang:num_queue_reqs | 3622 | 0.999724 | 0.333333 | exact_all_rank_timestamp_alignment |
| 694d9fdfb4d8ee15 | sglang:num_running_reqs | 3622 | 0.999172 | 1 | exact_all_rank_timestamp_alignment |

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

### Strong inference

- Prefill TP/CP rank views are highly synchronized (rank-envelope running maxima 5.0 and 4.0), so multiplying a rank max by eight is invalid. They are useful pressure evidence.

### Unknown

- With CP8, every rank is a metric-emitting attention-TP rank and SGLang counts local `batch.reqs`/`waiting_queue` views. The public export lacks per-rank request IDs, so it cannot prove the unique logical request union for a prefill worker. Worker and cluster unique prefill running/waiting remain Unknown.

| component | metric | max | p50 | p90 | p95 | positive_fraction | status | reconstruction_method | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| prefill | running_requests | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | withheld: CP rank-local counters lack a validated per-worker unique logical-request union | Workers 694d9fdfb4d8ee13, 694d9fdfb4d8ee15; summing rank envelopes or ranks is not valid. |
| prefill | waiting_requests | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | withheld: CP rank-local counters lack a validated per-worker unique logical-request union | Workers 694d9fdfb4d8ee13, 694d9fdfb4d8ee15; summing rank envelopes or ranks is not valid. |

## Decode DP-rank semantics and worker reconstruction

### Evidence

| worker_id | metric | aligned_timeslice_count | all_8_ranks_exactly_equal_ratio | overall_max_rank_difference | timestamp_alignment_status | semantic_status |
| --- | --- | --- | --- | --- | --- | --- |
| 694d9fdfb4d8ee18 | sglang:num_queue_reqs | 3607 | 1 | 0 | exact_all_rank_timestamp_alignment | Validated reconstruction |
| 694d9fdfb4d8ee18 | sglang:num_running_reqs | 3607 | 0.327973 | 2 | exact_all_rank_timestamp_alignment | Validated reconstruction |
| 694d9fdfb4d8ee1b | sglang:num_queue_reqs | 3624 | 1 | 0 | exact_all_rank_timestamp_alignment | Validated reconstruction |
| 694d9fdfb4d8ee1b | sglang:num_running_reqs | 3624 | 0.371965 | 2 | exact_all_rank_timestamp_alignment | Validated reconstruction |

### Validated reconstruction

- Under TP8/DP8/DP attention, one attention-TP rank exists per DP shard. The exact source controller dispatches normal generation requests to one selected DP worker; complete same-timeslice DP grids can therefore be summed **within a decode worker**.

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

## Decode cluster reconstruction

### Validated reconstruction

- Independent decode-worker counters are intersected over their actual endpoint timeslice intervals; no nearest-neighbor matching, forward-fill, or unrelated-timestamp maxima are used. Decode-stage occupancy P90 is **10.0** (Validated reconstruction); its **highest reconstructed 1-s-bin sum is 17.0**, not an instantaneous unique-request maximum. Named generic `num_queue_reqs` cluster max is **0.0**.

| component | metric | worker_a | worker_b | overlap_segment_count | common_worker_overlap_s | common_worker_overlap_fraction_of_profile | max | time_weighted_mean | p50 | p75 | p90 | p95 | p99 | positive_fraction | status | reconstruction_method | decode_waiting_all_zero_raw_rank_series | timeslice_selected_field | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| decode | running_requests | 694d9fdfb4d8ee1b | 694d9fdfb4d8ee18 | 7185 | 3592.85 | 0.987046 | 17 | 5.14057 | 4 | 8 | 10 | 12 | 15 | 0.917739 | Validated reconstruction | sum of validated worker scheduler counts over exact endpoint interval intersections |  | avg | sum of validated worker scheduler counts over exact endpoint interval intersections; DP rank sums are valid only because source topology and complete grids are both verified. selected raw avg field from exported one-second scheduler occupancy bins; not an instantaneous unique-request maximum. |
| decode | waiting_requests | 694d9fdfb4d8ee1b | 694d9fdfb4d8ee18 | 7185 | 3592.85 | 0.987046 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Validated reconstruction | sum of validated worker scheduler counts over exact endpoint interval intersections | True | avg | sum of validated worker scheduler counts over exact endpoint interval intersections; DP rank sums are valid only because source topology and complete grids are both verified. Selected raw field: avg. |
| decode | decode_prealloc_queue_requests | 694d9fdfb4d8ee1b | 694d9fdfb4d8ee18 | 7185 | 3592.85 | 0.987046 | 5 | 0.541441 | 0 | 1 | 2 | 3 | 4 | 0.325967 | Validated reconstruction | sum of validated worker scheduler counts over exact endpoint interval intersections |  | avg | sum of validated worker scheduler counts over exact endpoint interval intersections; DP rank sums are valid only because source topology and complete grids are both verified. Selected raw field: avg. |
| decode | decode_transfer_queue_requests | 694d9fdfb4d8ee1b | 694d9fdfb4d8ee18 | 7185 | 3592.85 | 0.987046 | 4 | 0.143479 | 0 | 0 | 1 | 1 | 2 | 0.123454 | Validated reconstruction | sum of validated worker scheduler counts over exact endpoint interval intersections |  | avg | sum of validated worker scheduler counts over exact endpoint interval intersections; DP rank sums are valid only because source topology and complete grids are both verified. Selected raw field: avg. |

### Decode queues in the same scope

| queue_metric | max | p90 | positive_fraction | status | notes |
| --- | --- | --- | --- | --- | --- |
| Generic SGLang `num_queue_reqs` | 0 | 0 | 0 | Validated reconstruction | sum of validated worker scheduler counts over exact endpoint interval intersections; DP rank sums are valid only because source topology and complete grids are both verified. Selected raw field: avg. |
| Decode preallocation queue | 5 | 2 | 0.325967 | Validated reconstruction | sum of validated worker scheduler counts over exact endpoint interval intersections; DP rank sums are valid only because source topology and complete grids are both verified. Selected raw field: avg. |
| Decode transfer queue | 4 | 1 | 0.123454 | Validated reconstruction | sum of validated worker scheduler counts over exact endpoint interval intersections; DP rank sums are valid only because source topology and complete grids are both verified. Selected raw field: avg. |

### Scope caveat

- `sglang:num_queue_reqs=0` applies to that generic decode scheduler waiting queue. PD-specific preallocation/transfer queue gauges are different counters and are not added to it. A zero generic queue is therefore not evidence that all decode/P-D queues were zero. This is decode-stage scheduler occupancy, not GPU sequences or unique system-wide requests.

## Decode occupancy bin semantics

### Evidence

- Raw field availability and the extractor's selected-field precedence are versioned below. The current reconstruction selected **`avg`** where the audit CSV makes that determinable.

| metric | worker_id | rank | timeslice_count | avg_present_fraction | last_present_fraction | max_present_fraction | value_present_fraction | min_present_fraction | avg_fractional_value_count | avg_differs_from_max_count | selected_field_under_current_parser |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sglang:num_running_reqs | 694d9fdfb4d8ee18 | 0 | 3607 | 1 | 0 | 1 | 0 | 1 | 15 | 15 | avg |
| sglang:num_running_reqs | 694d9fdfb4d8ee18 | 1 | 3607 | 1 | 0 | 1 | 0 | 1 | 26 | 26 | avg |
| sglang:num_running_reqs | 694d9fdfb4d8ee18 | 2 | 3607 | 1 | 0 | 1 | 0 | 1 | 18 | 18 | avg |
| sglang:num_running_reqs | 694d9fdfb4d8ee18 | 3 | 3607 | 1 | 0 | 1 | 0 | 1 | 26 | 26 | avg |
| sglang:num_running_reqs | 694d9fdfb4d8ee18 | 4 | 3607 | 1 | 0 | 1 | 0 | 1 | 17 | 17 | avg |
| sglang:num_running_reqs | 694d9fdfb4d8ee18 | 5 | 3607 | 1 | 0 | 1 | 0 | 1 | 24 | 26 | avg |
| sglang:num_running_reqs | 694d9fdfb4d8ee18 | 6 | 3607 | 1 | 0 | 1 | 0 | 1 | 14 | 14 | avg |
| sglang:num_running_reqs | 694d9fdfb4d8ee18 | 7 | 3607 | 1 | 0 | 1 | 0 | 1 | 28 | 31 | avg |
| sglang:num_running_reqs | 694d9fdfb4d8ee1b | 0 | 3624 | 1 | 0 | 1 | 0 | 1 | 23 | 24 | avg |
| sglang:num_running_reqs | 694d9fdfb4d8ee1b | 1 | 3624 | 1 | 0 | 1 | 0 | 1 | 18 | 18 | avg |
| sglang:num_running_reqs | 694d9fdfb4d8ee1b | 2 | 3624 | 1 | 0 | 1 | 0 | 1 | 24 | 24 | avg |
| sglang:num_running_reqs | 694d9fdfb4d8ee1b | 3 | 3624 | 1 | 0 | 1 | 0 | 1 | 22 | 22 | avg |
| sglang:num_running_reqs | 694d9fdfb4d8ee1b | 4 | 3624 | 1 | 0 | 1 | 0 | 1 | 25 | 25 | avg |
| sglang:num_running_reqs | 694d9fdfb4d8ee1b | 5 | 3624 | 1 | 0 | 1 | 0 | 1 | 23 | 23 | avg |
| sglang:num_running_reqs | 694d9fdfb4d8ee1b | 6 | 3624 | 1 | 0 | 1 | 0 | 1 | 29 | 29 | avg |
| sglang:num_running_reqs | 694d9fdfb4d8ee1b | 7 | 3624 | 1 | 0 | 1 | 0 | 1 | 18 | 18 | avg |

### Field sensitivity

| timeslice_field | availability_status | raw_rank_timeslice_count | raw_field_present_fraction | cluster_overlap_segment_count | cluster_overlap_s | mean | p50 | p90 | p95 | p99 | highest_reconstructed_1s_bin_sum | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| avg | Evidence | 57848 | 1 | 7185 | 3592.85 | 5.140572157500383 | 4.0 | 10.0 | 12.0 | 15.0 | 17.0 | Exact endpoint-interval intersection after validated DP-shard sums. Values are exported one-second occupancy-bin statistics, not instantaneous unique requests. |
| last | Unavailable | 57848 | 0 |  |  | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | The raw field was absent; no fallback value was invented. |
| max | Evidence | 57848 | 1 | 7185 | 3592.85 | 5.1908523229398815 | 4.0 | 11.0 | 12.0 | 15.0 | 17.0 | Exact endpoint-interval intersection after validated DP-shard sums. Values are exported one-second occupancy-bin statistics, not instantaneous unique requests. |

### Worker-timeslice alignment

| worker_a | worker_b | intersection_segment_count | intersection_duration_min_ns | intersection_duration_p50_ns | intersection_duration_p90_ns | intersection_duration_p95_ns | intersection_duration_max_ns | worker_b_minus_a_start_offset_p50_ns | worker_b_minus_a_start_offset_p90_ns | worker_b_minus_a_start_offset_p95_ns | absolute_start_offset_p50_ns | absolute_start_offset_p90_ns | absolute_start_offset_p95_ns | availability_status | method | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 694d9fdfb4d8ee1b | 694d9fdfb4d8ee18 | 7185 | 1.49116e+08 | 8.50466e+08 | 8.50884e+08 | 8.50884e+08 | 8.50884e+08 | -1.49116e+08 | 8.50884e+08 | 8.50884e+08 | 1.49116e+08 | 8.50884e+08 | 8.50884e+08 | Evidence | actual [start_ns,end_ns) endpoint-interval intersection; no nearest-neighbor, fill, or interpolation | Offsets compare the two exported backend timeslice grids, not request timestamps. |

### Interpretation

- The preferred public label is **decode reconstructed occupancy**: a sum over overlapping exported one-second scheduler-occupancy bins. Its highest value is not an instantaneous client/HTTP maximum, not an instantaneous SGLang request count, and not a unique P/D global request count.
- Worker bins are combined only by exact `[start_ns, end_ns)` interval intersection; the alignment table shows the observed scrape-offset and intersection-duration distribution. No nearest-neighbor join, forward-fill, or cross-worker point-sample maximum is used.
- The sensitivity table intentionally reports only raw fields actually present in the export; a missing `last` or `max` field is not silently substituted with another field.

### Unknown

- The public timeslice export does not provide per-bin logical request identities or a request-correlated P/D lifecycle. It cannot turn the highest bin sum into an instantaneous unique-request maximum.

## Dynamo cross-validation

### Evidence

| component | worker_id | dynamo_metric | sglang_metric | common_phase_second_bins | spearman_rho | pearson_r | same_value_fraction | best_lag_seconds | dynamo_positive_sglang_zero_fraction | sglang_positive_dynamo_zero_fraction | rank_or_reconstruction_method | alignment_method | worker_type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| prefill | 694d9fdfb4d8ee13 | dynamo_component_inflight_requests (generate endpoint) | sglang:num_running_reqs supplied comparison series | 3615 | 0.835668 | 0.759775 | 0.667773 | 0 | 0.128077 | 0 | TP0 local CP-rank scheduler view; not worker unique union | same backend endpoint exact exported [start,end) 1-second bins |  |
| prefill | 694d9fdfb4d8ee15 | dynamo_component_inflight_requests (generate endpoint) | sglang:num_running_reqs supplied comparison series | 3622 | 0.775248 | 0.743236 | 0.680287 | 0 | 0.159304 | 0 | TP0 local CP-rank scheduler view; not worker unique union | same backend endpoint exact exported [start,end) 1-second bins |  |
| decode | 694d9fdfb4d8ee18 | dynamo_component_inflight_requests (generate endpoint) | sglang:num_running_reqs supplied comparison series | 3607 | 0.722641 | 0.674845 | 0.336013 | -2 | 0.101192 | 0 | validated sum of complete DP-rank scheduler shards | same backend endpoint exact exported [start,end) 1-second bins |  |
| decode | 694d9fdfb4d8ee1b | dynamo_component_inflight_requests (generate endpoint) | sglang:num_running_reqs supplied comparison series | 3624 | 0.779347 | 0.683684 | 0.415563 | -1 | 0.108444 | 0 | validated sum of complete DP-rank scheduler shards | same backend endpoint exact exported [start,end) 1-second bins |  |
| frontend_or_request_plane |  | dynamo_frontend_inflight_requests |  | 3639 |  |  |  |  |  |  | not directly joined to backend scheduler metrics | independent frontend/request-plane AIPerf 1-second export bins |  |
| frontend_or_request_plane |  | dynamo_frontend_queued_requests |  | 3639 |  |  |  |  |  |  | not directly joined to backend scheduler metrics | independent frontend/request-plane AIPerf 1-second export bins |  |
| frontend_or_request_plane |  | dynamo_frontend_router_queue_pending_isl_tokens |  | 3639 |  |  |  |  |  |  | not directly joined to backend scheduler metrics | independent frontend/request-plane AIPerf 1-second export bins | decode |
| frontend_or_request_plane |  | dynamo_frontend_router_queue_pending_isl_tokens |  | 3639 |  |  |  |  |  |  | not directly joined to backend scheduler metrics | independent frontend/request-plane AIPerf 1-second export bins | prefill |
| frontend_or_request_plane |  | dynamo_frontend_router_queue_pending_requests |  | 3639 |  |  |  |  |  |  | not directly joined to backend scheduler metrics | independent frontend/request-plane AIPerf 1-second export bins | decode |
| frontend_or_request_plane |  | dynamo_frontend_router_queue_pending_requests |  | 3639 |  |  |  |  |  |  | not directly joined to backend scheduler metrics | independent frontend/request-plane AIPerf 1-second export bins | prefill |
| frontend_or_request_plane |  | dynamo_request_plane_inflight_requests |  | 3639 |  |  |  |  |  |  | not directly joined to backend scheduler metrics | independent frontend/request-plane AIPerf 1-second export bins |  |

### Inference

- Dynamo component inflight is correlated with, but demonstrably not identical to, SGLang running. It is a lifecycle cross-check, not a substitute scheduler count. Frontend/request-plane scrape series remain a separate layer.

## Frontend → backend concurrency hierarchy

```text
AgentX root lanes
  → HTTP request-plane inflight
  → Dynamo frontend/router queue
  → Dynamo backend component inflight
  → SGLang scheduler waiting
  → SGLang scheduler running
  → GPU rank / DP shard
```

## Can prefill + decode be added?

### Unknown

- No request-correlated P/D handoff lifecycle proves that prefill and decode counters do not overlap for the same logical request. Prefill unique-worker union is also unavailable. Consequently no P/D sum is reported as backend-stage or unique global running.

## Final reconstructed concurrency table

| metric | value | unit | scope | status | reconstruction_method | evidence | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| http_max_inflight | 11 | requests | HTTP/client [request_start_ns, request_end_ns) profile overlap | Evidence | interval sweep from successful profiling request timestamps | public profile_export + canonical processed request table | Not an SGLang scheduler running-request count. |
| http_time_weighted_mean | 3.968259088179123 | requests | HTTP/client [request_start_ns, request_end_ns) profile overlap | Evidence | interval sweep from successful profiling request timestamps | public profile_export + canonical processed request table | Not an SGLang scheduler running-request count. |
| http_p90 | 7.0 | requests | HTTP/client [request_start_ns, request_end_ns) profile overlap | Evidence | interval sweep from successful profiling request timestamps | public profile_export + canonical processed request table | Not an SGLang scheduler running-request count. |
| http_p95 | 8.0 | requests | HTTP/client [request_start_ns, request_end_ns) profile overlap | Evidence | interval sweep from successful profiling request timestamps | public profile_export + canonical processed request table | Not an SGLang scheduler running-request count. |
| prefill_worker_0_max_running | Unknown | requests | unique logical requests at one CP8 prefill worker | Unknown | withheld: TP/CP rank-local views lack request-ID union | raw 1-second rank grids plus SGLang CP8 source topology | The rank envelope is recorded separately; neither rank sum nor a unique worker count is proven. |
| prefill_worker_0_rank_envelope_max_running | 5.0 | rank-local counter | rank-envelope running requests | Strong inference | max over per-timeslice TP/CP rank envelope; no sum | raw 1-second prefill rank series | Pressure evidence only, not a unique logical worker request count. |
| prefill_worker_0_max_waiting | Unknown | requests | unique logical requests at one CP8 prefill worker | Unknown | withheld: TP/CP rank-local views lack request-ID union | raw 1-second rank grids plus SGLang CP8 source topology | The rank envelope is recorded separately; neither rank sum nor a unique worker count is proven. |
| prefill_worker_0_rank_envelope_max_waiting | 5.0 | rank-local counter | rank-envelope queue requests | Strong inference | max over per-timeslice TP/CP rank envelope; no sum | raw 1-second prefill rank series | Pressure evidence only, not a unique logical worker request count. |
| prefill_worker_1_max_running | Unknown | requests | unique logical requests at one CP8 prefill worker | Unknown | withheld: TP/CP rank-local views lack request-ID union | raw 1-second rank grids plus SGLang CP8 source topology | The rank envelope is recorded separately; neither rank sum nor a unique worker count is proven. |
| prefill_worker_1_rank_envelope_max_running | 4.0 | rank-local counter | rank-envelope running requests | Strong inference | max over per-timeslice TP/CP rank envelope; no sum | raw 1-second prefill rank series | Pressure evidence only, not a unique logical worker request count. |
| prefill_worker_1_max_waiting | Unknown | requests | unique logical requests at one CP8 prefill worker | Unknown | withheld: TP/CP rank-local views lack request-ID union | raw 1-second rank grids plus SGLang CP8 source topology | The rank envelope is recorded separately; neither rank sum nor a unique worker count is proven. |
| prefill_worker_1_rank_envelope_max_waiting | 5.0 | rank-local counter | rank-envelope queue requests | Strong inference | max over per-timeslice TP/CP rank envelope; no sum | raw 1-second prefill rank series | Pressure evidence only, not a unique logical worker request count. |
| prefill_cluster_max_running | Unknown | requests | two prefill workers' unique logical request union | Unknown | withheld: each CP8 worker unique union is unknown | prefill rank validation | Do not sum TP ranks or strong-inference rank envelopes across workers. |
| prefill_cluster_p50_running | Unknown | requests | two prefill workers' unique logical request union | Unknown | withheld: each CP8 worker unique union is unknown | prefill rank validation | Unknown is intentionally not converted to zero. |
| prefill_cluster_p90_running | Unknown | requests | two prefill workers' unique logical request union | Unknown | withheld: each CP8 worker unique union is unknown | prefill rank validation | Unknown is intentionally not converted to zero. |
| prefill_cluster_p95_running | Unknown | requests | two prefill workers' unique logical request union | Unknown | withheld: each CP8 worker unique union is unknown | prefill rank validation | Unknown is intentionally not converted to zero. |
| prefill_cluster_max_waiting | Unknown | requests | two prefill workers' unique logical request union | Unknown | withheld: each CP8 worker unique union is unknown | prefill rank validation | Do not sum TP ranks or strong-inference rank envelopes across workers. |
| prefill_cluster_p50_waiting | Unknown | requests | two prefill workers' unique logical request union | Unknown | withheld: each CP8 worker unique union is unknown | prefill rank validation | Unknown is intentionally not converted to zero. |
| prefill_cluster_p90_waiting | Unknown | requests | two prefill workers' unique logical request union | Unknown | withheld: each CP8 worker unique union is unknown | prefill rank validation | Unknown is intentionally not converted to zero. |
| prefill_cluster_p95_waiting | Unknown | requests | two prefill workers' unique logical request union | Unknown | withheld: each CP8 worker unique union is unknown | prefill rank validation | Unknown is intentionally not converted to zero. |
| prefill_cluster_waiting_positive_fraction | Unknown | fraction | two prefill workers' unique logical request union | Unknown | withheld: CP-rank queue counters cannot establish a unique worker union | prefill rank validation | Rank-local positive queue evidence exists but cluster positive fraction is not reconstructable. |
| decode_worker_0_max_running | 9.0 | requests | one decode worker, sum of complete DP8 rank-local scheduler shards | Validated reconstruction | sum of validated independent rank-local scheduler shards | raw 1-second decode DP rank grids + SGLang DP attention source semantics | A logical request is assigned to one DP shard under the validated source mapping. |
| decode_worker_0_max_waiting | 0.0 | requests | one decode worker, sum of complete DP8 rank-local scheduler shards | Validated reconstruction | sum of validated independent rank-local scheduler shards | raw 1-second decode DP rank grids + SGLang DP attention source semantics | A logical request is assigned to one DP shard under the validated source mapping. |
| decode_worker_1_max_running | 10.0 | requests | one decode worker, sum of complete DP8 rank-local scheduler shards | Validated reconstruction | sum of validated independent rank-local scheduler shards | raw 1-second decode DP rank grids + SGLang DP attention source semantics | A logical request is assigned to one DP shard under the validated source mapping. |
| decode_worker_1_max_waiting | 0.0 | requests | one decode worker, sum of complete DP8 rank-local scheduler shards | Validated reconstruction | sum of validated independent rank-local scheduler shards | raw 1-second decode DP rank grids + SGLang DP attention source semantics | A logical request is assigned to one DP shard under the validated source mapping. |
| decode_cluster_max_running | 17.0 | requests | two decode workers, exact intersections of exported one-second scheduler occupancy bins | Validated reconstruction | sum of validated worker scheduler counts over exact endpoint interval intersections | raw decode DP grids, validated worker sums, exact endpoint-interval intersection | Highest reconstructed sum across exported one-second scheduler occupancy bins. Not an instantaneous unique-request maximum. |
| decode_cluster_p50_running | 4.0 | requests | two decode workers, exact intersections of exported one-second scheduler occupancy bins | Validated reconstruction | sum of validated worker scheduler counts over exact endpoint interval intersections | raw decode DP grids, validated worker sums, exact endpoint-interval intersection | Time-weighted distribution of reconstructed exported one-second scheduler occupancy-bin sums; not instantaneous unique-request counts. |
| decode_cluster_p90_running | 10.0 | requests | two decode workers, exact intersections of exported one-second scheduler occupancy bins | Validated reconstruction | sum of validated worker scheduler counts over exact endpoint interval intersections | raw decode DP grids, validated worker sums, exact endpoint-interval intersection | Time-weighted distribution of reconstructed exported one-second scheduler occupancy-bin sums; not instantaneous unique-request counts. |
| decode_cluster_p95_running | 12.0 | requests | two decode workers, exact intersections of exported one-second scheduler occupancy bins | Validated reconstruction | sum of validated worker scheduler counts over exact endpoint interval intersections | raw decode DP grids, validated worker sums, exact endpoint-interval intersection | Time-weighted distribution of reconstructed exported one-second scheduler occupancy-bin sums; not instantaneous unique-request counts. |
| decode_cluster_max_waiting | 0.0 | requests | two decode workers, exact intersections of exported one-second scheduler occupancy bins | Validated reconstruction | sum of validated worker scheduler counts over exact endpoint interval intersections | raw decode DP grids, validated worker sums, exact endpoint-interval intersection | Generic SGLang decode waiting queue only; this does not assert that all P/D-specific decode queues were zero. |

- Table is truncated to 30 rows.

## Direct answers

### Evidence

- **Q1:** Prefill TP8 `num_running_reqs` is neither eight independently summable counts nor a proven single duplicated worker gauge; it is CP-rank local scheduler evidence.
- **Q4:** Decode DP rank counters are independent scheduler shards for this TP8/DP8 DP-attention runtime.
- **Q5:** Decode worker and decode-stage cluster occupancy can be summed in their stated scope; P90=10.0 and highest reconstructed 1-s-bin sum=17.0.
- **Q6:** Every observed decode `sglang:num_queue_reqs` raw DP-rank sample is zero; this does not cover separate PD-specific queues.
- **Q7:** The highest confirmed backend scope is decode-stage cluster scheduler occupancy. HTTP max remains a separate 11-request client interval overlap.

### Unknown

- **Q2/Q3:** Prefill worker A/B and prefill-cluster unique running/waiting are unknown because rank-local CP views lack request-ID union.
- **Q8:** Statement C is closest: decode worker/cluster values are reconstructable in their scope, while unique P/D system-global running is Unknown. The old 5/2 rank-series values were not global counts; the reconstructed decode cluster does not make a prefill+decode global total valid.

## Implication for local vs InferX comparison

- Compare a local global scheduler counter to the public HTTP overlap only as a different layer, and to the public decode cluster only when the local metric is explicitly decode-stage scheduler occupancy. Do not substitute the public prefill rank envelope for a global prefill count.

## Files

1. `../processed/c8_cluster_scheduler_reconstruction.csv`
2. `../processed/c8_scheduler_rank_semantics_validation.csv`
3. `../processed/c8_prefill_worker_scheduler_summary.csv`
4. `../processed/c8_prefill_cluster_scheduler_summary.csv`
5. `../processed/c8_decode_rank_scheduler_summary.csv`
6. `../processed/c8_decode_worker_scheduler_summary.csv`
7. `../processed/c8_decode_cluster_scheduler_summary.csv`
8. `../processed/c8_decode_timeslice_field_semantics.csv`
9. `../processed/c8_decode_cluster_field_sensitivity.csv`
10. `../processed/c8_decode_timeslice_alignment_summary.csv`
11. `../processed/c8_dynamo_sglang_concurrency_crosscheck.csv`
12. `../processed/c8_scheduler_source_semantics.csv`
13. `../figures/c8_prefill_worker_running_waiting.png`
14. `../figures/c8_decode_worker_running_waiting.png`
15. `../figures/c8_frontend_backend_concurrency_timeline.png`
