# Internal GPT Task — `07dd405` Local c1 / c4 / c8 Saturation Analysis

## 0. 목적

사내 서버에서 이미 수행한 동일 workload `07dd405`의 local concurrency 1 / 4 / 8 결과를 실제 raw log/config/result 파일에서 분석하여, concurrency 증가에 따라 **queueing, prefill, decode, E2E, offered load, scheduler pressure가 어떻게 변하는지** 분리한다.

이 작업의 핵심은 단순히 c1/c4/c8의 TTFT 숫자를 나열하는 것이 아니다.

다음을 검증한다.

```text
1. c1을 local single-load execution baseline으로 정의할 수 있는가?
2. c4에서 scheduler/admission pressure가 언제부터 나타나는가?
3. c8에서 관측되는 큰 TTFT가 queue 증가로 설명되는가?
4. concurrency 증가에도 prefill / decode execution 성능은 얼마나 유지되는가?
5. AgentX root concurrency와 실제 HTTP request fan-out, vLLM running/waiting은 어떻게 다른가?
6. 동일 source request를 exact-match했을 때 c1→c4→c8 latency inflation이 어디에서 발생하는가?
```

계획만 작성하지 말고 현재 사내 작업공간의 실제 파일을 탐색·파싱하여 분석을 완료한다.

---

# 1. 보안 규칙

사내 raw log, config, private metric, private path, internal hostname/IP, credential, model storage path 등은 외부 GitHub repository로 commit/push하지 않는다.

이 작업의 산출물은 사내 작업공간에만 생성한다.

특히 다음을 금지한다.

```text
Git commit
Git push
GitHub upload
외부 서비스로 raw log 업로드
private path/hostname/IP를 export-safe 결과에 포함
```

Public GitHub repository가 읽기 가능할 경우 reference 파일을 **read-only**로만 사용한다.

---

# 2. Primary workload

Canonical public source trace ID:

```text
07dd40536557a1d6440a923557c3129dc929
```

Requested prefix:

```text
07dd405
```

Local c1/c4/c8에서 실제로 동일 canonical trace를 실행했는지 raw metadata/config에서 확인한다.

---

# 3. 분석할 Local runs

최소 다음 세 실험을 찾는다.

```text
concurrency = 1
concurrency = 4
concurrency = 8
```

각 run에서 copy/lane 수를 config/log로 검증한다.

예상 구조는 다음과 같지만 증거 없이 확정하지 않는다.

```text
c1 -> 1 independent root copy
c4 -> 4 independent root copies
c8 -> 8 independent root copies
```

각 run에 대해 다음을 명시한다.

```text
configured_global_concurrency
observed_independent_root_copy_count
observed_max_overlapping_root_sessions
observed_max_overlapping_http_requests
vllm_observed_max_running
vllm_observed_max_waiting
```

---

# 4. System configuration consistency 검증

c1 / c4 / c8이 concurrency를 제외하면 동일한 system configuration인지 비교한다.

다음 필드를 run별로 추출한다.

```text
GPU SKU / count
model checkpoint
weight dtype
quantization
TP / DP / PP / EP
speculative decoding / MTP
max_model_len
max_num_batched_tokens
max_num_seqs
KV block/page size
GPU KV capacity
LMCache enablement
LMCache chunk size
LMCache CPU backend size
LMCache disk backend / capacity
cache eviction policy
save decode cache
save unfull chunk
prefix/radix cache setting
CPU/KV offload setting
vLLM / serving framework version
```

생성:

```text
local_id03_c1_c4_c8_config_consistency.csv
```

필드:

```text
field,c1_value,c4_value,c8_value,consistent,status,notes
```

Concurrency 외 설정 차이가 발견되면 이후 scaling analysis에 confounder로 명시한다.

---

# 5. Request-level canonical table

각 local run의 모든 target workload request를 long-form canonical table로 만든다.

가능하면 1 row = 1 copy × 1 source request.

필수 컬럼:

```text
local_concurrency
local_copy_index
local_copy_label

source_trace_id
source_outer_idx
source_inner_idx
source_conversation_path
source_branch_type
turn_index
exact_source_key

request_start
request_end

success
error_category
context_overflow

input_tokens
input_token_semantics
output_tokens
requested_output_limit

ttft_ms
queue_ms
prefill_ms
itl_ms
decode_tps
e2e_ms

cache_hit_tokens
cache_hit_metric_semantics
cache_store_tokens
cache_store_metric_semantics

worker_or_scheduler_id
```

생성:

```text
local_id03_c1_c4_c8_requests.csv
```

