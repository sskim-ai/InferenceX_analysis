# 06. Cross-concurrency comparisons

## Evidence

- **Evidence:** ID-level ratio rows `57` 중 baseline self-row를 제외한 cross-concurrency row는 `46`개다. coverage-comparable row는 `11`, coverage-confounded row는 `35`개다.
- **Evidence:** 아래 ID-level ratio 표는 coverage-comparable cross-concurrency rows만 제시한다. 이 표에 없는 cross-concurrency ratio는 workload/request/token coverage가 달라져 degradation evidence로 사용하지 않는다.

| root_trace_id | concurrency | baseline_concurrency | ttft_ratio | itl_ratio | e2e_ratio | wall_clock_output_rate_ratio | request_coverage_ratio | input_token_coverage_ratio | output_token_coverage_ratio |
|---|---|---|---|---|---|---|---|---|---|
| 006c98de37d8… | 6 | 5 | 1.81305 | 1.00557 | 1.64059 | 0.668747 | 1.09091 | 1.08331 | 1.09153 |
| 006c98de37d8… | 7 | 5 | 2.42427 | 1.01734 | 2.1125 | 0.494285 | 1.18182 | 1.16466 | 1.14401 |
| 006c98de37d8… | 8 | 5 | 3.01432 | 1.01263 | 2.65008 | 0.433603 | 1.18182 | 1.16468 | 1.14401 |
| 0196085d85d2… | 2 | 1 | 1.07447 | 1.03446 | 1.05449 | 0.495065 | 0.977778 | 0.999989 | 0.999513 |
| 0196085d85d2… | 3 | 1 | 1.02273 | 1.01289 | 1.00372 | 0.407081 | 1.18889 | 1.00003 | 1.00414 |
| 0470d446a451… | 3 | 2 | 1.08208 | 0.985082 | 1.43679 | 0.691768 | 1.13636 | 1.18252 | 1.13963 |
| 0470d446a451… | 4 | 2 | 1.09054 | 1.08421 | 1.31127 | 0.855115 | 1.04545 | 1.05889 | 1.03005 |
| 04dba6fe6213… | 4 | 3 | 0.038245 | 1.24613 | 0.691843 | 1.25095 | 1 | 0.999964 | 1 |
| 04dba6fe6213… | 6 | 3 | 1.97303 | 1.03884 | 1.47043 | 0.516942 | 1 | 0.999964 | 1 |
| 04dba6fe6213… | 7 | 3 | 3.16249 | 1.03342 | 2.1583 | 0.304468 | 1 | 0.999964 | 1 |
| 05c249572509… | 4 | 3 | 0.849077 | 1.0883 | 1.06608 | 1.03946 | 1 | 0.99997 | 1 |
- **Evidence:** strict-exact turn filter에서 나온 paired cross-concurrency row는 `7`개다. 각 side의 target replay `output_tokens`를 그대로 유지하며, source output length로 대체하지 않는다. 동일 observed output token row는 `7/7`, 서로 다른 observed output token row는 `0/7`이다.
- **Evidence:** paired rows 중 conc1을 baseline으로 가진 row는 `0/7`개다; 나머지는 해당 exact turn의 최소 관측 concurrency를 baseline으로 사용한다.
- **Evidence:** Strict-exact paired table:

| root_trace_id | concurrency | baseline_concurrency | matched_sample_count | baseline_matched_sample_count | output_tokens | baseline_output_tokens | output_token_delta | ttft_ratio | itl_ratio | e2e_ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| 03e110ac6921… | 5 | 2 | 1 | 1 | 345 | 345 | 0 | 187.119 | 0.944249 | 14.7004 |
| 0470d446a451… | 6 | 4 | 1 | 1 | 380 | 380 | 0 | 37.8647 | 1.05582 | 7.83163 |
| 04dba6fe6213… | 6 | 4 | 1 | 1 | 692 | 692 | 0 | 18.681 | 0.867192 | 4.0171 |
| 04dba6fe6213… | 7 | 4 | 1 | 1 | 692 | 692 | 0 | 57.5358 | 0.834429 | 10.8606 |
| 04dba6fe6213… | 6 | 4 | 1 | 1 | 538 | 538 | 0 | 43.8718 | 0.985421 | 5.28991 |
| 04dba6fe6213… | 7 | 4 | 1 | 1 | 538 | 538 | 0 | 71.6445 | 0.926393 | 8.02435 |
| 05c249572509… | 8 | 3 | 1 | 1 | 725 | 725 | 0 | 112.552 | 0.963957 | 8.52639 |
- **Evidence:** Root-ID clustered bootstrap summary:

| concurrency | metric | paired_turn_count | root_id_cluster_count | median_ratio | bootstrap_ci_low | bootstrap_ci_high | n_bootstrap |
|---|---|---|---|---|---|---|---|
| 5 | ttft_ratio | 1 | 1 | 187.119 | 187.119 | 187.119 | 1000 |
| 5 | itl_ratio | 1 | 1 | 0.944249 | 0.944249 | 0.944249 | 1000 |
| 5 | e2e_ratio | 1 | 1 | 14.7004 | 14.7004 | 14.7004 | 1000 |
| 6 | ttft_ratio | 3 | 2 | 37.8647 | 31.2764 | 37.8647 | 1000 |
| 6 | itl_ratio | 3 | 2 | 0.985421 | 0.926306 | 1.05582 | 1000 |
| 6 | e2e_ratio | 3 | 2 | 5.28991 | 4.65351 | 7.83163 | 1000 |
| 7 | ttft_ratio | 2 | 1 | 64.5901 | 64.5901 | 64.5901 | 1000 |
| 7 | itl_ratio | 2 | 1 | 0.880411 | 0.880411 | 0.880411 | 1000 |
| 7 | e2e_ratio | 2 | 1 | 9.44248 | 9.44248 | 9.44248 | 1000 |
| 8 | ttft_ratio | 1 | 1 | 112.552 | 112.552 | 112.552 | 1000 |
| 8 | itl_ratio | 1 | 1 | 0.963957 | 0.963957 | 0.963957 | 1000 |
| 8 | e2e_ratio | 1 | 1 | 8.52639 | 8.52639 | 8.52639 | 1000 |
- **Evidence:** strict exact source/H200 rows for theoretical cache-shape analysis: `21`.

| concurrency | branch_group | exact_turn_request_count | distinct_root_ids | median_ttft_ms | median_theoretical_new_tokens | median_theoretical_cache_ratio | spearman_ttft_vs_theoretical_new_tokens | spearman_ttft_vs_theoretical_cache_ratio |
|---|---|---|---|---|---|---|---|---|
| 1 | all | 1 | 1 | 1272.51 | 6080 | 0.920168 |  |  |
| 1 | root | 1 | 1 | 1272.51 | 6080 | 0.920168 |  |  |
| 2 | all | 1 | 1 | 890.624 | 768 | 0.991254 |  |  |
| 2 | subagent_main | 1 | 1 | 890.624 | 768 | 0.991254 |  |  |
| 3 | all | 5 | 3 | 57866.2 | 14336 | 0.82008 | 0.3 | -0.3 |
| 3 | root | 4 | 3 | 33683.7 | 18976 | 0.747628 | 0.8 | -0.8 |
| 3 | subagent_main | 1 | 1 | 68630.7 | 1664 | 0.95057 |  |  |
| 4 | all | 5 | 4 | 2702.17 | 26912 | 0.635938 | 0.8 | -0.4 |
| 4 | root | 3 | 3 | 2702.17 | 3520 | 0.928105 | 1 | -1 |
| 4 | subagent_main | 2 | 1 | 3720.4 | 50304 | 0 |  |  |
| 5 | all | 2 | 2 | 84518.1 | 3040 | 0.946803 |  |  |
| 5 | root | 1 | 1 | 2383.25 | 5312 | 0.902353 |  |  |
| 5 | subagent_main | 1 | 1 | 166653 | 768 | 0.991254 |  |  |
| 6 | all | 3 | 2 | 102317 | 26912 | 0.464052 |  |  |
| 6 | root | 1 | 1 | 102317 | 3520 | 0.928105 |  |  |
| 6 | subagent_main | 2 | 1 | 99157.6 | 50304 | 0 |  |  |
| 7 | all | 3 | 2 | 280386 | 50304 | 0 |  |  |
| 7 | subagent_main | 3 | 2 | 280386 | 50304 | 0 |  |  |
| 8 | all | 1 | 1 | 185416 | 9088 | 0.863724 |  |  |
| 8 | root | 1 | 1 | 185416 | 9088 | 0.863724 |  |  |

## Inference

- **Inference:** coverage-comparable ID-level ratios and strict-exact paired rows are descriptive replay comparisons, not proof of a monotonic or causal concurrency degradation.

## Unknown

- **Unknown:** coverage-confounded rows, unpaired rows, shared-system scheduling, and small exact-pair counts prevent population-level causal claims.
