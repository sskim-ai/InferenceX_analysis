# 14. Local conc1 / Local conc8 / InferenceX — ID03 System Comparison

## 0. Scope

Canonical AgentX source trace:

```text
07dd40536557a1d6440a923557c3129dc929
```

이 문서는 다음 세 결과를 한 표에서 바로 복사해 사용할 수 있도록 정리한다.

1. **Local conc1** — 사내 2×H200 NVL, ID03 단일 trajectory
2. **Local conc8** — 동일 사내 서버에서 같은 ID03 trajectory를 8-copy로 동시 실행
3. **InferX** — Public InferenceX 32×H200 GPU-resident MTP c8에서 수행된 ID03

Local 값은 사용자가 제공한 export-safe 요약값만 기록하며, 사내 raw log/path/hostname/IP 등은 저장하지 않는다.

중요: 세 환경은 동일 GPU 하드웨어 벤치마크가 아니다. 모델, precision, topology, MTP, KV 계층, GPU 수, 실제 offered load가 다르므로 **serving-system behavior comparison**으로 해석한다.

---

# 1. 복사용 핵심 분석 결과표

> 기본 표기는 `Local conc1 | Local conc8 | InferX 결과` 순서로 통일한다.
>
> **중요:** InferX의 `HTTP P90=7`, prefill TP/CP rank envelope, decode DP-shard cluster running은 서로 다른 metric/scope다. Decode-stage cluster는 max **17**, P90 **10**으로 재구성됐지만, prefill unique union과 P/D 전체 unique global running/waiting 총합은 여전히 **Unknown**이다.

## 1.1 환경 및 성능

| Metric | Local conc1 | Local conc8 | InferX 결과 |
| --- | ---: | ---: | ---: |
| GPU | 2× NVIDIA H200 NVL | 2× NVIDIA H200 NVL | 32 backend H200 |
| Model | GLM-4.7-Flash | GLM-4.7-Flash | GLM-5.2-FP8 |
| Weight dtype / quantization | BF16 / none | BF16 / none | FP8 model |
| Serving topology | Aggregated, TP2 | Aggregated, TP2 | P/D disaggregated, 2P×8 + 2D×8 |
| MTP / speculative decoding | OFF | OFF | EAGLE MTP ON, steps=3, draft=4, acceptance length ≈2.99 |
| Max model length | 202,752 | 202,752 | 1,048,576 |
| KV block/page | 16 tokens | 16 tokens | 64 tokens |
| GPU KV runtime capacity | 258,864 tokens/rank | 258,864 tokens/rank | 218,560 tokens/logged decode rank |
| Approx. primary KV footprint | ≈52.9 KiB/token/rank | ≈52.9 KiB/token/rank | ≈60 KiB/token/rank |
| External KV tier | LMCache CPU + disk | LMCache CPU + disk | none, decode KV GPU-resident |
| ID03 exact request coverage | 119/119 | copy1 119/119 | 119/119 |
| Same output length vs InferX | exact pair 비교 대상 | copy1 119/119 | 119/119 reference |
| TTFT median | **0.563 s** | **26.682 s** (copy1 26.69 s) | **1.081 s** |
| Queue median | **0.012 s** | **24.385 s** | prefill histogram median ≈0.0024–0.0027 s; decode ≈0.00017–0.00019 s* |
| Prefill median | 0.531 s | 1.221 s | request-level 동일 metric 미분리 |
| TTFT − queue mean proxy | **0.770 s** | **1.812 s** | observed TTFT 1.081 s; typical queue는 매우 낮음* |
| Weighted decode TPS | **93.05 tok/s** | **61.71 tok/s**; exact copy1 **59.15** | **90.45 tok/s** |
| System wall output TPS | 53.62 tok/s | 130.73 tok/s | c8 전체 mixed workload **210.51 tok/s** |
| ID03 trajectory wall time | **11m 57s = 717 s** | 아직 별도 trajectory wall-time export 없음 | **8m 02.7s = 482.69 s** |
| Local/runtime cache-hit ratio | 95.00% | 94.86% | 동일 의미 counter로 직접 비교하지 않음 |
| External share of cached KV | 1.07% | 99.99% | N/A — GPU-resident KV |
| KV usage P95 | 72.5% | 98.0% | decode token-usage rank-series P95 약 91–93%* |
| GPU utilization avg | 52.2% | 86.3% | 동일 scope 값은 현재 비교표에 미포함 |
| Logical KV load per ID03 trajectory | ≈9.407M tokens | ≈9.407M tokens/copy | ≈9.407M tokens, trace-equivalent logical workload |
| Logical KV new/store per ID03 trajectory | ≈0.493M tokens | ≈0.493M tokens/copy | ≈0.493M tokens, trace-equivalent logical workload |