이 full local table은 사내에만 보관한다.

---

# 6. Exact source key

Canonical exact key:

```text
source_trace_id + source_outer_idx + source_inner_idx
```

Root-level null source_inner_idx는 실제 loader semantics가 root null임을 확인한 경우에만 normalized `-1`을 사용할 수 있다.

Validation field:

```text
source_conversation_path
turn_index
```

Key가 같지만 validation field가 충돌하면 strict comparison에서 제외한다.

---

# 7. Coverage 검증

각 run/copy별로 다음을 계산한다.

```text
expected_source_key_count
observed_request_count
successful_request_count
failed_request_count
distinct_exact_source_key_count
first_successful_key
last_successful_key
first_failed_key
context_overflow_position
```

생성:

```text
local_id03_c1_c4_c8_coverage.csv
```

특히 c1/c4/c8의 비교는 가능한 한 **모두 성공한 공통 exact source-key subset**을 primary subset으로 사용한다.

---

# 8. Three-way common exact subset

다음 조건을 만족하는 source key를 추출한다.

```text
c1에서 성공
AND
c4의 모든 비교 대상 copy에서 성공
AND
c8의 모든 비교 대상 copy에서 성공
```

다만 한 copy의 단일 transport/server disconnection 때문에 전체 key를 버리는 것이 분석 목적에 부적절하면 두 subset을 별도로 만든다.

```text
strict_all_copy_common_subset
run_level_success_common_subset
```

두 subset 정의를 보고서에서 명확히 설명한다.

---

# 9. Local c1 baseline 정의

c1은 local server의 low-contention baseline 후보다.

그러나 다음을 확인한 뒤 baseline으로 확정한다.

```text
HTTP overlap
vLLM waiting
queue time
scheduler running
```

c1에서도 유의미한 waiting/queue가 관측되면 "contention-free baseline"이라고 부르지 않는다.

그 경우:

```text
lowest-observed-load baseline
```

으로 표현한다.

---

# 10. Request-wise c4/c1, c8/c1 paired comparison

동일 exact source key 기준으로 다음 pair를 만든다.

```text
c1 vs c4
c1 vs c8
c4 vs c8
```

c4/c8에 여러 copies가 있으므로 최소 두 분석 단위를 만든다.

### A. Focal copy comparison

각 run의 copy1을 사용:

```text
c1 copy1
c4 copy1
c8 copy1
```

### B. All-copy normalized comparison

동일 exact source key에 대해 run 내 copy median을 계산:

```text
median across c4 copies
median across c8 copies
```

그 후 c1과 비교한다.

---

# 11. Strict comparison subsets

### Strict TTFT

```text
same exact source key
validation conflict 없음
양쪽 성공
TTFT 존재
```

### Strict queue

```text
Strict TTFT + 양쪽 queue metric 존재 및 semantics 동일
```

### Strict prefill

```text
Strict TTFT + 양쪽 prefill metric 존재 및 semantics 동일
```

### Strict decode

```text
Strict TTFT
output_tokens > 1
양쪽 ITL 존재
observed output length 동일
```

### Strict E2E

```text
Strict TTFT + observed output length 동일 + E2E 존재
```

---

# 12. TTFT decomposition

각 request에 대해 가능한 경우 다음을 계산한다.

```text
execution_side_ttft_ms = ttft_ms - queue_ms
```

그리고 가능한 경우:

```text
pre_first_token_residual_ms = ttft_ms - queue_ms - prefill_ms
```

단, queue/prefill metric 정의가 TTFT와 additive relationship을 갖는지 raw instrumentation semantics를 먼저 확인한다.

정의가 확실하지 않으면 이름을 `observed_residual_proxy`로 낮춘다.

Negative residual이 의미 있게 나타나면 metric boundary가 additive하지 않은 것이므로 decomposition을 중단하고 원인을 기록한다.

---

# 13. Run-level latency summary

각 concurrency에 대해:

```text
TTFT mean / median / P75 / P90 / P95 / max
queue mean / median / P90 / P95
prefill mean / median / P90 / P95
execution-side TTFT mean / median / P90
prefirst residual mean / median / P90
E2E mean / median / P90 / P95
```

생성:

```text
local_id03_c1_c4_c8_latency_summary.csv
```

---

# 14. Queue share

Request-level로:

```text
queue_share_of_ttft = queue_ms / ttft_ms
prefill_share_of_ttft = prefill_ms / ttft_ms
execution_side_share = (ttft_ms - queue_ms) / ttft_ms
```

각 concurrency별:

