# ID03 Exported Result Review — Local conc8 vs Public H200 c8

## 0. 목적

이 문서는 사내 원본 로그를 외부로 반출하지 않고, 사내에서 `id03_h200_reference_requests.csv`와 local `07dd405_cpy1~cpy8` 결과를 결합/가공한 **반출 가능한 결과파일**만으로 후속 상세 분석을 수행하기 위한 리뷰 지침이다.

이 문서 자체는 공개 GitHub에 versioning하지만, **사내 원본 로그·사내 request 원본·사내 결과파일은 이 repository에 commit/push하지 않는다.**

후속 분석 시 사용자는 반출 허용된 결과파일을 별도로 제공한다. 분석자는 그 파일만 읽고 아래 절차를 수행한다.

---

# 1. Public reference provenance

Public reference repository:

```text
https://github.com/sskim-ai/InferenceX_analysis
```

Branch:

```text
analysis/h200-gpu-resident-mtp
```

Primary public request reference:

```text
studies/h200_gpu_resident_mtp/processed/id03_h200_reference_requests.csv
```

Canonical ID03:

```text
07dd40536557a1d6440a923557c3129dc929
```

Primary public comparison point:

```text
H200 GPU-resident MTP c8
```

Supporting public reports:

```text
studies/h200_gpu_resident_mtp/reports/11_id03_deep_dive.md
studies/h200_gpu_resident_mtp/reports/12_id03_local_cpy_comparison_plan.md
studies/h200_gpu_resident_mtp/handoff/id03_local_join_contract.md
```

후속 분석자는 가능하면 branch의 최신 public reference를 다시 읽어 provenance를 확인한다. 다만 사용자가 제공한 반출 결과파일 안에 H200 reference column이 이미 포함되어 있다면 해당 column의 source/version도 우선 검증한다.

---

# 2. 보안 및 데이터 취급 원칙

다음은 절대 수행하지 않는다.

```text
- 사내 raw log를 요청하거나 외부 업로드하도록 지시
- 반출 결과파일을 GitHub repository에 commit/push
- hostname, internal IP, username, mount path, credential, token 등 내부 식별정보를 공개 repo에 기록
- 반출 허용 여부가 확인되지 않은 추가 사내 데이터를 요구
```

사용자가 제공한 반출 가능한 결과파일만 분석한다.

추가 raw evidence가 필요한 경우에도 “사내에서 확인해야 할 metric/판정식”만 설명하고, 원본 반출을 요구하지 않는다.

---

# 3. 실험 의미를 고정해서 해석

Local `cpy1~cpy8`은 현재 정의상 **global concurrency=8 실험 안의 8개 independent root copy/lane**이다.

따라서 다음 해석은 금지한다.

```text
cpy1 = concurrency 1
cpy2 = concurrency 2
...
cpy8 = concurrency 8
```

즉 `cpy8 / cpy1`을 concurrency scaling으로 계산하지 않는다.

Local에서 의미 있는 두 분석 단위는 다음과 같다.

### A. Focal-lane comparison

```text
Local conc8 / copy1
vs
Public H200 c8 / ID03
```

### B. Eight-copy distribution

```text
Local conc8 / copy1~copy8 전체
vs
Public H200 c8 / ID03
```

copy index는 같은 source request를 반복 관측한 independent local lane identifier로 유지한다.

---

# 4. Cross-system 비교의 의미

이번 비교는 **하드웨어 벤치마크가 아니라 observed serving-behavior comparison**이다.

두 시스템은 최소 다음이 다르다.

```text
Local:
- 2 GPU
- Aggregated serving
- local model/checkpoint
- local precision / KV architecture
- speculative/MTP state는 local exported metadata 기준
- global root concurrency 8
- same ID03 trace replicated across 8 copies

Public H200:
- 32 backend H200
- P/D disaggregated
- GLM-5.2 FP8
- FP8 E4M3 GPU-resident decode KV
- EAGLE MTP ON
- global concurrency 8
- mixed-root AgentX workload
```

따라서 다음 결론은 금지한다.

```text
- “2 GPU가 32 H200보다 X% 빠르다/느리다”
- “GPU 자체 성능이 X배 차이난다”
- “MTP 효과가 정확히 X배다”
- “KV residency 하나 때문에 X배 차이난다”
```

허용되는 표현:

```text
- 동일 source request에서 관측된 TTFT/ITL/E2E 차이
- local conc8 내부 copy-to-copy variability
- local queue/prefill/decode decomposition
- public H200와 local serving behavior의 observed system-level difference
```

