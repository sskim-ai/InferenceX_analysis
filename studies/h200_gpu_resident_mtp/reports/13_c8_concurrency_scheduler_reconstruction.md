# 13. c8 concurrency and scheduler reconstruction

## Scope

### Evidence

- This report uses only public run 31235207041 c8 profiling records, the public AIPerf server-metrics export, and public frontend/server logs. It contains no local or internal-server measurements.
- The interval population is the 957 successful profiling requests with valid `[request_start_ns, request_end_ns)` endpoints.

### Inference

- These sources are sufficient to reconstruct client/profile observed offered-load overlap and some rank-series scheduler counters, but not a single unified backend execution timeline.

### Unknown

- The public package does not expose a complete request-correlated scheduler lifecycle from acceptance through prefill, decode admission, first token, and completion.

## Definitions

### Evidence

- **AgentX root-trajectory lane concurrency:** c8 is the configured count of eight root trajectory lanes; it is a workload-generator setting.
- **HTTP/client in-flight:** overlapping profile request intervals use `[start, end)` semantics. At an equal timestamp, end events are processed before start events; a start-context value includes all requests that start at that exact timestamp.
- **SGLang scheduler running/waiting:** explicit `sglang:*` values are aggregate samples in endpoint/rank-export series. Prefill TP/CP counters are not summed into an unsupported worker or cluster total. A later source/topology validation permits a limited decode DP-shard reconstruction only; see Report 15.
- **Configured limits:** prefill `max_running_requests=32` and decode `max_running_requests=200` are capacity settings, not measurements of runtime running requests.

### Unknown

- Neither a profile interval nor a Dynamo selected-worker routing ID proves GPU affinity, backend batch membership, or a number of concurrent GPU sequences.

## HTTP offered-load reconstruction

### Evidence

| valid_interval_request_count | invalid_interval_request_count | observation_span_s | max_inflight | time_weighted_mean_inflight | time_weighted_p50_inflight | time_weighted_p75_inflight | time_weighted_p90_inflight | time_weighted_p95_inflight | time_weighted_p99_inflight | max_root_inflight | max_subagent_inflight | fraction_time_inflight_ge_8 | fraction_time_inflight_ge_12 | request_start_sampled_p50_inflight | request_start_sampled_p90_inflight | interval_semantics | same_timestamp_policy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 957 | 0 | 3613.67 | 11 | 3.96826 | 4 | 5 | 7 | 8 | 9 | 7 | 7 | 0.0526486 | 0 | 5 | 8 | [request_start_ns, request_end_ns) | all end events before starts; start context includes all same-timestamp starts |

| metric | value | status | evidence_scope | notes |
| --- | --- | --- | --- | --- |
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

- The reviewable event timeline is `../processed/c8_http_inflight_timeline.csv`; the request-start context for all 957 profile rows is `../processed/c8_requests_with_inflight_context.csv`.
- The visual timeline is `../figures/c8_http_inflight_timeline.png`.

### Inference

- The observed HTTP/client offered load is modest for much of the measured span (time-weighted mean 3.968259088179123, P90 7.0, P95 8.0), but it is not synonymous with a scheduler running count.

### Unknown

- Profile endpoints do not identify how much of an interval was frontend routing, queueing, prefill, KV transfer, decode, or client/network work.

## Root vs subagent fan-out

### Evidence

| scope | source_branch_type | request_count | ttft_median_ms | ttft_p90_ms | e2e_median_ms | e2e_p90_ms | weighted_itl_ms | weighted_decode_tps | system_inflight_at_start_median | system_inflight_at_start_p90 | metric_scope |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_c8 | root | 518 | 2194.89 | 20816.7 | 10146.4 | 40657.5 | 10.7587 | 92.9482 | 4 | 7 | source branch origin; not backend worker/GPU affinity |
| all_c8 | subagent | 439 | 1195.63 | 10757.9 | 5590.29 | 25176.3 | 10.9173 | 91.5975 | 5 | 8 | source branch origin; not backend worker/GPU affinity |
| id03_c8 | root | 9 | 1155.27 | 3317.08 | 4624.45 | 44713.3 | 10.5072 | 95.1732 | 3 | 4.4 | source branch origin; not backend worker/GPU affinity |
| id03_c8 | subagent | 110 | 1071.77 | 3316.38 | 3503.7 | 7217.62 | 11.2503 | 88.8866 | 5 | 8 | source branch origin; not backend worker/GPU affinity |