```text
mean
median
P75
P90
```

을 계산한다.

Aggregate mean끼리 나눈 값도 보조로 표시할 수 있지만 primary metric은 request-wise ratio distribution으로 한다.

---

# 15. TTFT inflation

c1 baseline 대비:

```text
request-wise TTFT ratio c4/c1
request-wise TTFT ratio c8/c1
```

각각:

```text
P25
median
P75
P90
```

을 계산한다.

그리고 aggregate median ratio도 별도 보조지표로 계산한다.

```text
median_TTFT_c4 / median_TTFT_c1
median_TTFT_c8 / median_TTFT_c1
```

Request-wise ratio median과 ratio-of-medians를 혼동하지 않는다.

---

# 16. Queue inflation

동일 exact source key에서:

```text
queue_c4 - queue_c1
queue_c8 - queue_c1
```

및 필요하면 ratio를 계산한다.

c1 queue가 0 또는 매우 작을 경우 ratio는 불안정하므로 absolute delta를 primary로 사용한다.

필수:

```text
median queue delta c4-c1
P90 queue delta c4-c1
median queue delta c8-c1
P90 queue delta c8-c1
```

---

# 17. Execution-side TTFT retention

queue를 제외한 request-level execution-side TTFT를 c1/c4/c8에서 비교한다.

```text
execution_side_ttft_c4 / execution_side_ttft_c1
execution_side_ttft_c8 / execution_side_ttft_c1
```

P25/median/P75/P90를 계산한다.

이 metric은 다음 질문에 답해야 한다.

```text
Concurrency 증가 시 실제 admission 이후 first-token service time도 크게 악화되는가?
아니면 대부분의 증가가 queue에서 발생하는가?
```

---

# 18. Prefill scaling

동일 exact source key에서:

```text
prefill_c4 / prefill_c1
prefill_c8 / prefill_c1
```

을 계산한다.

입력 길이/캐시 hit 상황이 같은 request인지 validation한다.

특히 cache-hit/new-token workload가 concurrency별로 유사한지 확인한다.

---

# 19. Decode TPS retention

Weighted ITL 정의:

```text
weighted_itl_ms =
sum(itl_ms * (output_tokens - 1))
/
sum(output_tokens - 1)
```

Weighted decode TPS:

```text
weighted_decode_tps = 1000 / weighted_itl_ms
```

각 concurrency의 strict-decode common subset에서 계산한다.

c1 기준 retention:

```text
TPS_retention_c4 = TPS_c4 / TPS_c1
TPS_retention_c8 = TPS_c8 / TPS_c1
```

추가로 request-wise decode TPS ratio distribution:

```text
P25
median
P75
P90
```

을 계산한다.

---

# 20. E2E scaling

같은 output length strict subset에서:

```text
E2E c4/c1
E2E c8/c1
```

request-wise ratio P25/median/P75/P90를 계산한다.

E2E 증가가 TTFT 증가만으로 설명되는지 decode slowdown도 의미 있게 기여하는지 분리한다.

---

# 21. HTTP offered load reconstruction

각 concurrency에서 전체 AgentX request를 사용한다. Target root뿐 아니라 subagent HTTP request도 포함한다.

각 request interval:

```text
[start, end)
```

으로 sweep-line overlap을 계산한다.

필수:

```text
max_http_inflight
time_weighted_mean_http_inflight
P50 / P90 / P95 inflight
max_root_inflight
max_subagent_inflight
```

가능하면 각 target request 시작 시:

```text
http_inflight_at_start
root_inflight_at_start
subagent_inflight_at_start
```

도 계산한다.

생성:

```text
local_id03_c1_c4_c8_http_concurrency.csv
```

---

# 22. vLLM scheduler pressure

각 run에서 실제 runtime log를 이용하여 가능한 경우:

```text
running requests
waiting requests
```

시간축을 복원한다.

Configured limit와 observed count를 구분한다.

```text
configured max_num_seqs != observed max running
```

각 concurrency별:

```text
observed_max_running
observed_max_waiting
running P50/P90/P95
waiting P50/P90/P95
fraction observations waiting > 0
```

로그 sampling이 event-based라면 time-weighted라고 부르지 않는다.

생성:

```text
local_id03_c1_c4_c8_scheduler_summary.csv
```

---

# 23. Saturation / knee point 분석

c1 → c4 → c8에서 다음 metric curve를 비교한다.

```text
HTTP in-flight
scheduler running
scheduler waiting
TTFT
queue time
execution-side TTFT
prefill
weighted decode TPS
wall output throughput
```

