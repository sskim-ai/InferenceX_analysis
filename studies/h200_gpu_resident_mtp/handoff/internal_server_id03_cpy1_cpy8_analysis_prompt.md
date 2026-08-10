# Internal GPT Final Task — `07dd405_cpy1~cpy8` Local Analysis and H200 ID03 Comparison

## 0. 목적

이 작업은 사내 2-GPU GLM 서버에서 이미 수행한 `07dd405_cpy1` ~ `07dd405_cpy8` 결과를 실제 raw log/config/result 파일에서 추출하고, 공개 H200 GPU-resident MTP benchmark의 동일 source trace와 request-level로 비교하는 최종 내부 분석 단계다.

방법론 설명이나 계획만 작성하지 말고, 현재 작업공간의 실제 파일을 재귀적으로 탐색·파싱하여 분석을 끝까지 수행하고 CSV/그래프/한국어 보고서를 생성하라.

외부 서비스에 사내 로그나 결과를 업로드하지 않는다. 인터넷 접근이 없어도 작업 가능한 범위까지 수행한다.

---

# 1. Primary trace

분석 대상 canonical source trace ID:

```text
07dd40536557a1d6440a923557c3129dc929
```

사용자가 처음 제공한 prefix:

```text
07dd405
```

공개 분석에서 위 prefix는 단 하나의 full source trace ID로 unique resolution되었다.

---

# 2. Local experiment의 현재 사용자 설명

사용자 설명상 사내 서버에는 **global concurrency=8 실행 안에서** 다음 copy 결과가 존재한다.

```text
07dd405_cpy1
07dd405_cpy2
07dd405_cpy3
07dd405_cpy4
07dd405_cpy5
07dd405_cpy6
07dd405_cpy7
07dd405_cpy8
```

현재 예상 의미:

```text
한 번의 concurrency=8 실험에서
동일한 07dd405 trajectory를 여러 독립 copy/lane으로 실행
cpy1~cpy8은 copy index
```

그러나 이 의미를 사용자 설명만으로 확정하지 말고 config/log에서 검증한다.

**중요:** `cpy1`, `cpy2`, ..., `cpy8`을 concurrency 1,2,...,8의 별도 실험이라고 해석하지 않는다. 사용자의 최신 설명은 `concurrency=8 결과 안의 copy1~copy8`이다.

따라서 다음 계산은 금지한다 unless raw evidence가 예상과 다르게 나타난다.

```text
cpy8 / cpy1 = concurrency scaling
cpyN = concurrency N
```

copy index와 concurrency는 별도 변수로 유지한다.

---

# 3. 현재 알려진 Local system 조건

사용자 제공 정보:

```text
GPU count: 2
Serving topology: Aggregated
Global test concurrency: 8 for the cpy1~cpy8 experiment
max_model_len: 202,752
Target workload: 07dd405...
```

`Aggregated` 의미:

```text
동일한 2개 GPU가 Prefill과 Decode를 모두 수행
```

아래 항목은 아직 raw evidence로 검증해야 한다.

```text
GPU exact SKU
exact model checkpoint
quantization / weight precision
TP / DP / PP / EP
KV dtype
KV page/block size
physical KV token slots / GPU
physical KV GiB / GPU
prefix/radix cache
CPU/KV offload
MTP/speculative decoding
max_num_batched_tokens / max_total_tokens
max_running_requests
scheduler configuration
```

---

# 4. Public H200 primary reference

Public repository analysis:

```text
Repository: https://github.com/sskim-ai/InferenceX_analysis
Branch: analysis/h200-gpu-resident-mtp
```

Primary public reference file if the repository checkout is available locally:

```text
studies/h200_gpu_resident_mtp/processed/id03_h200_reference_requests.csv
```

Local/H200 exact join contract:

```text
studies/h200_gpu_resident_mtp/handoff/id03_local_join_contract.md
```

ID03 deep-dive report:

```text
studies/h200_gpu_resident_mtp/reports/11_id03_deep_dive.md
```

Local comparison design:

```text
studies/h200_gpu_resident_mtp/reports/12_id03_local_cpy_comparison_plan.md
```