---

# 5. 반출 결과파일의 권장 최소 schema

파일 형식은 CSV/Parquet/XLSX 중 하나여도 된다. 실제 컬럼명이 다르면 mapping table을 먼저 만든다.

## 5.1 Identity / exact join

가능한 경우 다음을 포함한다.

```text
local_copy_index
local_copy_label
source_trace_id
source_outer_idx
source_inner_idx
source_conversation_path
turn_index
exact_source_key
```

Public canonical exact key:

```text
source_trace_id + source_outer_idx + source_inner_idx
```

Root-level null inner index는 기존 public contract에 따라 normalized `-1`을 사용할 수 있다.

## 5.2 Outcome

```text
local_success
local_error_category
local_context_overflow
```

## 5.3 Token metrics

```text
local_input_tokens
local_input_token_semantics
local_output_tokens

h200_input_sequence_length
h200_source_input_tokens
h200_output_tokens
```

가능한 경우:

```text
local_cache_hit_tokens
local_cache_store_tokens
local_cache_metric_semantics
```

Cache metric은 public H200 request cache counter와 직접 동일하다고 가정하지 않는다.

## 5.4 Latency / decode

```text
local_ttft_ms
local_queue_ms
local_prefill_ms
local_itl_ms
local_weighted_decode_tps 또는 request_decode_tps
local_e2e_ms

h200_ttft_ms
h200_itl_ms
h200_decode_tps
h200_e2e_ms
```

가능하면 `local_queue_ms`와 `local_prefill_ms`는 서버가 직접 기록한 값인지, derived 값인지 별도 표시한다.

---

# 6. 파일 수신 즉시 수행할 Validation

분석 전에 데이터 integrity부터 확인한다.

## 6.1 Row count / copy coverage

확인:

```text
총 local observation 수
copy별 observation 수
copy별 성공 수
copy별 실패 수
source key distinct count
```

현재 실험 설계상 full coverage 기대치는 최대:

```text
119 source keys × 8 copies = 952 local observations
```

단, 실제 반출파일을 source of truth로 사용하고 952를 강제로 맞추지 않는다.

## 6.2 Duplicate semantics

같은:

```text
copy_index + exact_source_key
```

가 중복되는지 확인한다.

중복이 있으면:

```text
true replay duplicate
retry
export duplication
```

중 무엇인지 구분되지 않는 한 임의 dedup하지 않는다.

## 6.3 H200 join validation

각 local row에 H200 reference가 붙어 있다면:

```text
source_trace_id
source_outer_idx
source_inner_idx
```

가 H200 row와 일치하는지 확인한다.

가능하면:

```text
source_conversation_path
turn_index
```

도 validation field로 확인한다.

분류:

```text
high_confidence_exact
key_match_validation_missing
key_match_validation_conflict
unmatched
```

Conflict row는 strict paired comparison에서 제외한다.

## 6.4 Unit validation

TTFT/queue/prefill/ITL/E2E가 ms인지 s인지 반드시 검증한다.

TPS는:

```text
tok/s
```

단위로 통일한다.

---

# 7. Strict comparison subset 정의

## 7.1 Strict TTFT subset

다음을 모두 만족:

```text
high-confidence exact source-key match
local success
H200 success
local TTFT present
H200 TTFT present
```

Output length가 달라도 TTFT 비교에는 포함 가능하다.

## 7.2 Strict decode subset

다음을 모두 만족:

```text
Strict TTFT 조건
local output_tokens > 1
H200 output_tokens > 1
local ITL present
H200 ITL present
local output_tokens == H200 output_tokens
```

Output length가 다른 row는 decode TPS/ITL ratio에서 제외하고 별도 coverage 표에 보존한다.

## 7.3 Strict E2E subset

가능하면:

```text
exact source key
양쪽 성공
동일 output length
E2E present
```

을 primary E2E comparison으로 사용한다.

---

# 8. Primary Analysis 1 — Local copy1 vs H200 c8

가장 먼저 수행할 cross-system 분석이다.

`copy1`의 exact matched rows와 public H200 c8 ID03를 1:1로 맞춘다.

## 8.1 Coverage

계산:

```text
copy1 local rows
copy1 successful rows
H200 matched rows
strict TTFT rows
strict decode rows
strict E2E rows
same-output rows
output-length-different rows
```

## 8.2 TTFT paired comparison

