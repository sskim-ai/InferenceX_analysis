# 분석 대상

- **Evidence:** 공개 InferenceX GitHub Actions run `29820102138`과 `semianalysisai/cc-traces-weka-062126` source workload trace를 분석 대상으로 고정했다.
- **Evidence:** source `model`은 Claude Code 수집 시의 workload label이다. H200 target `GLM-5.2 FP8` replay 성능과 동일시하지 않도록 별도 field로 보존한다.

# H200 환경 검증

- **Evidence:** GitHub run metadata가 저장됨; same-SHA InferenceX config/recipe는 target `GLM-5.2 FP8`, shared 16×H200, Dynamo+SGLang, Mooncake, HiSparse, 1,048,576 context, conc1–8을 명시한다 (`01_provenance.md`).
- **Inference:** successful run metadata와 same-SHA recipe의 조합은 의도된 GLM-5.2 FP8 H200 replay 환경이라는 해석을 뒷받침한다 (confidence: 높음 for recipe association).
- **Unknown:** per-request command override, queue/server state, actual cache residency는 aggregate/config만으로 확정할 수 없다.

# 데이터와 ID 연결 방식

- **Evidence:** source root trace `393`개, source request `98,827`개를 flattened table로 보존했다.
- **Evidence:** `metadata.source_trace_id`는 loader가 raw H200 row에 보존한 source-root evidence다. `::sa:` split은 metadata가 없을 때의 fallback이며, direct metadata와 동일한 강도로 주장하지 않는다.
- **Evidence:** profiling H200 row `2,491`개 중 `metadata.source_trace_id` root provenance `2,491`개 (100.0%), loader metadata association `2,491`개 (100.0%), input-compatible strict exact-turn `21`개 (0.8%)다.
- **Unknown:** loader metadata association은 source outer/inner index 연결 evidence이지만, strict exact-turn도 input length compatibility까지의 보수적 기준이다. 독립적인 시간/order identity를 추가로 증명하지 않는다.

# ID coverage

- **Evidence:** conc1–8 전체에서 profiling으로 한 번 이상 관측된 root ID는 `11/393` (2.8%)다.
- **Evidence:** concurrency별 observed root-ID / profiling request / token coverage와 replay suffix vs source-origin branch count를 `04_coverage.md`와 `id_coverage_matrix.csv`에 보존했다. 각 concurrency의 observed H200 ID가 source ID와 일치하는 비율과 source universe coverage는 분모가 다르다.
- **Inference:** observed ID set 차이는 fixed-duration replay, warmup, recycling, scheduling 또는 concurrency에 따른 coverage bias일 수 있으므로 성능 비교 전에 통제한다.

# ID별 성능 핵심 결과

- **Evidence:** valid profiling row `2,491`개를 root-ID × concurrency `57`개로 집계했다. `session_num` group은 opaque/unvalidated metadata이며 독립 replay instance로 취급하지 않는다. request-weighted/root-ID-weighted 결과는 `weighting_summary.csv`에서 분리한다.
- **Evidence:** TTFT, request-level ITL/TPOT, E2E는 profiling·성공·비취소·유효 metric filter의 observed target H200 replay 값이다. source `api_time`과 동일 조건 값으로 비교하지 않는다.
- **Unknown:** conversation ID별 GPU 수, GPU utilization, 또는 GPU affinity는 이 shared 16×H200 record에서 식별할 수 없다.

# Concurrency 1~8 비교

- **Evidence:** ID-level ratio `57`개 중 실제 cross-concurrency ratio `46`개, coverage-comparable `11`개, coverage-confounded `35`개다. confounded row는 degradation evidence로 사용하지 않는다.
- **Evidence:** strict-exact paired H200 comparison `7`개는 target replay의 실제 양쪽 `output_tokens`를 유지한다. 같은 output `7/7`, 다른 output `0/7`이며 conc1 baseline pair는 `0/7`개다.
- **Inference:** coverage-comparable ID-level ratio 및 strict-exact pair는 조건부 descriptive comparison이다. monotonic concurrency degradation 또는 단일 원인으로 해석하지 않는다 (confidence: 낮음~중간; paired sample count에 의존).