이 파일들이 사내 작업공간에 없다면 public request-level exact join은 수행할 수 없다고 표시하되, local raw 분석은 끝까지 수행한다. 아래의 embedded H200 aggregate reference를 사용하여 최소한 summary comparison은 수행한다.

---

# 5. Public H200 ID03 c8 embedded reference

H200 primary comparison point:

```text
System: GLM-5.2 FP8
Hardware: 32 backend H200
Topology: P/D disaggregated
Prefill: 2 workers × 8 H200
Decode: 2 workers × 8 H200
KV transfer: Mooncake
Decode KV: GPU-resident
HiSparse: OFF
KV dtype: FP8 E4M3
Context length: 1,048,576
MTP: EAGLE ON
Speculative steps: 3
Draft tokens: 4
Simulated acceptance length: 2.99
Global public concurrency: 8
Workload: mixed-root AgentX replay
```

ID03 c8 result:

```text
Canonical ID:
07dd40536557a1d6440a923557c3129dc929

Successful profiling requests: 119
Distinct exact source keys: 119
Coverage: 119 / 119 = 100%
Warmup ID03 requests: 0
Errors: 0
Cancellations: 0

TTFT mean: 2,709.924 ms
TTFT median: 1,080.570 ms
TTFT P90: 3,326.139 ms
TTFT P95: 6,497.038 ms

ITL-valid requests: 119
Weighted ITL: 11.055295 ms/token
Weighted decode TPS: 90.454390 tok/s

E2E median: 3,604.660 ms
E2E P90: 8,113.728 ms

Output tokens total: 37,635
ID03 wall span: 482.691 s
ID03 wall output rate: 77.969 tok/s
```

H200 c8 latency distribution:

```text
TTFT P10  = 797.231 ms
TTFT P25  = 938.143 ms
TTFT P50  = 1,080.570 ms
TTFT P75  = 1,655.558 ms
TTFT P90  = 3,326.139 ms
TTFT P95  = 6,497.038 ms
TTFT P99  = 37,471.151 ms

ITL P10   = 10.463 ms
ITL P25   = 10.635 ms
ITL P50   = 10.898 ms
ITL P75   = 11.809 ms
ITL P90   = 12.341 ms
ITL P95   = 13.642 ms
ITL P99   = 15.870 ms
```

Source-workload input proxy range:

```text
30,784 ~ 117,696 source tokens
```

이 source token은 target GLM logical context token과 동일하다고 해석하지 않는다.

---

# 6. Public H200 c12는 secondary reference

ID03 public c8↔c12에는 exact source key 112개가 공통이다.

같은 request 기준 observed ratio:

```text
Median TTFT c12/c8 ≈ 1.451×
Weighted ITL c12/c8 ≈ 1.0147×
Median ITL c12/c8 ≈ 0.9923×
```

즉 public H200에서 global concurrency 8→12 증가 시 동일 request의 TTFT는 증가하지만 active decode ITL은 거의 유지되는 패턴이 관측됐다.

이는 local concurrency=8 copy 간 비교의 직접 baseline은 아니다. Local result 해석의 secondary architectural context로만 사용한다.

Public c16은 ID03 13/119 late-tail keys만 profiling되므로 primary comparison에서 제외한다.

---

# 7. 가장 중요한 비교 질문

이번 분석의 핵심 질문은 다음이다.

1. Local `concurrency=8` 실험에서 실제로 8개의 independent copy/session이 동시에 존재했는가?
2. `cpy1~cpy8`은 같은 source trace를 독립적으로 실행한 8개 copy인가?
3. Local copy1은 public H200 c8의 ID03와 exact source request를 몇 개 공유하는가?
4. Local copy1과 H200 c8의 동일 request에서 TTFT/ITL/E2E가 얼마나 차이나는가?
5. Local copy1의 output length가 H200와 동일한 request는 몇 개인가?
6. Strict decode comparison에서 Local/H200 weighted TPS ratio는 얼마인가?
7. Local copy2~copy8도 같은 source keys를 수행했는가?
8. 같은 source request를 copy1~8에서 반복했을 때 copy-to-copy latency variability는 얼마나 되는가?
9. Local cpy8 실험에서 scheduler/queueing 때문에 특정 copy가 지속적으로 유리하거나 불리한가?
10. Local max_model_len=202752로 인해 특정 copy가 context overflow되었는가?
11. 모든 copy가 119 ID03 source keys를 완료했다면 public H200 c8와 119-key full exact comparison이 가능한가?
12. Local MTP/speculative decoding이 ON/OFF 중 무엇인가?
13. MTP가 H200와 다르면 TPS 차이를 hardware difference라고 부를 수 없는 이유는 무엇인가?
14. Local cache read/store counter와 public H200 counter가 동일 semantic scope인가?
15. 최종적으로 어떤 지표가 apples-to-apples에 가장 가깝고, 어떤 지표가 contextual only인가?