\* InferX queue/KV 숫자는 endpoint/rank-series scope이며 Local의 global metric과 동일 scope가 아니다.

## 1.2 동시성 / scheduler / queue — 반드시 scope를 구분해서 읽기

| Metric | Local conc1 | Local conc8 | InferX 결과 | Scope / 읽는 법 |
| --- | ---: | ---: | ---: | --- |
| Root concurrency / copies | 1 | 8 | 8 root lanes | workload-generator 설정 |
| Workload composition | ID03 1 trajectory | 동일 ID03 8 copies | mixed-root c8 안의 ID03 1 trajectory | root 수가 같아도 fan-out은 다를 수 있음 |
| **HTTP in-flight max** | **4** | **29** | **11** | request-plane에서 동시에 살아 있던 HTTP/profile request 수 |
| HTTP in-flight time-weighted mean | 미산출 | 미산출 | **3.97** | InferX 전체 c8 957 profile request 기준 |
| HTTP in-flight P90 | 미산출 | 미산출 | **7** | **running=7이라는 뜻이 아님.** 시간의 90%에서 HTTP in-flight ≤7이라는 뜻 |
| HTTP in-flight P95 | 미산출 | 미산출 | **8** | scheduler running 수와 다른 metric |
| **Scheduler running — global/cluster total** | **max 4** | **max 7** | **unique P/D global Unknown** | Local은 global 관측. InferX는 decode-stage cluster만 재구성 가능하고 P/D unique global total은 Unknown |
| InferX prefill running reference | N/A | N/A | unique worker/cluster **Unknown**; TP/CP rank-envelope max **5/4** | rank envelope은 pressure evidence이며 worker logical request union이 아님 |
| InferX decode running reference | N/A | N/A | validated decode workers max **9/10**; cluster max **17**, P90 **10** | TP8/DP8 DP-shard sum, exact endpoint-interval overlap; P/D global total 아님 |
| **Scheduler waiting — global/cluster total** | **max 1** | **max 25** | **unique P/D global Unknown** | Local은 global 관측. InferX generic decode queue cluster만 0으로 재구성됨 |
| InferX prefill waiting reference | N/A | N/A | unique worker/cluster **Unknown**; TP/CP rank-envelope max **5/5** | cluster-global waiting=5라는 뜻이 아님 |
| InferX decode waiting reference | N/A | N/A | generic `num_queue_reqs` cluster **0** | PD-specific prealloc/transfer queue와 동일 metric이 아님 |
| Waiting-positive behavior | 0.29% of 1s bins | **93.0% of 1s bins** | 동일한 cluster-global metric 없음 | Local conc8은 persistent backlog가 직접 관측됨 |

### 이 표에서 가장 중요한 해석

```text
InferX HTTP P90 = 7
≠ InferX scheduler running = 7

InferX prefill rank-envelope max = 5/4
+ InferX decode-stage cluster max = 17
≠ InferX P/D unique global running
```

이유는 다음과 같다.