# Root agent와 subagent 비교

- **Evidence:** H200 replay `branch_type`은 conversation-ID suffix taxonomy이고, `source_branch_type`/`source_origin_branch_type`은 mapped source nested trace origin taxonomy다. 둘은 source-origin과 replay structure를 나타내는 서로 다른 field다.
- **Evidence:** replay suffix taxonomy는 `replay_branch_type_summary.csv`/`root_subagent_summary.csv`, source-origin taxonomy는 `source_origin_branch_summary.csv`에 concurrency별로 분리한다. label 차이 자체를 target model 차이로 해석하지 않는다.
- **Unknown:** `session_num`은 replay grouping field로 보존하지만 semantic replay-instance identity나 request independence를 증명하지 않는다. paired bootstrap은 보수적으로 root trace ID를 cluster unit으로 사용한다.

# Context 및 theoretical cache reuse 영향

- **Evidence:** source hash ID longest-common-prefix로 계산한 theoretical cache reuse는 source workload shape다. actual H200 server cache residency/hit와 동일하지 않다.
- **Evidence:** strict exact source/H200 row `21`개에서만 theoretical new tokens/cache ratio와 observed H200 TTFT의 관계를 `cache_shape_relationship_summary.csv`로 계산했다.
- **Unknown:** actual cache metric이 request scope에서 없으면 cache ratio와 TTFT의 인과 관계를 확정할 수 없다.

# 가장 부담이 큰 trace IDs

- **Evidence:** 아래 ranking은 observed root-ID × concurrency row 기준이다. full public trace ID와 sample count는 CSV/Parquet에 보존한다.

`total_input_tokens` (top 5 observed root-ID × concurrency rows):

| rank | root_trace_id | concurrency | profiled_request_count | rank_metric | total_input_tokens | total_output_tokens | median_ttft_ms | sample_quality_flag |
|---|---|---|---|---|---|---|---|---|
| 1 | 02bc0afb13f7… | 1 | 265 | total_input_tokens | 1.10482e+07 | 123157 | 1045.6 | session_num_unique_per_profiled_row |
| 2 | 02bc0afb13f7… | 4 | 108 | total_input_tokens | 6.49587e+06 | 91153 | 3806.75 | session_num_unique_per_profiled_row |
| 3 | 0470d446a451… | 3 | 50 | total_input_tokens | 5.39519e+06 | 40009 | 1117.13 | session_num_unique_per_profiled_row |
| 4 | 0470d446a451… | 7 | 88 | total_input_tokens | 5.38844e+06 | 37554 | 185940 | session_num_unique_per_profiled_row |
| 5 | 0470d446a451… | 8 | 84 | total_input_tokens | 5.17822e+06 | 35880 | 211109 | session_num_unique_per_profiled_row |

`total_output_tokens` (top 5 observed root-ID × concurrency rows):

| rank | root_trace_id | concurrency | profiled_request_count | rank_metric | total_input_tokens | total_output_tokens | median_ttft_ms | sample_quality_flag |
|---|---|---|---|---|---|---|---|---|
| 1 | 02bc0afb13f7… | 1 | 265 | total_output_tokens | 1.10482e+07 | 123157 | 1045.6 | session_num_unique_per_profiled_row |
| 2 | 02bc0afb13f7… | 4 | 108 | total_output_tokens | 6.49587e+06 | 91153 | 3806.75 | session_num_unique_per_profiled_row |
| 3 | 03e110ac6921… | 2 | 86 | total_output_tokens | 4.04998e+06 | 83665 | 1256.14 | session_num_unique_per_profiled_row |
| 4 | 03e110ac6921… | 5 | 29 | total_output_tokens | 1.88742e+06 | 44744 | 94602.9 | session_num_unique_per_profiled_row |
| 5 | 03e110ac6921… | 4 | 73 | total_output_tokens | 2.98563e+06 | 42949 | 36498.3 | session_num_unique_per_profiled_row |