---

# 8. Local 파일 탐색

현재 사내 작업공간을 재귀적으로 탐색한다.

다음 이름/패턴을 우선 찾는다.

```text
07dd405
cpy1
cpy2
cpy3
cpy4
cpy5
cpy6
cpy7
cpy8
profile_export
server_metrics
benchmark
server
frontend
scheduler
worker
config
yaml
yml
json
jsonl
csv
log
stdout
stderr
```

가능한 파일:

```text
profile_export.jsonl
profile_export_aiperf.json
profile_export_aiperf.csv
server_metrics_export.json
server_metrics_export.csv
benchmark_command.txt
benchmark.log
server.log
frontend.log
scheduler.log
worker logs
launch script
config YAML/JSON
GPU telemetry
```

파일명이 예상과 달라도 content keyword로 탐색한다.

---

# 9. Local runtime configuration 확정

먼저 다음 표를 만든다.

| field | local value | evidence source | classification |
|---|---|---|---|

필수 field:

```text
target_model
model_revision/checkpoint
weight_precision/quantization
GPU SKU
GPU count
TP
DP
PP
EP
topology aggregated/disaggregated
configured concurrency
observed max simultaneous requests
max_model_len
max_total_tokens
max_num_batched_tokens
max_running_requests
KV dtype
KV page/block size
KV physical token slots/GPU
KV physical GiB/GPU
prefix/radix cache
CPU/KV offload
MTP/speculative algorithm
speculative steps
draft tokens
acceptance config
attention backend
```

모든 항목을:

```text
Evidence
Inference
Unknown
```

중 하나로 표시한다.

---

# 10. `cpy1~cpy8` 의미를 실제로 검증

다음 표를 만든다.

| copy | configured_concurrency | independent_root_sessions | distinct_conversation_ids | source_trace_ids | first_start | last_end | successful_requests | failed_requests |
|---|---:|---:|---:|---|---|---|---:|---:|

그리고 다음을 계산한다.

```text
observed_max_simultaneous_requests
observed_max_simultaneous_root_sessions
```

동시성은 request interval overlap을 이용해 가능한 한 실제로 검증한다.

예:

```text
request_start <= time < request_end
```

에 활성인 request 수의 최대값.

최종적으로 다음 중 하나로 판정한다.

```text
verified_global_concurrency_8_with_8_same_trace_copies
configured_concurrency_8_but_observed_concurrency_lower
cpy_labels_not_independent_sessions
semantics_partially_verified
unknown
```

---

# 11. Copy identity 보존

각 local request에는 반드시 다음 컬럼을 만든다.

```text
local_run_label
local_copy_label
local_copy_index
```

예:

```text
local_copy_label = 07dd405_cpy1
local_copy_index = 1
```

copy index는 exact source request key에 포함하지 않는다.

같은 source request를 8개 copy가 수행한 것은 duplicate가 아니라 8개의 독립 관측값이다.

---

# 12. Canonical local request table

최소 다음 컬럼을 가진 table을 만든다.

```text
local_run_label
local_copy_label
local_copy_index
configured_concurrency

source_trace_id
source_outer_idx
source_inner_idx
source_conversation_path
source_branch_type
source_branch_request_index
turn_index

conversation_id
session_num

request_id
correlation_id
worker_id

request_start
request_end

input_tokens
input_token_semantics
requested_output_limit
output_tokens

cache_read_tokens
cache_read_metric_semantics
cache_write_tokens
cache_write_metric_semantics

logical_prompt_tokens
logical_prompt_semantics

TTFT_ms
ITL_ms
E2E_ms

success
error
error_text_or_category
context_overflow

exact_source_key
match_validation_status
```