각 exact key에 대해:

```text
local_ttft_ms
h200_ttft_ms
ratio = local / h200
delta_ms = local - h200
```

요약:

```text
median ratio
P25/P75 ratio
P90 ratio
median absolute delta
```

추가로 paired scatter 및 ratio-by-source-ordinal을 만든다.

## 8.3 Decode paired comparison

Strict decode subset에서:

```text
local_itl_ms
h200_itl_ms
ITL ratio = local / h200

local_decode_tps
h200_decode_tps
TPS ratio = local / h200
```

Primary aggregate decode metric은 양쪽 모두 가능한 경우 **output-transition-token-weighted ITL**로 계산한다.

```text
weighted_itl = sum(itl_ms * (output_tokens - 1)) / sum(output_tokens - 1)
weighted_decode_tps = 1000 / weighted_itl
```

비교:

```text
Local copy1 weighted TPS
H200 exact-subset weighted TPS
Local/H200 TPS ratio
```

전체 H200 119-request aggregate `90.454 tok/s`를 exact-subset 값 대신 사용하지 않는다 unless overlap이 119/119이고 output 조건도 동일하다.

## 8.4 E2E paired comparison

동일 output length subset에서:

```text
local_e2e / h200_e2e
```

median 및 P90 ratio를 계산한다.

---

# 9. Primary Analysis 2 — Local 8-copy distribution

같은 source key를 copy1~copy8에서 반복 실행한 결과를 이용해 local scheduler variability를 분석한다.

각 exact source key별로:

```text
copy_count_observed
success_count
TTFT median across copies
TTFT min/max
TTFT P25/P75
TTFT coefficient of variation
queue median/min/max
prefill median/min/max
ITL median/min/max
TPS median/min/max
E2E median/min/max
```

그리고 H200 동일 key 하나를 옆에 붙인다.

핵심 표:

```text
exact_source_key
local_8copy_ttft_median
local_8copy_ttft_p25
local_8copy_ttft_p75
h200_ttft

local_8copy_itl_median
h200_itl

local_8copy_e2e_median
h200_e2e
```

이 표는 copy1 하나가 우연히 유리/불리했는지를 판정하는 primary evidence다.

---

# 10. Copy fairness / scheduler bias 분석

각 copy별로 다음을 계산한다.

```text
success count
TTFT median/P90
queue mean/median/P90
prefill mean/median/P90
weighted ITL
weighted decode TPS
E2E median/P90
```

그리고 copy 간:

```text
range
standard deviation
coefficient of variation
rank consistency
```

를 계산한다.

질문:

```text
- 특정 copy가 지속적으로 낮은 queue를 받는가?
- 특정 copy가 지속적으로 높은 TTFT를 받는가?
- decode TPS도 copy별로 체계적인 차이가 있는가?
- copy 차이는 queue 차이로 대부분 설명되는가?
```

Source key fixed effect를 통제하기 위해 가능하면 각 key별 copy deviation도 계산한다.

예:

```text
copy_deviation_ttft = copy_ttft - source_key_local_copy_median_ttft
```

copy별 median deviation이 0에서 지속적으로 벗어나는지 본다.

---

# 11. Queue / Prefill / Decode 병목 분해

Local TTFT가 가능한 경우 다음처럼 분해되는지 검증한다.

```text
TTFT ≈ queue + prefill + residual/frontend/network
```

Request-level로:

```text
residual_ttft_ms = local_ttft_ms - local_queue_ms - local_prefill_ms
```

단, metric timer boundary가 정확히 호환되는지 먼저 확인한다.

Timer scope가 다르면 residual 계산을 하지 않고 별도 metric으로 유지한다.

분석:

```text
queue share of TTFT
prefill share of TTFT
residual share
```

각 source key 및 copy별로 본다.

Primary 질문:

```text
Local과 H200의 TTFT 차이가 local queue time으로 얼마나 설명되는가?
```

가능하면 counterfactual descriptive metric을 계산한다.

```text
local_ttft_minus_queue = local_ttft - local_queue
```

이를 H200 TTFT와 비교한다.

**주의:** 이것은 “queue가 없었을 때 실제 TTFT”라는 causal estimate가 아니라 단순 decomposition diagnostic이다.

---

# 12. Source progression / context-shape 분석

Source request ordinal 또는 exact key 순서에 따라:

```text
local TTFT
local queue
local prefill
local ITL
local output tokens
H200 TTFT
H200 ITL
```