- `HTTP in-flight`는 frontend/request-plane interval overlap이다.
- `num_running_reqs`는 SGLang scheduler metric이다.
- Prefill TP8/ATTN_CP8 값은 CP-rank local view이므로 worker/cluster unique count로 합산하지 않는다.
- Decode TP8/DP8 값은 source ownership과 complete raw DP grid를 검증해 decode worker/cluster stage occupancy로만 합산했다.
- 따라서 **InferX에서 P/D 전체의 unique request 총수는 현재 Unknown**으로 남겨야 한다. Decode-stage max 17은 global GPU service total이 아니다.

---

# 2. 환경 차이

| Field | Local conc1 | Local conc8 | InferX 결과 |
| --- | --- | --- | --- |
| GPU 구성 | 2× H200 NVL | 2× H200 NVL | 32 backend H200 |
| Prefill / Decode | 같은 2 GPU가 모두 수행 | 같은 2 GPU가 모두 수행 | Prefill 16 GPU / Decode 16 GPU 분리 |
| Parallelism | TP2 / DP1 / PP1 | TP2 / DP1 / PP1 | Prefill TP8×2 workers / Decode TP8×2 workers + DP-attention |
| Model | GLM-4.7-Flash | GLM-4.7-Flash | GLM-5.2-FP8 |
| Precision | BF16 | BF16 | FP8 |
| MTP | OFF | OFF | ON |
| KV 전략 | GPU KV + LMCache | GPU KV + LMCache | GPU-resident decode KV |
| Context limit | 202,752 | 202,752 | 1,048,576 |
| 실제 c8 workload | 해당 없음 | 동일 ID03 8-copy | mixed-root AgentX c8 |
| 실제 HTTP peak | 4 | 29 | 11 |
| Cluster-global scheduler running | max 4 | max 7 | **P/D unique global Unknown**; decode-stage cluster max 17 / P90 10 |
| Cluster-global scheduler waiting | max 1 | max 25 | **P/D unique global Unknown**; generic decode queue cluster 0 |
| Queue regime | 거의 queue-free | deep saturation | generic decode queue=0이나 P/D global queue regime은 Unknown |

따라서 `Local conc8`과 `InferX c8`은 이름만 c8이 같고 실제 backend pressure는 동일하지 않다.

---

# 3. Local 내부 saturation 분석

| Metric | Local conc1 | Local conc8 | InferX 결과 |
| --- | ---: | ---: | ---: |
| HTTP in-flight max | 4 | **29** | **11** |
| Cluster-global scheduler running max | 4 | **7** | **P/D unique global Unknown**; decode-stage cluster max **17** |
| Cluster-global scheduler waiting max | 1 | **25** | **P/D unique global Unknown**; generic decode queue cluster **0** |
| InferX scheduler 참고값 | N/A | N/A | prefill rank-envelope running≤5/4, waiting≤5/5; decode workers max 9/10, cluster P90 10 |
| Waiting-positive | 0.29% | **93.0%** | 동일 scope global metric 없음; prefill rank-series P90 waiting=0 |
| TTFT median | 0.563 s | **26.682 s** | 1.081 s |
| Queue median | 0.012 s | **24.385 s** | typical prefill queue histogram median ≈2–3 ms* |
| TTFT−queue proxy | 0.770 s | **1.812 s** | 1.081 s observed TTFT* |
| Weighted decode TPS | 93.05 | **61.71** | 90.45 |
| KV usage P95 | 72.5% | **98.0%** | decode token-usage rank-series P95 ≈91–93%* |

Local은 conc1에서는 거의 queue-free지만, conc8에서는 queue median 24.385초와 waiting-positive 93%가 관측되는 deep-saturation 상태다.

Local c1→c8 변화는 다음처럼 분해된다.

- HTTP in-flight max: **4 → 29**
- 실제 global running max: **4 → 7**
- 실제 global waiting max: **1 → 25**
- TTFT median: **0.563 → 26.682 s**, 약 47.4× 증가
- Queue median: **0.012 → 24.385 s**, 약 2,032× 증가
- TTFT−queue mean proxy: **0.770 → 1.812 s**, 약 2.35× 증가
- Weighted decode TPS: **93.05 → 61.71 tok/s**, 약 66.3% 유지