원본 field 이름과 canonical field 이름의 mapping table도 생성한다.

---

# 13. Exact source key

Primary exact key:

```text
source_trace_id
+ source_outer_idx
+ source_inner_idx
```

canonical string:

```text
<source_trace_id>|<source_outer_idx>|<source_inner_idx_normalized>
```

Root-level null `source_inner_idx`만 documented sentinel `-1`로 normalize할 수 있다.

실제 local value가 단순 missing/unknown이라면 임의로 -1을 넣지 않는다.

Validation field:

```text
source_conversation_path
turn_index
```

match status:

```text
high_confidence_exact
key_match_validation_missing
key_match_validation_conflict
unmatched
```

Conflict row는 strict comparison에서 제외한다.

---

# 14. 각 copy의 source coverage

cpy1~cpy8 각각에 대해 다음을 계산한다.

```text
all request count
successful request count
failed request count

first exact source key
last successful exact source key
first failed exact source key

distinct exact source key count
coverage out of public 119 keys

source_request_index min/max
source_outer_idx min/max
branch count

context overflow count
```

표:

| copy | successful keys | public-119 coverage | last success | first fail | overflow |
|---|---:|---:|---|---|---|

---

# 15. Context overflow / 202,752 분석

Local max model length:

```text
202,752
```

각 실패/overflow request에서 가능한 한 다음을 추출한다.

```text
logical prompt tokens
requested output limit
prompt + requested output
max_model_len
margin to limit
server error text
```

중단 rule을 판별한다.

```text
prompt_tokens > 202752
prompt + requested_output > 202752
loader filter
KV pool shortage
scheduler capacity
OOM
other
```

**중요:** public H200 profile에는 request-level target logical prompt token이 없으므로 public `input_sequence_length` 또는 `source_input_tokens`를 202752 cutoff에 사용하지 않는다.

Local에서 실제 성공한 exact key 집합을 기준으로 public H200 reference를 역필터한다.

즉 copy별로:

```text
comparison_keys_copyN
=
Local successful high-confidence exact keys
INTERSECTION
H200 c8 ID03 exact keys
```

이것이 context-compatible comparison의 실제 기준이다.

---

# 16. Primary comparison A — Local cpy1 vs H200 c8 ID03

가장 먼저 `copy1`을 focal lane으로 비교한다.

이 비교의 의미:

```text
Local: global concurrency=8 환경의 07dd405 copy1
vs
H200: mixed-root global concurrency=8 환경의 ID03 lane
```

둘의 workload composition은 동일하지 않으므로 `same-global-concurrency focal-lane comparison`으로 표현한다.

H200 public reference file이 있으면 exact key로 inner join한다.

Strict TTFT subset:

```text
high_confidence exact key
both success
both TTFT present
```

Strict decode subset:

```text
strict TTFT subset
both output_tokens > 1
both ITL present
same observed output length
```

Strict E2E subset:

```text
high-confidence exact
both success
same output length
both E2E present
```

---

# 17. cpy1 vs H200 request-level output

다음 파일을 만든다.

```text
local_id03_output/processed/cpy1_vs_h200_c8_exact_requests.csv
```

컬럼:

```text
exact_source_key
source_outer_idx
source_inner_idx
source_conversation_path
turn_index

local_output_tokens
h200_output_tokens
same_output_length

local_ttft_ms
h200_ttft_ms
ttft_ratio_local_over_h200

local_itl_ms
h200_itl_ms
local_decode_tps
h200_decode_tps
itl_ratio_local_over_h200

local_e2e_ms
h200_e2e_ms
e2e_ratio_local_over_h200

local_input_tokens
local_input_semantics
h200_input_sequence_length
h200_source_input_tokens

match_validation_status
strict_ttft_subset
strict_decode_subset
strict_e2e_subset
```

---

# 18. cpy1 vs H200 summary

다음 표를 만든다.

| metric | Local cpy1 | H200 c8 matched subset | Local/H200 ratio | n |
|---|---:|---:|---:|---:|