그래프를 만든다.

질문:

```text
- trace 후반으로 갈수록 local queue가 증가하는가?
- prefill은 context progression에 따라 증가하는가?
- H200 TTFT와 local prefill은 비슷한 source-shape dependency를 보이는가?
- local decode ITL은 context progression에서 안정적인가?
```

Public `source_input_tokens`는 target local logical prompt와 동일하다고 해석하지 않는다. Source-shape proxy로만 사용한다.

---

# 13. Output-length effect 분석

Output length가 latency/TPS 비교를 왜곡하는지 확인한다.

Bucket 예시:

```text
2-32
33-128
129-512
513-2048
>2048
```

각 bucket에서:

```text
matched row count
local TTFT median
H200 TTFT median
local weighted TPS
H200 weighted TPS
E2E ratio
```

를 계산한다.

표본 n<3 bucket은 comparative conclusion에서 suppress하고 descriptive only로 표시한다.

---

# 14. Local cache 결과 분석

반출 결과파일에 local cache metric이 포함되어 있으면 local 내부 consistency만 우선 확인한다.

분석:

```text
cache-hit tokens
stored/miss tokens
cache-hit ratio
source key별 cache behavior
copy별 cache behavior
```

다음 관계를 본다.

```text
local cache hit tokens vs prefill
local cache hit ratio vs TTFT
local cache hit ratio vs queue
```

그러나 public H200 request-level cache counter는 scope가 검증되지 않았으므로 **local cache-hit tokens와 public raw cache counter의 직접 ratio는 계산하지 않는다.**

Public/local cache architecture가 다르면 “cache가 X배 좋다”는 결론을 내리지 않는다.

---

# 15. Failure 분석

Local 실패 row가 있으면 삭제하지 않는다.

별도 표:

```text
copy
exact_source_key
source ordinal
error category
local input/output info
인접 request의 queue/prefill/running 상태(반출파일에 있을 경우)
```

단일 server-disconnection 등 transport failure라면 성능 percentile에서는 제외할 수 있지만:

```text
performance exclusion
reliability observation
```

을 명확히 분리한다.

실패를 context overflow나 capacity failure로 오분류하지 않는다.

---

# 16. System-level concurrency evidence가 결과파일에 포함될 경우

다음 metric이 반출되어 있으면 함께 해석한다.

```text
root concurrency
HTTP request concurrency incl. subagents
vLLM running requests
vLLM waiting requests
scheduler queue depth
GPU utilization
KV usage
```

특히:

```text
queue_ms ↔ waiting depth
queue_ms ↔ running count
```

관계를 분석한다.

단, timestamp alignment가 없으면 aggregate maxima를 individual request latency의 causal explanation으로 사용하지 않는다.

---

# 17. 반드시 생성할 핵심 비교표

## Table A — System architecture/context

```text
Local vs H200
```

모델, GPU 수, topology, precision, MTP, KV/cache architecture, concurrency 의미를 나란히 놓는다.

## Table B — copy1 exact matched comparison

```text
matched keys
TTFT median/P90
weighted ITL
weighted TPS
E2E median/P90
output-length equality count
```

## Table C — local 8-copy summary

copy1~8 성능을 나란히 표시한다.

## Table D — 8-copy pooled / per-key median vs H200

같은 source request의 local distribution median을 H200 single observation과 비교한다.

## Table E — bottleneck decomposition

```text
Local TTFT
Local queue
Local prefill
Local decode ITL/TPS
H200 TTFT
H200 ITL/TPS
```

## Table F — reliability/coverage

```text
expected observations
observed
success
failure
matched H200 keys
strict TTFT rows
strict decode rows
```

---

# 18. 반드시 만들 그래프

반출 결과파일에 필요한 row-level 데이터가 있으면 다음을 만든다.

```text
1. Exact-key TTFT scatter: Local copy1 vs H200
2. Exact-key ITL scatter: Local copy1 vs H200
3. TTFT ratio vs source ordinal
4. Local queue/prefill/TTFT vs source ordinal
5. Copy1~8 TTFT distribution
6. Copy1~8 queue distribution
7. Copy1~8 weighted TPS
8. Per-key local 8-copy median TTFT vs H200
9. Output-length bucket TPS comparison
10. E2E paired comparison
```

한 그래프에서 서로 다른 의미의 metric을 과도하게 혼합하지 않는다.

---

# 19. 최종 결론에서 반드시 답할 질문