`replay_nonroot_branch_request_count` (top 5 observed root-ID × concurrency rows):

| rank | root_trace_id | concurrency | profiled_request_count | rank_metric | total_input_tokens | total_output_tokens | median_ttft_ms | sample_quality_flag |
|---|---|---|---|---|---|---|---|---|
| 1 | 02bc0afb13f7… | 1 | 265 | replay_nonroot_branch_request_count | 1.10482e+07 | 123157 | 1045.6 | session_num_unique_per_profiled_row |
| 2 | 02bc0afb13f7… | 3 | 188 | replay_nonroot_branch_request_count | 158338 | 2756 | 2343.94 | session_num_unique_per_profiled_row |
| 3 | 02bc0afb13f7… | 2 | 177 | replay_nonroot_branch_request_count | 150818 | 2663 | 2173.75 | session_num_unique_per_profiled_row |
| 4 | 02bc0afb13f7… | 5 | 110 | replay_nonroot_branch_request_count | 3.74078e+06 | 24440 | 30759.9 | session_num_unique_per_profiled_row |
| 5 | 02bc0afb13f7… | 4 | 108 | replay_nonroot_branch_request_count | 6.49587e+06 | 91153 | 3806.75 | session_num_unique_per_profiled_row |

Latency / wall-time / low-output-rate ranking:

`median_ttft_ms` (top 5 observed root-ID × concurrency rows):

| rank | root_trace_id | concurrency | profiled_request_count | rank_metric | median_ttft_ms | p90_ttft_ms | median_e2e_ms | p90_e2e_ms | total_h200_wall_time_s | wall_clock_output_rate | sample_quality_flag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0196085d85d2… | 8 | 11 | median_ttft_ms | 309425 | 343078 | 309425 | 343078 | 3409.52 | 0.0032067 | session_num_unique_per_profiled_row |
| 2 | 0196085d85d2… | 7 | 12 | median_ttft_ms | 289555 | 385831 | 289555 | 385831 | 3468.72 | 0.00343574 | session_num_unique_per_profiled_row |
| 3 | 03e110ac6921… | 8 | 18 | median_ttft_ms | 271908 | 365606 | 287284 | 365606 | 4624.38 | 1.19646 | session_num_unique_per_profiled_row |
| 4 | 002001296e8a… | 8 | 15 | median_ttft_ms | 249645 | 300592 | 258083 | 311285 | 3558.14 | 2.55745 | session_num_unique_per_profiled_row |
| 5 | 063179eb93f4… | 8 | 3 | median_ttft_ms | 240846 | 244611 | 246228 | 272040 | 766.268 | 4.48807 | session_num_unique_per_profiled_row |

`p90_ttft_ms` (top 5 observed root-ID × concurrency rows):

| rank | root_trace_id | concurrency | profiled_request_count | rank_metric | median_ttft_ms | p90_ttft_ms | median_e2e_ms | p90_e2e_ms | total_h200_wall_time_s | wall_clock_output_rate | sample_quality_flag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0196085d85d2… | 7 | 12 | p90_ttft_ms | 289555 | 385831 | 289555 | 385831 | 3468.72 | 0.00343574 | session_num_unique_per_profiled_row |
| 2 | 03e110ac6921… | 8 | 18 | p90_ttft_ms | 271908 | 365606 | 287284 | 365606 | 4624.38 | 1.19646 | session_num_unique_per_profiled_row |
| 3 | 0196085d85d2… | 8 | 11 | p90_ttft_ms | 309425 | 343078 | 309425 | 343078 | 3409.52 | 0.0032067 | session_num_unique_per_profiled_row |
| 4 | 02bc0afb13f7… | 8 | 43 | p90_ttft_ms | 239140 | 318628 | 242462 | 326511 | 10362.3 | 3.49548 | session_num_unique_per_profiled_row |
| 5 | 006c98de37d8… | 8 | 13 | p90_ttft_ms | 236222 | 309980 | 265358 | 385855 | 3267.59 | 3.18428 | session_num_unique_per_profiled_row |