따라서 Local conc8에서는 들어온 request fan-out이 실제 service/admission capacity보다 훨씬 빠르게 증가했고, 그 차이가 waiting backlog로 누적됐다.

다만 이것을 단순히 **`max_num_seqs=8` hard limit 때문**이라고 해석하면 안 된다. Local에서는 설정상 8 sequence까지 허용했지만 실제 running max가 7에 머물렀고, 동시에 KV usage P95가 98%, external share of cached KV가 99.99%였다. 따라서 실제 binding constraint는 sequence-count ceiling 하나가 아니라 KV working-set pressure, external KV staging, batch/token budget, TP2 compute contention, aggregated prefill/decode interference 등이 결합된 결과일 가능성이 높다.

즉 `max_num_seqs`를 더 높여도 다른 자원 병목이 그대로라면 running 수와 queue time이 거의 개선되지 않을 수 있다.

---

# 4. ID03 exact comparison

Local conc8 copy1과 InferX ID03는 다음 조건이 모두 맞는다.

```text
Exact source match:      119 / 119
Same output length:      119 / 119
Strict TTFT:             119 / 119
Strict decode:           119 / 119
Strict E2E:              119 / 119
```

## 4.1 실제 시스템 결과

| Metric | Local conc1 | Local conc8 | InferX 결과 |
| --- | ---: | ---: | ---: |
| TTFT median | **0.563 s** | **26.69 s** (copy1) | **1.081 s** |
| Weighted decode TPS | **93.05** | **59.15** (copy1) | **90.45** |
| ID03 exact source coverage | 119/119 | 119/119 | 119/119 |
| ID03 trajectory wall time | **717 s** | 아직 별도 export 없음 | **482.69 s** |
| Logical KV load | ≈9.407M | ≈9.407M | ≈9.407M |
| Logical KV new/store | ≈0.493M | ≈0.493M | ≈0.493M |

## 4.2 Local conc8 copy1 ↔ InferX paired ratios

| Derived metric | Result |
| --- | ---: |
| Aggregate TTFT median ratio Local conc8 / InferX | **24.70×** |
| Request-wise TTFT ratio median | **18.85×** |
| Request-wise TTFT ratio P25 | 6.33× |
| Request-wise TTFT ratio P75 | 31.04× |
| Request-wise TTFT ratio P90 | 38.93× |
| Weighted decode TPS Local conc8 / InferX | **0.654×** |
| Request-wise TPS ratio median | **0.656×** |
| Request-wise E2E ratio median | **7.15×** |

Raw c8 비교는 실제 deployment 결과를 보여주지만, 동일 offered-load 비교는 아니다. Local c8 HTTP peak는 29이고 InferX는 11이다.

---

# 5. 세 가지 해석용 비교

## 5.1 Low-contention baseline

| Metric | Local conc1 | Local conc8 | InferX 결과 |
| --- | ---: | ---: | ---: |
| TTFT median | **0.563 s** | 26.682 s | **1.081 s** |
| Queue median | **0.012 s** | 24.385 s | typical prefill queue ≈0.0025 s* |
| Weighted decode TPS | **93.05** | 61.71 | **90.45** |
| Local conc1 / InferX TTFT | **0.521×** | N/A | reference 1.0× |
| Local conc1 / InferX decode TPS | **1.029×** | N/A | reference 1.0× |

Local conc1과 InferX c8는 둘 다 typical persistent queue가 거의 없는 operating regime이라는 점에서 **low-contention service baseline**으로 비교할 수 있다.

이 결과는 2 GPU가 32 GPU보다 빠르다는 의미가 아니다. 모델과 serving architecture가 다르기 때문에, 각 시스템이 자신의 모델을 low-contention 상태에서 처리한 observed behavior 비교다.

## 5.2 Queue-adjusted service-side view