1. Local copy1과 H200 c8 ID03 사이 exact source-key overlap은 몇 개인가?
2. 그중 strict TTFT / strict decode / strict E2E sample은 몇 개인가?
3. 동일 request에서 local TTFT는 H200 대비 median 몇 배인가?
4. 동일 output-length request에서 local decode ITL/TPS는 H200 대비 어느 정도인가?
5. Local 8개 copy는 서로 얼마나 균일한가?
6. 특정 copy가 지속적으로 scheduler에서 유리/불리한 evidence가 있는가?
7. Local TTFT 중 queue가 차지하는 비중은 어느 정도인가?
8. Local/H200 TTFT 격차를 queue component가 얼마나 설명하는가?
9. Prefill 자체의 크기는 H200 TTFT와 비교했을 때 어느 정도인가?
10. Decode가 primary bottleneck인가, queue/prefill이 primary bottleneck인가?
11. Source progression에 따라 병목의 성격이 변하는가?
12. Local cache behavior는 기대한 reuse pattern과 일치하는가?
13. 실패 1건 등이 성능 결론에 영향을 주는가?
14. 모델/precision/MTP/topology 차이 때문에 어떤 결론까지 허용되고 어떤 결론은 금지되는가?

---

# 20. Evidence / Inference / Unknown 규칙

최종 보고서의 핵심 주장마다 아래 중 하나를 붙인다.

```text
Evidence
Inference
Unknown
```

예:

```text
Evidence:
exact matched request 100개에서 local TTFT median이 H200보다 X배 높음.

Inference:
local queue component가 TTFT 격차의 주요 contributor로 보임.

Unknown:
모델/engine/topology가 다르므로 GPU 자체의 순수 성능 차이는 분리할 수 없음.
```

---

# 21. 금지되는 분석 오류

다음은 하지 않는다.

```text
- aggregate 평균만으로 paired request comparison을 대체
- cpy index를 concurrency level로 해석
- output length가 다른 request의 decode TPS를 strict pair에 포함
- source_input_tokens를 local target logical context로 간주
- public raw cache counter를 local cache-hit token과 동일 metric으로 간주
- H200 전체 119-request TPS를 smaller exact subset의 TPS인 것처럼 사용
- local queue 제거값을 causal no-queue performance로 표현
- 모델 차이를 무시하고 GPU hardware superiority를 결론
- 실패 row를 조용히 삭제
- 반출 결과파일을 GitHub에 commit/push
```

---

# 22. 분석 결과 산출 형식

사용자가 반출 결과파일을 제공하면 최종 응답은 최소 다음 구조로 작성한다.

```text
# Executive Summary

# Data Validation / Coverage

# Local Experiment Verification

# Copy1 vs H200 Exact-Matched Comparison

# 8-Copy Distribution and Fairness

# Queue / Prefill / Decode Bottleneck Decomposition

# Source-Progression Analysis

# Output-Length-Controlled Decode Analysis

# Cache / Reliability Findings

# What the Public H200 Comparison Does and Does Not Show

# Evidence

# Inference

# Unknown

# Final Conclusion
```

수치가 있는 결론은 sample count와 denominator를 같이 명시한다.

---

# 23. 결과파일을 만들 때 가장 권장하는 형태

가능하면 한 행을:

```text
1 local copy × 1 exact source request
```

로 만든 long-form table이 가장 좋다.

즉 최대 약:

```text
8 copies × 119 source requests = 952 rows
```

형태다.

각 row에 H200 matched metric을 붙여도 되고, local/H200를 별도 table로 제공해도 된다.

추천 방식:

```text
local_id03_export.csv
- 1 row = local copy × source request
- local columns 포함
- exact_source_key 포함

id03_h200_reference_requests.csv
- public branch의 기존 파일 그대로
```

두 파일을 별도로 제공하는 방식이 가장 audit-friendly하다.

사내 정책상 H200 public row를 local export에 결합해 반출해야 한다면 combined file도 허용하지만, 반드시 `local_*` / `h200_*` prefix로 source를 명확히 분리한다.

---

# 24. 최종 원칙

**목표는 사내 원본을 반출하는 것이 아니라, exact source-key 기준으로 충분히 축약된 반출 결과만 사용해 Local conc8 ID03와 Public H200 c8 ID03의 serving behavior를 검증 가능한 방식으로 비교하는 것이다.**

Local 결과는 공개 repository에 저장하지 않는다. Public H200 reference만 GitHub provenance로 사용한다.