`median_e2e_ms` (top 5 observed root-ID × concurrency rows):

| rank | root_trace_id | concurrency | profiled_request_count | rank_metric | median_ttft_ms | p90_ttft_ms | median_e2e_ms | p90_e2e_ms | total_h200_wall_time_s | wall_clock_output_rate | sample_quality_flag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0196085d85d2… | 8 | 11 | median_e2e_ms | 309425 | 343078 | 309425 | 343078 | 3409.52 | 0.0032067 | session_num_unique_per_profiled_row |
| 2 | 0196085d85d2… | 7 | 12 | median_e2e_ms | 289555 | 385831 | 289555 | 385831 | 3468.72 | 0.00343574 | session_num_unique_per_profiled_row |
| 3 | 03e110ac6921… | 8 | 18 | median_e2e_ms | 271908 | 365606 | 287284 | 365606 | 4624.38 | 1.19646 | session_num_unique_per_profiled_row |
| 4 | 006c98de37d8… | 8 | 13 | median_e2e_ms | 236222 | 309980 | 265358 | 385855 | 3267.59 | 3.18428 | session_num_unique_per_profiled_row |
| 5 | 002001296e8a… | 8 | 15 | median_e2e_ms | 249645 | 300592 | 258083 | 311285 | 3558.14 | 2.55745 | session_num_unique_per_profiled_row |

`total_h200_wall_time_s` (top 5 observed root-ID × concurrency rows):

| rank | root_trace_id | concurrency | profiled_request_count | rank_metric | median_ttft_ms | p90_ttft_ms | median_e2e_ms | p90_e2e_ms | total_h200_wall_time_s | wall_clock_output_rate | sample_quality_flag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0470d446a451… | 8 | 84 | total_h200_wall_time_s | 211109 | 284506 | 221965 | 300429 | 17665.8 | 10.0874 | session_num_unique_per_profiled_row |
| 2 | 0470d446a451… | 7 | 88 | total_h200_wall_time_s | 185940 | 280403 | 194711 | 294004 | 17481.2 | 10.4106 | session_num_unique_per_profiled_row |
| 3 | 02bc0afb13f7… | 8 | 43 | total_h200_wall_time_s | 239140 | 318628 | 242462 | 326511 | 10362.3 | 3.49548 | session_num_unique_per_profiled_row |
| 4 | 02bc0afb13f7… | 7 | 46 | total_h200_wall_time_s | 206870 | 308725 | 210587 | 321535 | 10156 | 3.4985 | session_num_unique_per_profiled_row |
| 5 | 02bc0afb13f7… | 6 | 59 | total_h200_wall_time_s | 153821 | 223447 | 159696 | 226236 | 9157.61 | 3.69239 | session_num_unique_per_profiled_row |

`wall_clock_output_rate` (top 5 observed root-ID × concurrency rows):

