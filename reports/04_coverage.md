# 04. Coverage by concurrency

## Evidence

- **Evidence:** conc1–8 전체에서 한 번 이상 profiling으로 관측된 source root ID는 `11/393` (2.8%)이다.
- **Evidence:** 아래 표의 `root_match_rate`는 해당 concurrency에서 관측된 H200 root ID 중 source ID와 일치한 비율이며, source universe 전체 coverage와는 다른 분모다. `replay_*`는 replay conversation-ID suffix taxonomy, `source_origin_*`는 mapped source trace의 nested-origin taxonomy다.

| concurrency | profiled_request_count | distinct_root_ids | matched_root_ids | root_match_rate | replay_root_request_count | replay_nonroot_branch_request_count | replay_unknown_branch_request_count | source_origin_root_request_count | source_origin_subagent_request_count | source_origin_unknown_branch_request_count | total_input_tokens | total_output_tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 355 | 2 | 2 | 1 | 98 | 257 | 0 | 200 | 155 | 0 | 1.1688e+07 | 127262 |
| 2 | 395 | 4 | 4 | 1 | 164 | 231 | 0 | 347 | 48 | 0 | 9.40309e+06 | 125538 |
| 3 | 455 | 7 | 7 | 1 | 204 | 251 | 0 | 399 | 56 | 0 | 1.17988e+07 | 159005 |
| 4 | 379 | 8 | 8 | 1 | 209 | 170 | 0 | 239 | 140 | 0 | 1.79037e+07 | 243209 |
| 5 | 250 | 7 | 7 | 1 | 110 | 140 | 0 | 163 | 87 | 0 | 9.61085e+06 | 108877 |
| 6 | 197 | 9 | 9 | 1 | 89 | 108 | 0 | 108 | 89 | 0 | 7.22273e+06 | 112007 |
| 7 | 241 | 9 | 9 | 1 | 65 | 176 | 0 | 94 | 147 | 0 | 1.07041e+07 | 124318 |
| 8 | 219 | 11 | 11 | 1 | 78 | 141 | 0 | 110 | 109 | 0 | 1.04943e+07 | 84618 |
- **Evidence:** Observed vs never-observed source workload shape (source medians; this is a coverage-bias diagnostic, not a target-model comparison):

| concurrency | observation_group | source_trace_count | source_request_count_total_median | source_recorded_span_s_median | source_total_input_tokens_median | source_total_output_tokens_median | source_subagent_count_median | source_max_input_tokens_median |
|---|---|---|---|---|---|---|---|---|
| 1 | observed | 2 | 349.5 | 118459 | 8.89374e+07 | 496482 | 5 | 600384 |
| 1 | never_observed | 391 | 81 | 10092.5 | 1.1172e+07 | 95178 | 0 | 223360 |
| 2 | observed | 4 | 349.5 | 81614 | 8.89374e+07 | 496482 | 7 | 600384 |
| 2 | never_observed | 389 | 81 | 10092.5 | 1.117e+07 | 93881 | 0 | 223360 |
| 3 | observed | 7 | 107 | 73578.8 | 1.18433e+07 | 169943 | 3 | 315648 |
| 3 | never_observed | 386 | 83.5 | 10012 | 1.11857e+07 | 95602.5 | 0 | 224000 |
| 4 | observed | 8 | 152.5 | 87523.2 | 2.40613e+07 | 177604 | 3.5 | 355936 |
| 4 | never_observed | 385 | 81 | 9931.59 | 1.1172e+07 | 95178 | 0 | 223360 |
| 5 | observed | 7 | 198 | 17764.3 | 3.62794e+07 | 185265 | 4 | 396224 |
| 5 | never_observed | 386 | 81 | 10106.9 | 1.1171e+07 | 94529.5 | 0 | 223360 |
| 6 | observed | 9 | 107 | 17764.3 | 1.18433e+07 | 169943 | 3 | 315648 |
| 6 | never_observed | 384 | 83.5 | 10106.9 | 1.11857e+07 | 95602.5 | 0 | 224000 |
| 7 | observed | 9 | 107 | 17764.3 | 1.18433e+07 | 169943 | 3 | 315648 |
| 7 | never_observed | 384 | 83.5 | 10106.9 | 1.11857e+07 | 95602.5 | 0 | 224000 |
| 8 | observed | 11 | 73 | 17764.3 | 4.54099e+06 | 61035 | 3 | 180544 |
| 8 | never_observed | 382 | 86 | 10106.9 | 1.12142e+07 | 96570 | 0 | 225472 |
- **Evidence:** Source workload-model-label composition by observation group (labels are source provenance, not target-model classes):