| Metric | Local conc1 | Local conc8 | InferX 결과 |
| --- | ---: | ---: | ---: |
| TTFT−queue mean proxy | 0.770 s | **1.812 s** | observed TTFT **1.081 s*** |
| Approx. Local conc8 proxy / InferX TTFT | N/A | **1.68×** | reference 1.0× |
| Weighted decode TPS | 93.05 | 61.71 | 90.45 |

\* InferX 1.081초는 queue-adjusted 값이 아니라 observed median TTFT다. Prefill queue histogram median은 약 2–3ms이고 generic decode queue는 0이지만, 이는 P/D global queue-time decomposition이나 global queue pressure 결론이 아니다.

## 5.3 Raw deployment-level view

| Metric | Local conc1 | Local conc8 | InferX 결과 |
| --- | ---: | ---: | ---: |
| Raw TTFT median | 0.563 s | **26.682 s** | **1.081 s** |
| Weighted decode TPS | 93.05 | **61.71** | **90.45** |
| HTTP peak | 4 | **29** | **11** |
| Global scheduler running | max 4 | max 7 | **P/D unique global Unknown**; decode-stage cluster max 17 |
| Global scheduler waiting | max 1 | max 25 | **P/D unique global Unknown**; generic decode queue cluster 0 |
| Waiting regime | 거의 없음 | **persistent/deep saturation** | generic decode queue=0; P/D global waiting regime Unknown |

---

# 6. Trajectory wall-time comparison

| Metric | Local conc1 | Local conc8 | InferX 결과 |
| --- | ---: | ---: | ---: |
| ID03 trajectory elapsed time | **11m 57s** | 아직 별도 export 없음 | **8m 02.7s** |
| Seconds | **717 s** | 아직 별도 export 없음 | **482.69 s** |
| Local conc1 / InferX time ratio | **1.485×** | N/A | reference 1.0× |

InferX ID03 trajectory는 Local conc1보다 wall-clock 기준 약 **32.7% 짧게** 끝났다.

단, 이것도 pure GPU speed 비교는 아니다. InferX는 mixed-root c8 replay이며 P/D disaggregation, MTP, 다른 모델/precision을 사용한다.

---

# 7. Logical KV workload alignment

| Metric | Local conc1 | Local conc8 | InferX 결과 |
| --- | ---: | ---: | ---: |
| Exact source requests | 119 | copy1 119 | 119 |
| Logical reusable/load KV per trajectory | ≈9.407M tokens | ≈9.407M tokens/copy | ≈9.407M tokens |
| Logical new/store KV per trajectory | ≈0.493M tokens | ≈0.493M tokens/copy | ≈0.493M tokens |
| Local runtime vs trace logical agreement | trace-equivalent | c8 runtime ≈99.8%+ agreement | trace-equivalent logical workload; physical cache counter는 직접 사용하지 않음 |

Local c8 8-copy 전체 trace 예상값:

```text
Logical reusable/load: 75,254,400 tokens
Logical new/store:      3,943,680 tokens
```

Local runtime 관측값:

```text
External cache hit:     75,148,896 tokens
LMCache stored:          3,936,512 tokens
```

Trace 대비 차이는 각각 약 0.14%, 0.18% 수준이다.

InferX는 GPU-resident KV이므로 물리적인 external load/store counter를 Local LMCache와 직접 비교하지 않는다. 다만 ID03 source structure와 119 exact key가 동일하므로 **logical KV workload는 사실상 같은 trajectory**로 취급한다.

---

# 8. Main conclusions