필수:

```text
matched exact source keys
strict TTFT count
strict decode count
strict E2E count

TTFT mean
TTFT median
TTFT P90
TTFT P95

weighted ITL
weighted decode TPS
median ITL

E2E median
E2E P90

output tokens total on strict/common set
```

**TTFT ratio는 request-wise ratio median과 aggregate median ratio를 둘 다 계산하고 구분한다.**

**TPS ratio는 weighted ITL에서 계산한 aggregate ratio와 request-wise TPS ratio median을 구분한다.**

---

# 19. Primary comparison B — Local copy1~8 전체 분포 vs H200 c8

copy1 하나가 scheduler에서 우연히 유리/불리할 수 있으므로 8개 copy 전체를 분석한다.

각 exact source key마다 local 8-copy 분포를 만든다.

예:

```text
exact key X
local copy1 TTFT
local copy2 TTFT
...
local copy8 TTFT

local median TTFT
local P25/P75 TTFT
local min/max TTFT
local CV or robust dispersion

H200 TTFT
```

생성:

```text
local_id03_output/processed/per_source_key_local_copy_distribution_vs_h200.csv
```

필수 local distribution:

```text
copy observation count
median
P25
P75
IQR
min
max
MAD if practical
CV only when mean > 0 and metric meaning allows
```

TTFT/ITL/E2E 각각 생성한다.

---

# 20. Copy-to-copy fairness / scheduler variability

각 copy별 성능을 비교한다.

표:

| copy | exact success keys | median TTFT | P90 TTFT | weighted TPS | E2E median | wall span |
|---|---:|---:|---:|---:|---:|---:|

다음 질문에 답한다.

```text
특정 copy가 지속적으로 느린가?
copy index와 TTFT 사이 monotonic pattern이 있는가?
copy별 output mix 차이가 큰가?
copy별 request coverage가 동일한가?
copy별 start timing이 다른가?
```

단순 copy index correlation은 sample size와 실험 의미를 고려하여 descriptive로만 사용한다.

---

# 21. Local concurrency=8 aggregate

local 8-copy 전체 시스템 관점으로 다음을 계산한다.

```text
total successful requests
total output tokens
run wall span
system wall output TPS

TTFT median/P90 across all copies
weighted decode TPS across all valid decode rows
```

그러나 이 aggregate를 **H200 ID03-only wall output TPS 77.969**와 직접 비교하지 않는다.

이유:

```text
Local aggregate = 8 copies of same ID03 workload
H200 ID03-only = one ID03 trajectory inside mixed-root shared c8 run
```

필요하면 public H200 full-system c8 aggregate와 contextual comparison을 별도 표로 제공하되 hardware/topology/MTP/workload 차이를 크게 표시한다.

---

# 22. MTP / speculative decoding 검증

Public H200 c8은 EAGLE MTP ON이다.

Local에서 다음을 반드시 찾는다.

```text
speculative_algorithm
MTP
EAGLE
num_steps
draft_tokens
acceptance_length
acceptance_rate
```

판정:

```text
local_mtp_equivalent
local_speculative_different
local_non_speculative
unknown
```

Local이 non-MTP라면:

```text
Local TPS / H200 TPS
```

는 **observed serving-system difference**로만 표현한다.

금지:

```text
2 GPU가 H200보다 X% 빠르다
GPU compute 자체가 X배 빠르다
```

TTFT도 P/D topology 차이 때문에 pure hardware latency로 해석하지 않는다.

---

# 23. KV cache 분석

Local startup/runtime log에서:

```text
KV dtype
page/block size
physical token slots/GPU
physical KV GiB/GPU
max running requests
prefix/radix cache
CPU/offload
```

를 추출한다.

`max_model_len`과 `physical KV pool token slots`를 동일 개념으로 취급하지 않는다.

Public H200 reference:

```text
max context = 1,048,576
decode runtime-profiled token value = 218,560
FP8 E4M3
~12.51 GiB primary + 0.16 GiB secondary per logged decode rank
```

218,560은 public max_model_len이 아니다.

---

# 24. Cache read / store metric 안전 규칙