| concurrency | observation_group | source_model | source_trace_count_with_model | source_trace_count_in_group | source_model_trace_share |
|---|---|---|---|---|---|
| 1 | observed | claude-haiku-4-5-20251001 | 1 | 2 | 0.5 |
| 1 | observed | claude-opus-4-7 | 1 | 2 | 0.5 |
| 1 | observed | claude-opus-4-8 | 2 | 2 | 1 |
| 1 | never_observed | claude-fable-5 | 101 | 391 | 0.258312 |
| 1 | never_observed | claude-haiku-4-5-20251001 | 130 | 391 | 0.332481 |
| 1 | never_observed | claude-opus-4-6 | 27 | 391 | 0.0690537 |
| 1 | never_observed | claude-opus-4-7 | 26 | 391 | 0.0664962 |
| 1 | never_observed | claude-opus-4-8 | 312 | 391 | 0.797954 |
| 1 | never_observed | claude-sonnet-4-5 | 4 | 391 | 0.0102302 |
| 1 | never_observed | claude-sonnet-4-6 | 9 | 391 | 0.0230179 |
| 2 | observed | claude-fable-5 | 2 | 4 | 0.5 |
| 2 | observed | claude-haiku-4-5-20251001 | 2 | 4 | 0.5 |
| 2 | observed | claude-opus-4-6 | 2 | 4 | 0.5 |
| 2 | observed | claude-opus-4-7 | 1 | 4 | 0.25 |
| 2 | observed | claude-opus-4-8 | 3 | 4 | 0.75 |
| 2 | never_observed | claude-fable-5 | 99 | 389 | 0.254499 |
| 2 | never_observed | claude-haiku-4-5-20251001 | 129 | 389 | 0.33162 |
| 2 | never_observed | claude-opus-4-6 | 25 | 389 | 0.0642674 |
| 2 | never_observed | claude-opus-4-7 | 26 | 389 | 0.066838 |
| 2 | never_observed | claude-opus-4-8 | 311 | 389 | 0.799486 |
| 2 | never_observed | claude-sonnet-4-5 | 4 | 389 | 0.0102828 |
| 2 | never_observed | claude-sonnet-4-6 | 9 | 389 | 0.0231362 |
| 3 | observed | claude-fable-5 | 2 | 7 | 0.285714 |
| 3 | observed | claude-haiku-4-5-20251001 | 2 | 7 | 0.285714 |
| 3 | observed | claude-opus-4-6 | 2 | 7 | 0.285714 |
| 3 | observed | claude-opus-4-7 | 1 | 7 | 0.142857 |
| 3 | observed | claude-opus-4-8 | 6 | 7 | 0.857143 |
| 3 | never_observed | claude-fable-5 | 99 | 386 | 0.256477 |
| 3 | never_observed | claude-haiku-4-5-20251001 | 129 | 386 | 0.334197 |
| 3 | never_observed | claude-opus-4-6 | 25 | 386 | 0.0647668 |
| 3 | never_observed | claude-opus-4-7 | 26 | 386 | 0.0673575 |
| 3 | never_observed | claude-opus-4-8 | 308 | 386 | 0.797927 |
| 3 | never_observed | claude-sonnet-4-5 | 4 | 386 | 0.0103627 |
| 3 | never_observed | claude-sonnet-4-6 | 9 | 386 | 0.0233161 |
| 4 | observed | claude-fable-5 | 2 | 8 | 0.25 |
| 4 | observed | claude-haiku-4-5-20251001 | 3 | 8 | 0.375 |
| 4 | observed | claude-opus-4-6 | 2 | 8 | 0.25 |
| 4 | observed | claude-opus-4-7 | 1 | 8 | 0.125 |
| 4 | observed | claude-opus-4-8 | 7 | 8 | 0.875 |
| 4 | never_observed | claude-fable-5 | 99 | 385 | 0.257143 |

## Inference

- **Inference:** different observed ID sets can reflect fixed-duration replay, warmup point, recycling, scheduling, or concurrency; coverage differences are not automatically performance effects.

## Unknown

- **Unknown:** source coverage does not establish that every source trace or turn was replayed at every concurrency.