- Maximum simultaneous HTTP/profile intervals were root=7 and subagent=7. A root/subagent label comes from source-workload branch origin, not a backend worker assignment.

### Inference

- Source subagent fan-out can make the request-plane overlap differ from the configured root-lane count even when the benchmark has only eight root trajectories.

### Unknown

- The branch label alone cannot establish whether a branch was queued, batched, or served by a specific H200 GPU.

## ID03 load context

### Evidence

| predictor | outcome | sample_count | spearman_rho | p_value | classification | notes |
| --- | --- | --- | --- | --- | --- | --- |
| system_inflight_at_start | ttft_ms | 119 | 0.0239237 | 0.796207 | Evidence | Spearman on ID03 public c8 profile rows; HTTP interval overlap at request start, not an SGLang scheduler counter or causal estimate |
| system_inflight_at_start | e2e_ms | 119 | 0.0220144 | 0.812158 | Evidence | Spearman on ID03 public c8 profile rows; HTTP interval overlap at request start, not an SGLang scheduler counter or causal estimate |
| system_inflight_at_start | itl_ms | 119 | 0.514686 | 2.12318e-09 | Evidence | Spearman on ID03 public c8 profile rows; HTTP interval overlap at request start, not an SGLang scheduler counter or causal estimate |
| root_inflight_at_start | ttft_ms | 119 | -0.129642 | 0.159949 | Evidence | Spearman on ID03 public c8 profile rows; HTTP interval overlap at request start, not an SGLang scheduler counter or causal estimate |
| subagent_inflight_at_start | ttft_ms | 119 | 0.0634474 | 0.493019 | Evidence | Spearman on ID03 public c8 profile rows; HTTP interval overlap at request start, not an SGLang scheduler counter or causal estimate |

| inflight_bucket | request_count | ttft_median_ms | ttft_p90_ms | e2e_median_ms | itl_sample_count | weighted_itl_ms | weighted_decode_tps | metric_scope |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1-4 | 41 | 1179.59 | 2978.9 | 3370.78 | 41 | 10.7114 | 93.3587 | ID03 public c8; request-start HTTP overlap bucket, not scheduler running |
| 5-8 | 68 | 1044.92 | 3560.66 | 3640.56 | 68 | 11.4034 | 87.6928 | ID03 public c8; request-start HTTP overlap bucket, not scheduler running |
| 9-12 | 10 | 1033.71 | 2597.2 | 3621.86 | 10 | 11.5278 | 86.7469 | ID03 public c8; request-start HTTP overlap bucket, not scheduler running |

- All 119 public c8 ID03 profile rows are versioned with system/root/subagent request-start overlap in `../processed/id03_c8_with_system_load.csv`. The scatter plot is `../figures/id03_ttft_vs_system_inflight.png`.
- `../processed/id03_c8_backend_pressure.csv` adds exact Dynamo selected-worker routing and any matched router long-wait checkpoint. It does not add request-level SGLang running/waiting or GPU-affinity evidence.
- The displayed Spearman associations use HTTP interval overlap at request start—not a scheduler running counter—and do not adjust for request shape, source branch, cache state, route, or MTP state.

### Inference

- For ID03 c8, TTFT has no material monotonic association with this offered-load proxy in the observed sample (Spearman ρ=0.0239237, p=0.796207, n=119). This is descriptive, not a causal queueing test.

### Unknown

- A weak TTFT association at this profile-interval granularity cannot rule out queueing or admission effects inside an individual request.

## Prefill scheduler evidence

### Evidence

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

- Explicit rank-export series show a maximum observed prefill `num_running_reqs` of 5.0 and `num_queue_reqs` of 5.0; these are not summed across ranks.
- `../processed/c8_prefill_scheduler_timeline.csv` is event/scrape sampled. Its values are not treated as a time-weighted worker total.

### Inference

- Nonzero prefill queue samples demonstrate some observed waiting at this rank-series scope, but do not prove saturation of a prefill worker or the two-worker system.

### Unknown

- A precise per-worker prefill batch size, token load, and active-request total cannot be recovered by summing the available rank series.

## Decode scheduler evidence

### Evidence

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