Public H200 request-level profile cache counter는 semantic scope가 검증되지 않았고 일부 aggregate에서 prompt tokens보다 큰 값을 가질 수 있다.

따라서 public request `cache_read_tokens`를 physical KV load 또는 validated logical cache hit로 해석하지 않는다.

Local cache counter도 다음을 기록해야 한다.

```text
raw field name
unit
scope
per request / per session / cumulative
logical / physical
reset behavior
```

다음 조건을 만족할 때만 cross-system ratio를 계산한다.

```text
same semantic definition
same unit
same reset/scope
```

아니면:

```text
not comparable
```

로 표시한다.

Store도 명시적 `cache_write_tokens`가 없으면 실제 physical store 수를 추정하지 않는다.

---

# 25. TTFT 분석

Local copy별 및 strict matched subset에서:

```text
count
mean
P10
P25
median
P75
P90
P95
P99
max
```

을 계산한다.

H200 c8 reference 분포와 같은 quantile을 맞춘다.

그래프:

```text
copy별 TTFT box/violin 또는 quantile plot
cpy1 vs H200 exact request scatter
local all-copy median per source key vs H200 scatter
TTFT ratio vs source request ordinal
```

---

# 26. ITL / Decode TPS 분석

Valid decode row:

```text
output_tokens > 1
ITL > 0
```

Weighted ITL:

```text
sum(ITL_ms * (output_tokens - 1))
/
sum(output_tokens - 1)
```

Weighted decode TPS:

```text
1000 / weighted_ITL_ms
```

copy별로 계산하고, all-copy strict matched subset도 계산한다.

Output length가 H200와 다르면 strict cross-system decode subset에서 제외한다.

---

# 27. E2E 분석

Strict E2E comparison은 같은 source key + 같은 observed output length를 우선한다.

Output length가 다른 row는 별도 coverage table에 남기되 E2E speed ratio 결론에서는 제외한다.

---

# 28. Source request ordinal 분석

Local/H200 모두 source request progress에 따라:

```text
TTFT
ITL
E2E
output tokens
local logical prompt tokens if available
```

를 시각화한다.

특히 local에서 202,752 context 접근 시 latency가 증가하거나 overflow가 발생하는지 확인한다.

---

# 29. Local copy1이 119개를 모두 성공한 경우

copy1이 public ID03 119 exact keys를 모두 성공하면 가장 좋은 비교다.

이 경우 반드시 다음 결과를 별도 강조한다.

```text
119 / 119 full-trace exact comparison
```

표:

| metric | Local cpy1 | H200 c8 | ratio |
|---|---:|---:|---:|

그리고 request-wise ratio distribution을 제공한다.

---

# 30. Local copy별 coverage가 다를 경우

각 copy마다 자신의 intersection set을 사용한다.

그러나 copy 간 성능을 비교할 때 workload mix가 달라지는 것을 막기 위해 추가로:

```text
all-8-copy common exact key set
```

을 만든다.

즉:

```text
common_keys_all_local_copies
= intersection(copy1_success_keys ... copy8_success_keys)
```

그리고 H200에도 존재하는:

```text
strict_common_keys
= common_keys_all_local_copies ∩ h200_c8_keys
```

를 이용한 fairness table을 별도로 만든다.

이것이 copy-to-copy 성능 비교의 primary subset이다.

---

# 31. Output length equality 분석

각 copy별로 public H200와 exact key가 맞더라도 output length가 동일한지 확인한다.

다음 비율을 보고한다.

```text
exact key overlap count
same output length count
same output length ratio
```

MTP/모델 설정이 다르면 output length가 달라질 수 있으므로 매우 중요하다.

---

# 32. Public c8 mixed workload와 Local same-trace copies 차이

최종 보고서에 반드시 다음 차이를 명시한다.

```text
Public H200 c8:
- mixed-root workload
- one observed ID03 trajectory among other roots
- 32 H200
- P/D disaggregated
- EAGLE MTP

Local concurrency=8:
- expected eight copies of same 07dd405 trace
- 2 GPU
- Aggregated
- MTP state must be verified
- max_model_len 202752
```

따라서 comparison level을 분리한다.

### Level 1 — High-value paired comparison