| rank | root_trace_id | concurrency | profiled_request_count | rank_metric | median_ttft_ms | p90_ttft_ms | median_e2e_ms | p90_e2e_ms | total_h200_wall_time_s | wall_clock_output_rate | sample_quality_flag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0196085d85d2… | 8 | 11 | wall_clock_output_rate | 309425 | 343078 | 309425 | 343078 | 3409.52 | 0.0032067 | session_num_unique_per_profiled_row |
| 2 | 0196085d85d2… | 7 | 12 | wall_clock_output_rate | 289555 | 385831 | 289555 | 385831 | 3468.72 | 0.00343574 | session_num_unique_per_profiled_row |
| 3 | 00ca01c4aaec… | 7 | 6 | wall_clock_output_rate | 240049 | 297691 | 240049 | 297691 | 1323.5 | 0.00450011 | session_num_unique_per_profiled_row |
| 4 | 00ca01c4aaec… | 8 | 7 | wall_clock_output_rate | 195743 | 293834 | 195743 | 293834 | 1451.1 | 0.00479154 | session_num_unique_per_profiled_row |
| 5 | 0196085d85d2… | 6 | 17 | wall_clock_output_rate | 206489 | 276934 | 206489 | 276934 | 3475.5 | 0.00483978 | session_num_unique_per_profiled_row |
- **Inference:** 높은 observed workload 또는 wall time rank는 해당 run/coverage의 부담을 보여 주지만, 모든 source trace의 전역 rank나 GPU affinity를 뜻하지 않는다.

# Aggregate 결과 재현 검증

- **Evidence:** raw-to-published aggregate validation `240`개 중 `240`개가 `pass` 또는 documented alias-equivalent 상태다. metric별 raw/published/tolerance/status는 `aggregate_validation.csv`에 보존했다.
- **Inference:** 이 일치는 선택한 raw filter·unit conversion·percentile·time-window 구현의 재현 evidence이며, ID-level mapping의 완전성 또는 causal interpretation을 보장하지 않는다.

# 확인된 사실

- **Evidence:** source workload는 `393` root trace / `98,827` request이며 입력 `21,635,381,376` tokens, 출력 `106,474,498` tokens이다.
- **Evidence:** source `ttft` 존재율은 `57.1%`이다. source `api_time`은 source collection provenance이며 observed H200 replay latency와 분리한다.
- **Evidence:** conversation ID는 workload trace 식별자이며 GPU 식별자가 아니다.

# Source model label별 workload shape

- **Evidence:** 아래 label은 source Claude Code workload provenance이며 target GLM-5.2 target-model 성능 분류가 아니다.

| source_model | source_request_count | distinct_root_trace_ids | median_input_tokens | p90_input_tokens | median_output_tokens |
|---|---|---|---|---|---|
| claude-opus-4-8 | 62108 | 314 | 200448 | 622803 | 608 |
| claude-fable-5 | 16192 | 101 | 145952 | 414086 | 402.5 |
| claude-haiku-4-5-20251001 | 7973 | 131 | 41600 | 80640 | 148 |
| claude-opus-4-7 | 6419 | 27 | 135680 | 223424 | 266 |
| claude-opus-4-6 | 5452 | 27 | 89344 | 146880 | 201 |
| claude-sonnet-4-6 | 576 | 9 | 64160 | 104128 | 195 |
| claude-sonnet-4-5 | 107 | 4 | 41088 | 104781 | 527 |
- **Inference:** source model label과 H200 replay latency의 관계를 해석하려면 root ID, context, source-origin branch, replay branch, concurrency 및 coverage를 함께 통제해야 한다.

# 추론

- **Inference:** same-SHA recipe와 successful run metadata는 target GLM-5.2 FP8 H200 replay라는 해석을 뒷받침하지만, per-request override까지 증명하지는 않는다 (confidence: 높음 for recipe association; 낮음 for unobserved overrides).

# 확인할 수 없는 것

- **Unknown:** source/target model 직접 성능 비교, ID별 GPU attribution, source API measurement와 H200 replay measurement의 동등 조건 비교.

# 데이터 한계

- **Unknown:** fixed-duration replay의 warmup, recycling, scheduling, cancellation, repeated row, shared-system effect가 observed distribution에 미친 정확한 정도.

# 재현 방법

```sh
make bootstrap
gh auth login --web --git-protocol ssh
make acquire-run
make all
```

생성 시각(UTC): `2026-08-06T10:14:10Z`