1. **Local conc1은 low-contention baseline**이다. TTFT 0.563초, queue 0.012초, decode TPS 93.05 tok/s다.
2. **Local conc8은 deep saturation**이다. TTFT 26.682초 중 queue median이 24.385초이며, HTTP peak 29, global max waiting 25가 관측됐다.
3. **InferX c8은 Local conc8과 같은 c8 부하가 아니다.** HTTP max 11, time-weighted mean 3.97, P90 7, P95 8이다.
4. **InferX의 P/D unique global scheduler running/waiting request 수는 Unknown이다.** `HTTP P90=7`은 running 7을 뜻하지 않는다. Decode DP-shard cluster running은 max 17/P90 10으로 재구성했지만, prefill CP-rank unique union 및 P/D handoff deduplication이 없어 global total로 합산하지 않는다.
5. Public generic decode `num_queue_reqs`는 0으로 관측됐지만, prefill unique queue union 및 PD-specific decode prealloc/transfer queues는 별도 scope다. 따라서 **global persistent waiting이 낮다**고 확정하지 않는다.
6. **Local conc8 raw TTFT가 InferX보다 매우 길지만 decode TPS 차이는 훨씬 작다.** 따라서 TTFT 격차의 상당 부분은 Local scheduler/admission backlog로 설명된다.
7. **Local conc1과 InferX는 decode TPS가 같은 order**다: 93.05 vs 90.45 tok/s. 이는 low-contention behavior 비교이며 hardware efficiency 비교가 아니다.
8. **Local conc8에서 queue만 제외한 service-side proxy는 약 1.812초**로 InferX observed TTFT 1.081초와 같은 1초대 order다.
9. **ID03 logical KV load/store workload는 세 비교 모두 사실상 동일**하다: trajectory당 약 9.407M reusable/load + 0.493M new/store tokens.
10. **ID03 trajectory wall time은 현재 Local conc1 717초 vs InferX 482.69초**로, InferX가 약 32.7% 짧다.

가장 안전한 최종 표현은 다음과 같다.

> Local 2×H200 Aggregated 서버는 low-contention 상태에서는 빠른 service rate를 보이지만, 동일 ID03 workload에서 concurrency가 증가하면 scheduler/KV pressure가 빠르게 포화된다. Local conc8의 매우 큰 TTFT는 active inference 성능 저하만으로 설명되지 않으며 persistent queue backlog가 지배적이다. Public InferenceX c8은 동일 root-concurrency label을 사용하지만 실제 request-plane load가 훨씬 낮다. Public export에서는 P/D unique global running/waiting request 총수를 복원할 수 없으므로 Local의 global 7/25와 숫자 대 숫자로 비교하면 안 된다. Public decode-stage cluster occupancy는 검증됐지만 prefill unique union 및 cross-stage deduplication은 Unknown이다.

---

# 9. 비교 시 금지할 해석

- `InferX HTTP P90=7이므로 실제 running request도 7개다`
- `InferX prefill rank-envelope 5/4 + decode cluster 17 = global running`
- `InferX prefill TP/CP rank-envelope waiting max 5 = cluster-global waiting 5`
- `2 GPU가 32 GPU보다 빠르다`
- `Local c8와 InferX c8는 동일 offered load다`
- `59/62 vs 90 tok/s 비율이 GPU 성능비다`
- `H200 cache_read_tokens를 검증 없이 physical/logical KV load 총량으로 사용한다`
- `MTP / FP8 / P/D disaggregation 중 하나가 단독으로 차이를 만들었다고 주장한다`

---

# 10. Public reference files

```text
studies/h200_gpu_resident_mtp/processed/id03_h200_reference_requests.csv
studies/h200_gpu_resident_mtp/processed/id03_h200_scaling_curve.csv
studies/h200_gpu_resident_mtp/processed/c8_concurrency_reconstruction_summary.csv
studies/h200_gpu_resident_mtp/processed/c8_prefill_scheduler_summary.csv
studies/h200_gpu_resident_mtp/processed/c8_decode_scheduler_summary.csv
studies/h200_gpu_resident_mtp/processed/id03_c8_with_system_load.csv
studies/h200_gpu_resident_mtp/reports/11_id03_deep_dive.md
studies/h200_gpu_resident_mtp/reports/13_c8_concurrency_scheduler_reconstruction.md
```

Local values are export-safe summary measurements supplied by the user; internal raw files are intentionally not stored in this repository.