```text
same source request
same observed output length
local cpy1 vs H200 c8
```

### Level 2 — Local replicate variability

```text
same source request across local copy1~8
```

### Level 3 — Contextual serving-system comparison

```text
Local all-copy aggregate vs public full-system numbers
```

Level 3는 hardware benchmark라고 부르지 않는다.

---

# 33. 생성할 산출물

```text
local_id03_output/
├── inventory/
│   ├── local_file_inventory.csv
│   └── schema_mapping.csv
├── processed/
│   ├── local_runtime_configuration.csv
│   ├── local_cpy_semantics.csv
│   ├── local_requests_all.csv 또는 parquet
│   ├── local_requests_success.csv 또는 parquet
│   ├── local_copy_coverage.csv
│   ├── local_copy_metrics.csv
│   ├── local_all_copy_common_keys.csv
│   ├── cpy1_vs_h200_c8_exact_requests.csv
│   ├── cpy1_vs_h200_c8_summary.csv
│   ├── all_copies_vs_h200_summary.csv
│   ├── per_source_key_local_copy_distribution_vs_h200.csv
│   ├── local_context_overflow_analysis.csv
│   ├── local_kv_cache_configuration.csv
│   ├── cache_metric_semantics.csv
│   └── unmatched_or_conflicting_requests.csv
├── figures/
│   ├── copy_ttft_distribution.png
│   ├── copy_weighted_tps.png
│   ├── cpy1_vs_h200_ttft_scatter.png
│   ├── cpy1_vs_h200_itl_scatter.png
│   ├── per_key_local_median_vs_h200_ttft.png
│   ├── ttft_ratio_vs_source_ordinal.png
│   ├── local_context_growth_vs_ordinal.png
│   └── copy_coverage.png
└── reports/
    ├── 01_local_environment.md
    ├── 02_cpy_semantics.md
    ├── 03_local_coverage.md
    ├── 04_cpy1_vs_h200_exact.md
    ├── 05_copy_variability.md
    ├── 06_context_overflow.md
    ├── 07_kv_cache.md
    ├── 08_cache_metric_semantics.md
    ├── 09_limitations.md
    └── results_summary_ko.md
```

Parquet이 어려우면 CSV를 사용한다.

---

# 34. 최종 한국어 보고서

`local_id03_output/reports/results_summary_ko.md` 구조:

```text
# Executive Summary

# Local 2-GPU Runtime Architecture

# cpy1~cpy8 의미 검증

# Source Coverage

# Context 202752 영향

# Primary: Local cpy1 vs H200 c8 Exact Comparison

# Local copy1~8 Replicate Variability

# TTFT

# ITL / Weighted Decode TPS

# E2E

# Output-Length Equality

# KV Cache

# Cache Read / Store Metric Semantics

# What Is Directly Comparable

# What Is Contextual Only

# Evidence

# Inference

# Unknown

# Final Conclusion
```

---

# 35. 최종 보고서에서 반드시 답할 질문

1. cpy1~cpy8은 정말 한 concurrency=8 run 안의 8개 independent copy인가?
2. 실제 observed max concurrency는 얼마인가?
3. 각 copy는 public ID03 119 source key 중 몇 개를 성공했는가?
4. copy1은 119개 전부 성공했는가?
5. copy1과 H200 c8의 high-confidence exact overlap은 몇 개인가?
6. strict same-output TTFT/decode/E2E subset은 각각 몇 개인가?
7. copy1 median TTFT vs H200 c8 1.081s는 어떻게 다른가?
8. copy1 P90 TTFT vs H200 c8 3.326s는 어떻게 다른가?
9. copy1 weighted decode TPS vs H200 90.454 tok/s는 어떻게 다른가?
10. Local MTP state는 무엇인가?
11. MTP가 다를 경우 TPS ratio를 어떻게 해석해야 하는가?
12. copy2~8은 copy1 대비 체계적으로 느리거나 빠른가?
13. all-8-copy common key subset에서 copy별 TTFT 분포는 어떤가?
14. source request 진행에 따라 local TTFT가 증가하는가?
15. 202752 context overflow가 발생한 copy/request는 무엇인가?
16. Local physical KV pool은 token slots/GiB 기준 얼마인가?
17. cache read/store counter는 public H200와 semantic-equivalent인가?
18. 가장 apples-to-apples에 가까운 최종 comparison subset은 무엇인가?
19. Local과 H200의 어떤 성능 차이는 hardware 자체 차이라고 말할 수 없는가?
20. 최종적으로 local server의 강점/병목은 Prefill/TTFT 쪽인가 Decode/ITL 쪽인가?