- This report's rank-series inventory shows a maximum observed decode `num_running_reqs` of 2.0 and `num_queue_reqs` of 0.0; those inventory maxima are not a worker total. Report 15 subsequently validates a DP-shard sum within a decode worker and over two decode endpoints, with scope guards.
- `../processed/c8_decode_scheduler_timeline.csv` is event/scrape sampled rather than a request-correlated execution timeline.

### Inference

- Even after the scoped decode DP-shard reconstruction, the public evidence does not show a unique P/D global running-request total or the batch pressure experienced by any one request.

### Unknown

- Per-request decode admission time and unique cross-stage P/D running/waiting remain unknown from the public exports.

## Routing and queue checkpoints

### Evidence

| component | worker_id | request_count | percentage_of_profiled_requests | root_id_count | max_selected_http_interval_overlap | time_weighted_mean_selected_http_interval_overlap | routing_join_status | scope_note | classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| prefill | 7587896730349792787 | 476 | 0.497388 | 14 | 8 | 2.13795 | exact x_request_id -> frontend completion | Dynamo selected-worker routing. Interval overlap is not backend scheduler running or GPU affinity. | Evidence |
| prefill | 7587896730349792789 | 481 | 0.502612 | 14 | 8 | 1.87464 | exact x_request_id -> frontend completion | Dynamo selected-worker routing. Interval overlap is not backend scheduler running or GPU affinity. | Evidence |
| decode | 7587896730349792792 | 487 | 0.508882 | 14 | 7 | 2.23679 | exact x_request_id -> frontend completion | Dynamo selected-worker routing. Interval overlap is not backend scheduler running or GPU affinity. | Evidence |
| decode | 7587896730349792795 | 470 | 0.491118 | 14 | 7 | 1.74498 | exact x_request_id -> frontend completion | Dynamo selected-worker routing. Interval overlap is not backend scheduler running or GPU affinity. | Evidence |

| profile_request_count_with_checkpoint | checkpoint_event_count | checkpoint_wait_ms_median | checkpoint_wait_ms_p90 | checkpoint_wait_ms_max | classification | scope_note |
| --- | --- | --- | --- | --- | --- | --- |
| 18 | 18 | 16374.5 | 25483.6 | 27520 | Evidence | Dynamo KV-router long-wait refresh checkpoint; not final end-to-end H200 scheduler queue time. |