다음 질문에 답한다.

```text
1. waiting이 처음 유의미하게 발생하는 지점은 어디인가?
2. queue time이 비선형적으로 증가하기 시작하는 지점은 어디인가?
3. TTFT 증가와 waiting 증가가 같은 방향으로 움직이는가?
4. decode TPS는 saturation에서도 얼마나 유지되는가?
5. prefill 자체가 느려지는가, 아니면 admission 전 대기가 주원인인가?
```

c1/c4/c8 세 점만 있으므로 정확한 mathematical knee를 과도하게 추정하지 않는다.

가능한 표현:

```text
no saturation observed by c4
pressure visible by c4
strong saturation by c8
```

등 evidence 기반 categorical conclusion을 사용한다.

---

# 24. Copy fairness

c4는 copy1~copy4, c8은 copy1~copy8이 존재하는 경우 다음을 분석한다.

Run별 copy metric:

```text
TTFT median
TTFT P90
queue mean/median
prefill mean
weighted decode TPS
E2E median
success count
```

copy-level CV:

```text
CV of TTFT median
CV of weighted decode TPS
CV of queue mean
```

동일 exact source key에서 copy간:

```text
TTFT CV
queue CV
prefill CV
ITL/TPS CV
```

의 median/P90를 계산한다.

이는 장기 copy fairness와 request-level scheduling jitter를 분리하기 위한 것이다.

---

# 25. Cache consistency

각 concurrency에서 실제 available cache metrics를 동일 semantics로 집계한다.

예:

```text
reusable/cache-hit tokens
external cache hit tokens
gross miss/write tokens
LMCache stored tokens
```

가능하면 per-root-copy normalized 값을 함께 계산한다.

다음 질문에 답한다.

```text
Concurrency에 따라 cache hit efficiency 자체가 의미 있게 악화되는가?
아니면 cache reuse는 유지되는데 queue만 증가하는가?
```

Cache counter semantics가 concurrency별로 동일함을 먼저 확인한다.

---

# 26. Wall throughput

각 run 전체에 대해:

```text
wall_span = max(request_end) - min(request_start)
wall_output_tps = total_output_tokens / wall_span
```

을 계산한다.

필요하면 root-copy normalized throughput도 계산한다.

c1 기준:

```text
wall_throughput_scaling_c4
wall_throughput_scaling_c8
```

을 산출한다.

Latency 악화와 throughput gain의 trade-off를 같이 본다.

---

# 27. Reliability

각 run에서:

```text
total requests
successful
failed
error category
server disconnection
context overflow
cancellation
```

을 별도로 집계한다.

단일 실패 row를 숨기지 않는다.

성능 summary에는 success filter를 명시하고 reliability summary에는 실패를 포함한다.

---

# 28. Primary result table

최종적으로 다음 구조의 summary를 만든다.

```text
local_id03_c1_c4_c8_primary_summary.csv
```

필수 컬럼 예:

```text
concurrency
root_copy_count
successful_request_count
failed_request_count

max_http_inflight
observed_max_running
observed_max_waiting

TTFT_median_ms
TTFT_p90_ms
queue_mean_ms
queue_median_ms
queue_share_requestwise_median
prefill_mean_ms
execution_side_ttft_median_ms

weighted_decode_tps
E2E_median_ms
wall_output_tps

cache_hit_ratio_or_status
```

---

# 29. Paired scaling summary

생성:

```text
local_id03_c1_c4_c8_paired_scaling.csv
```

최소 rows:

```text
c4_vs_c1
c8_vs_c1
c8_vs_c4
```

필수 metrics:

```text
matched_source_key_count
same_output_length_count
strict_ttft_count
strict_queue_count
strict_prefill_count
strict_decode_count
strict_e2e_count

TTFT request-wise ratio P25/median/P75/P90
queue absolute delta median/P90
execution-side TTFT ratio P25/median/P75/P90
prefill ratio median/P90
weighted decode TPS ratio
request-wise TPS ratio median
E2E request-wise ratio median/P90
```

---

# 30. Export-safe 결과파일

사용자가 외부 분석에 사용할 수 있는 반출 승인 범위가 있다면, raw/private field를 제거한 **export-safe summary/result 파일**을 별도로 생성한다.

파일명 권장:

```text
id03_local_c1_c4_c8_export_safe.csv
id03_local_c1_c4_c8_export_safe_summary.csv
```

Export-safe request-level 파일에 포함 가능한 최소 필드 예:

```text
local_concurrency
copy_index
public_exact_source_key
success
output_tokens
TTFT_ms
queue_ms
prefill_ms
execution_side_TTFT_ms
ITL_ms
E2E_ms
HTTP_inflight_at_start (가능 시)
scheduler_running_at_start (가능 시)
scheduler_waiting_at_start (가능 시)
```

제외:

```text
internal file paths
hostnames
IPs
credentials
internal request IDs
private model paths
server names
private worker identifiers
raw log text
```

Public exact source key는 이미 public workload provenance인 경우에만 포함한다.

반출 가능 여부는 사내 정책을 우선한다.

---

# 31. Public H200 reference는 optional secondary context

Public repository가 사내에서 읽기 가능하면 다음을 read-only reference로 사용할 수 있다.

```text
Repository: https://github.com/sskim-ai/InferenceX_analysis
Branch: analysis/h200-gpu-resident-mtp

studies/h200_gpu_resident_mtp/processed/id03_h200_reference_requests.csv
studies/h200_gpu_resident_mtp/reports/11_id03_deep_dive.md
studies/h200_gpu_resident_mtp/handoff/id03_local_join_contract.md
```

그러나 이번 task의 **primary goal은 local c1/c4/c8 controlled scaling analysis**이다.

Public H200와의 최종 cross-system conclusion은 별도 외부 분석 단계에서 수행한다.

사내 분석 결과를 GitHub에 쓰지 않는다.

---

# 32. 최종 한국어 보고서

사내 작업공간에:

```text
local_id03_c1_c4_c8_analysis_ko.md
```

를 생성한다.

구조:

```text
# 실험 검증

# System config consistency

# c1 baseline

# c1/c4/c8 offered load

# Scheduler running / waiting

# TTFT scaling

# Queue scaling

# Execution-side TTFT scaling

# Prefill scaling

# Decode TPS retention

# E2E / throughput tradeoff

# Copy fairness / jitter

# Cache behavior

# Reliability

# Saturation point interpretation

# Evidence

# Inference

# Unknown

# 외부 비교를 위해 반출 가능한 결과 항목
```

---

# 33. 최종적으로 반드시 답해야 할 질문

보고서 결론에서 명시적으로 답한다.

### A

```text
c1에서 queueing은 사실상 없는가, 아니면 이미 존재하는가?
```

### B

```text
c4에서 scheduler pressure / waiting이 의미 있게 발생하는가?
```

### C

```text
c8 TTFT 증가분 중 queue가 차지하는 비중은 얼마인가?
```

Primary는 request-wise queue/TTFT ratio distribution으로 답한다.

### D

```text
queue를 제외한 execution-side TTFT는 c1→c4→c8에서 얼마나 변하는가?
```

### E

```text
prefill time은 concurrency 증가에 따라 악화되는가?
```

### F

```text
decode TPS는 c1 대비 c4/c8에서 몇 % 유지되는가?
```

### G

```text
HTTP fan-out은 root concurrency보다 얼마나 큰가?
```

### H

```text
vLLM observed running limit과 waiting queue는 c1/c4/c8에서 어떻게 달라지는가?
```

### I

```text
현재 local server의 saturation은 compute slowdown, KV/cache miss, scheduler/admission queueing 중 어느 쪽 증거가 가장 강한가?
```

단일 원인으로 과장하지 말고 Evidence / Inference / Unknown으로 분리한다.

---

# 34. 완료 조건

```text
[ ] c1/c4/c8 run 정확히 식별
[ ] system configuration consistency 검증
[ ] request-level canonical table 생성
[ ] exact source-key normalization
[ ] coverage 분석
[ ] three-way common subset 생성
[ ] c1 baseline 적합성 판정
[ ] c4/c1 exact paired 분석
[ ] c8/c1 exact paired 분석
[ ] c8/c4 exact paired 분석
[ ] request-wise TTFT inflation
[ ] queue absolute inflation
[ ] execution-side TTFT scaling
[ ] prefill scaling
[ ] weighted decode TPS retention
[ ] E2E scaling
[ ] HTTP overlap reconstruction
[ ] running/waiting scheduler 분석
[ ] copy fairness / jitter
[ ] cache consistency
[ ] wall throughput scaling
[ ] reliability summary
[ ] primary summary CSV
[ ] paired scaling CSV
[ ] export-safe 결과파일(정책 허용 시)
[ ] 한국어 보고서
[ ] Git commit/push를 수행하지 않았음을 최종 확인
```

실제 사내 raw evidence를 사용해 분석을 끝까지 수행하고, 확인되지 않는 항목은 임의 추정하지 말고 `Unknown`으로 유지한다.