---

# 36. 해석 우선순위

최종 결론은 다음 순서로 신뢰한다.

```text
1. Same source key + same output length request-level pair
2. Same source key request-level TTFT pair
3. Local all-copy common-key replicate comparison
4. Copy-level matched aggregate
5. Whole-run contextual aggregate
```

위쪽일수록 강한 evidence다.

---

# 37. 금지된 결론

다음을 하지 않는다.

```text
cpy8이므로 concurrency 8이라고 이름만 보고 확정
copy1~copy8을 concurrency 1~8 scaling으로 해석
H200 c8과 local cpy8 workload가 동일하다고 주장
Local TPS/H200 TPS를 GPU hardware ratio라고 주장
MTP ON/OFF 차이를 무시
P/D disaggregated와 Aggregated 차이를 무시
source_input_tokens를 target logical context로 사용
public raw cache counter를 physical KV load로 해석
max_model_len과 KV pool capacity를 동일시
output length가 다른 E2E를 strict comparison에 포함
copy instance를 duplicate request로 제거
```

---

# 38. Evidence / Inference / Unknown

모든 주요 결과에 다음 classification을 붙인다.

```text
Evidence
Inference
Unknown
```

예:

```text
Evidence:
server config에 max_model_len=202752

Evidence:
cpy1~8 각기 다른 conversation ID로 동시에 실행됨

Inference:
높은 TTFT가 queueing/prefill pressure에 의해 발생했을 가능성

Unknown:
public/private cache counter의 semantic equivalence
```

---

# 39. 데이터 부족 처리

필드가 없다고 전체 작업을 중단하지 않는다.

예:

```text
KV physical token slots 없음
→ Unknown
→ 나머지 TTFT/ITL exact comparison 계속
```

Public H200 request CSV가 없다면:

```text
local 분석 완료
embedded aggregate H200 comparison 완료
request-level H200 exact join unavailable
필요 public file path 명시
```

으로 종료한다.

---

# 40. 완료 조건

다음이 모두 충족되어야 완료다.

```text
[ ] local 파일 inventory
[ ] exact model/GPU/topology config 확인
[ ] max_model_len=202752 확인
[ ] MTP/speculative state 확인
[ ] KV config/runtime evidence 추출
[ ] cpy1~8 의미 검증
[ ] observed concurrency 계산
[ ] copy identity 보존 canonical table 생성
[ ] 각 copy source coverage 계산
[ ] context overflow 분석
[ ] local exact key 생성
[ ] H200 reference가 있으면 exact join
[ ] cpy1 vs H200 strict TTFT comparison
[ ] cpy1 vs H200 strict decode comparison
[ ] cpy1 vs H200 strict E2E comparison
[ ] all-copy common-key subset 생성
[ ] copy-to-copy variability 분석
[ ] TTFT 분포 분석
[ ] weighted ITL/TPS 분석
[ ] output length equality 분석
[ ] cache metric semantics 검증
[ ] CSV/그래프 생성
[ ] results_summary_ko.md 생성
[ ] Evidence/Inference/Unknown 구분
```

---

# 41. 최종 응답 형식

분석 완료 후 대화 응답에 아래만 간결하게 요약한다.

```text
1. Local runtime architecture
2. cpy1~8 semantics 판정
3. observed concurrency
4. copy별 source coverage
5. cpy1 ↔ H200 exact match counts
6. cpy1 ↔ H200 TTFT
7. cpy1 ↔ H200 weighted decode TPS
8. all-copy variability 핵심 결과
9. context overflow 결과
10. KV cache 결과
11. directly comparable metrics
12. non-comparable/contextual metrics
13. generated output paths
```

계획만 작성하지 말고 현재 작업공간의 실제 파일을 읽어 분석을 시작하라.