| component | worker | candidate_metric_name | value | metric_scope_interpretation | classification |
| --- | --- | --- | --- | --- | --- |
| prefill | 694d9fdfb4d8ee15 | sglang:num_decode_prealloc_queue_reqs | 0 | The number of requests in the decode prealloc queue. | Evidence |
| prefill | 694d9fdfb4d8ee15 | sglang:num_decode_prealloc_queue_reqs | 0 | The number of requests in the decode prealloc queue. | Evidence |
| prefill | 694d9fdfb4d8ee15 | sglang:num_decode_prealloc_queue_reqs | 0 | The number of requests in the decode prealloc queue. | Evidence |
| prefill | 694d9fdfb4d8ee15 | sglang:num_decode_prealloc_queue_reqs | 0 | The number of requests in the decode prealloc queue. | Evidence |
| prefill | 694d9fdfb4d8ee15 | sglang:num_decode_prealloc_queue_reqs | 0 | The number of requests in the decode prealloc queue. | Evidence |
| prefill | 694d9fdfb4d8ee15 | sglang:num_decode_prealloc_queue_reqs | 0 | The number of requests in the decode prealloc queue. | Evidence |
| prefill | 694d9fdfb4d8ee15 | sglang:num_decode_prealloc_queue_reqs | 0 | The number of requests in the decode prealloc queue. | Evidence |
| prefill | 694d9fdfb4d8ee15 | sglang:num_decode_prealloc_queue_reqs | 0 | The number of requests in the decode prealloc queue. | Evidence |
| prefill | 694d9fdfb4d8ee13 | sglang:num_decode_prealloc_queue_reqs | 0 | The number of requests in the decode prealloc queue. | Evidence |
| prefill | 694d9fdfb4d8ee13 | sglang:num_decode_prealloc_queue_reqs | 0 | The number of requests in the decode prealloc queue. | Evidence |
| prefill | 694d9fdfb4d8ee13 | sglang:num_decode_prealloc_queue_reqs | 0 | The number of requests in the decode prealloc queue. | Evidence |
| prefill | 694d9fdfb4d8ee13 | sglang:num_decode_prealloc_queue_reqs | 0 | The number of requests in the decode prealloc queue. | Evidence |
| prefill | 694d9fdfb4d8ee13 | sglang:num_decode_prealloc_queue_reqs | 0 | The number of requests in the decode prealloc queue. | Evidence |
| prefill | 694d9fdfb4d8ee13 | sglang:num_decode_prealloc_queue_reqs | 0 | The number of requests in the decode prealloc queue. | Evidence |
| prefill | 694d9fdfb4d8ee13 | sglang:num_decode_prealloc_queue_reqs | 0 | The number of requests in the decode prealloc queue. | Evidence |
| prefill | 694d9fdfb4d8ee13 | sglang:num_decode_prealloc_queue_reqs | 0 | The number of requests in the decode prealloc queue. | Evidence |
| prefill | 694d9fdfb4d8ee15 | sglang:num_decode_transfer_queue_reqs | 0 | The number of requests in the decode transfer queue. | Evidence |
| prefill | 694d9fdfb4d8ee15 | sglang:num_decode_transfer_queue_reqs | 0 | The number of requests in the decode transfer queue. | Evidence |
| prefill | 694d9fdfb4d8ee15 | sglang:num_decode_transfer_queue_reqs | 0 | The number of requests in the decode transfer queue. | Evidence |
| prefill | 694d9fdfb4d8ee15 | sglang:num_decode_transfer_queue_reqs | 0 | The number of requests in the decode transfer queue. | Evidence |
| prefill | 694d9fdfb4d8ee15 | sglang:num_decode_transfer_queue_reqs | 0 | The number of requests in the decode transfer queue. | Evidence |
| prefill | 694d9fdfb4d8ee15 | sglang:num_decode_transfer_queue_reqs | 0 | The number of requests in the decode transfer queue. | Evidence |
| prefill | 694d9fdfb4d8ee15 | sglang:num_decode_transfer_queue_reqs | 0 | The number of requests in the decode transfer queue. | Evidence |
| prefill | 694d9fdfb4d8ee15 | sglang:num_decode_transfer_queue_reqs | 0 | The number of requests in the decode transfer queue. | Evidence |
| prefill | 694d9fdfb4d8ee13 | sglang:num_decode_transfer_queue_reqs | 0 | The number of requests in the decode transfer queue. | Evidence |
| prefill | 694d9fdfb4d8ee13 | sglang:num_decode_transfer_queue_reqs | 0 | The number of requests in the decode transfer queue. | Evidence |
| prefill | 694d9fdfb4d8ee13 | sglang:num_decode_transfer_queue_reqs | 0 | The number of requests in the decode transfer queue. | Evidence |
| prefill | 694d9fdfb4d8ee13 | sglang:num_decode_transfer_queue_reqs | 0 | The number of requests in the decode transfer queue. | Evidence |
| prefill | 694d9fdfb4d8ee13 | sglang:num_decode_transfer_queue_reqs | 0 | The number of requests in the decode transfer queue. | Evidence |
| prefill | 694d9fdfb4d8ee13 | sglang:num_decode_transfer_queue_reqs | 0 | The number of requests in the decode transfer queue. | Evidence |

- Table is truncated to 30 rows.

- Dynamo routing was exactly joined from public profile `x_request_id` to frontend completion events for the profile rows. It identifies selected logical workers only.
- The queue checkpoint table contains a limited set of long-wait refresh events and is not a final per-request scheduler queue-time decomposition.

### Inference

- Routing balance can be reviewed at a Dynamo logical-worker level, while the corresponding backend GPU affinity and per-worker scheduler pressure remain separate questions.

### Unknown

- A request-correlated `accepted → queued → running → first token` chain is unavailable, so queue components cannot be subtracted from TTFT.

## What c8 actually means

### Evidence

| metric | value | status | evidence_scope | notes |
| --- | --- | --- | --- | --- |
| agentx_root_concurrency_configured | 8 | Evidence | AIPerf c8 command / trajectory lanes | Configured root-trajectory lane count; not HTTP or scheduler running count. |
| prefill_configured_max_running | 32 | Evidence | public startup ServerArgs / runtime evidence | Configured capacity, not observed runtime running-request count. |
| decode_configured_max_running | 200 | Evidence | public startup ServerArgs / runtime evidence | Configured capacity, not observed runtime running-request count. |
| prefill_observed_max_running | 5.0 | Evidence | AIPerf profiling-window 1-second server-metrics timeslices; maximum across endpoint/rank-export series | Rank-export series are not summed to a worker or cluster total; this is not a global scheduler total. |
| prefill_observed_max_waiting | 5.0 | Evidence | AIPerf profiling-window 1-second server-metrics timeslices; maximum across endpoint/rank-export series | Rank-export series are not summed to a worker or cluster total; this is not a global scheduler total. |
| decode_observed_max_running | 2.0 | Evidence | AIPerf profiling-window 1-second server-metrics timeslices; maximum across endpoint/rank-export series | Rank-export series are not summed to a worker or cluster total; this is not a global scheduler total. |
| decode_observed_max_waiting | 0.0 | Evidence | AIPerf profiling-window 1-second server-metrics timeslices; maximum across endpoint/rank-export series | Rank-export series are not summed to a worker or cluster total; this is not a global scheduler total. |
| routing_exact_profile_join_count | 957 | Evidence | raw profile x_request_id -> frontend request-completed log | Dynamo worker routing only, not GPU affinity. |

### Inference

- `c8` should be read first as configured AgentX root-trajectory lane concurrency. The other observed counters provide complementary scopes rather than a conversion from lanes to backend running requests.

### Unknown

- No evidence establishes that c8 equals eight simultaneous HTTP requests, eight SGLang running requests, eight requests per worker, or eight GPU sequences.

## Direct answers to the reconstruction questions

### Evidence

- **Question A — Does AgentX c8 imply only 8 simultaneous HTTP requests? No.** The configured root-lane count is eight, while the observed profile-interval maximum is 11.
- **Question B — Maximum observed HTTP in-flight during profiling:** 11. The time-weighted mean/P90/P95 are 3.968259088179123/7.0/8.0.
- **Question C — Was scheduler saturation observed? Unknown at the global P/D scope.** Report 15 validates decode DP-shard worker/cluster occupancy, but prefill unique-worker union and a global saturation fraction are still unavailable.
- **Question D — Can H200 queue time be separated from TTFT? No complete request-level decomposition.** The public evidence has `aggregate_scheduler_histogram_and_router_checkpoints_available` plus limited router checkpoints, not a full lifecycle join.
- **Question E — Is ID03 TTFT associated with offered load?** The unadjusted c8 interval-overlap Spearman result is ρ=0.0239237, p=0.796207, n=119; its bucket values are in `../processed/id03_c8_load_buckets.csv`.
- **Question F — Can a future external comparison distinguish queueing from execution-side pre-first-token latency? Partly.** This public reference supplies HTTP overlap, rank-series scheduler summaries, routing, and limited checkpoints; an external system must additionally expose a request-correlated lifecycle to make the separation.

### Inference

- The rank-series maxima below are useful pressure evidence, but neither nonzero waiting nor a low HTTP interval count alone explains the public c8 TTFT distribution or proves high backend admission capacity. Both offered load and execution-side mechanisms may contribute.

### Unknown

- The evidence cannot apportion low TTFT between low offered load and backend admission capacity, or quantify a per-request H200 scheduler queue time.

## Files for a subsequent public/external comparison

1. `../processed/c8_concurrency_reconstruction_summary.csv`
2. `../processed/c8_http_concurrency_summary.csv`
3. `../processed/c8_requests_with_inflight_context.csv`
4. `../processed/id03_c8_with_system_load.csv`
5. `../processed/id03_c8_backend_pressure.csv`
6. `../processed/id03_c8_load_latency_relationship.csv`
7. `../processed/id03_c8_load_buckets.csv`
8. `../processed/c8_scheduler_metric_inventory.csv`
9. `../processed/c8_prefill_scheduler_summary.csv`
10. `../processed/c8_decode_scheduler_summary.csv`
11. `../processed/c8_backend_worker_routing_summary.csv`
12. `../processed/c8_router_queue_wait_checkpoint_summary.csv`
13. `../figures/c8_http_inflight_timeline.png`
14. `../figures/id03_ttft_vs_system_inflight.png`
