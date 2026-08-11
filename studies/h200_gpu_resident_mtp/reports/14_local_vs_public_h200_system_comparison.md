# 14. Local 2×H200 vs Public InferenceX 32×H200 — ID03 System Comparison

## 0. Scope and provenance

This report compares two serving environments using the canonical AgentX source trace:

```text
07dd40536557a1d6440a923557c3129dc929
```

The two environments are:

1. **Local/internal serving experiment** — summarized from export-safe measurements provided by the user. No internal raw log, hostname/IP, credential, private path, or raw company artifact is stored in this repository.
2. **Public InferenceX H200 GPU-resident MTP benchmark** — reconstructed from public run `31235207041`, canonical run SHA `48ec5aa103dbf8e671580cd191eeef7e7186c802`.

The goal is **not** to claim a pure GPU hardware benchmark. The systems differ materially in model, precision, serving topology, speculative decoding, KV strategy, GPU count, and realized offered load. This is therefore a **serving-system behavior comparison**.

---

# 1. Environment comparison

| Field | Local/internal system | Public InferenceX H200 system |
| --- | --- | --- |
| GPU | 2× NVIDIA H200 NVL | 32 backend H200 |
| Model | GLM-4.7-Flash | `zai-org/GLM-5.2-FP8` |
| Weight dtype / quantization | BF16 / no quantization | FP8 model |
| Serving topology | **Aggregated**: same 2 GPUs perform prefill + decode | **P/D disaggregated** |
| Prefill resources | same TP2 pair | 2 workers × 8 H200 = 16 H200 |
| Decode resources | same TP2 pair | 2 workers × 8 H200 = 16 H200 |
| Parallelism | TP2 / DP1 / PP1 | runtime prefill TP8, decode TP8 / DP-attention |
| MTP / speculative decoding | **OFF** | **EAGLE MTP ON**, steps=3, top-k=1, draft tokens=4, sampled acceptance length ≈2.99 |
| Max model/context length | 202,752 | 1,048,576 |
| Scheduler limit | `max_num_seqs=8` | prefill `max_running_requests=32`; decode `max_running_requests=200` |
| KV block/page | 16 tokens | 64 tokens |
| GPU KV runtime capacity | 258,864 tokens/rank | runtime-profiled 218,560 tokens/rank on logged decode rank |
| GPU KV allocation | ≈13.05 GiB/GPU rank | ≈12.51 GiB primary + ≈0.16 GiB secondary/logged decode rank |
| Approx. primary KV footprint | ≈52.9 KiB/token/rank | ≈60 KiB/token/rank |
| External KV/cache tier | LMCache CPU 20 GB + disk up to 1.8 TB, LRU, O_DIRECT | none; decode KV GPU-resident |
| LMCache | enabled | disabled |
| CPU/KV offload | external LMCache path used | CPU offload 0; decode KV offload false |
| Root c8 workload composition | 8 independent copies of the same ID03 trajectory | 8 mixed AgentX root lanes across multiple source traces |

### Interpretation

The two systems share the H200 GPU generation but are **not architecture-equivalent**. The most important confounders are:

- GLM-4.7-Flash vs GLM-5.2-FP8
- BF16/no MTP vs FP8/EAGLE-MTP
- 2-GPU aggregated prefill+decode vs 32-GPU P/D-disaggregated serving
- external LMCache vs GPU-resident decode KV
- materially different realized request fan-out despite both experiments being labeled `c8`

Therefore ratios in this report are **observed end-to-end system ratios**, not isolated GPU, MTP, quantization, or topology causal effects.

---

# 2. Local c1 / c4 / c8 saturation curve

Export-safe local summary:

| Metric | c1 | c4 | c8 |
| --- | ---: | ---: | ---: |
| Root copies | 1 | 4 | 8 |
| Max HTTP in-flight | 4 | 15 | 29 |
| vLLM max running | 4 | 6 | 7 |
| vLLM max waiting | 1 | 11 | 25 |
| Waiting-positive 1-second bins | 0.29% | 66.1% | 93.0% |
| TTFT median | 0.563 s | 8.175 s | 26.682 s |
| Queue median | 0.012 s | 7.328 s | 24.385 s |
| Prefill median | 0.531 s | 1.214 s | 1.221 s |
| TTFT − queue mean proxy | 0.770 s | 1.776 s | 1.812 s |
| Weighted decode TPS | 93.05 | 63.72 | 61.71 |
| Wall output TPS | 53.62 | 117.17 | 130.73 |
| Local cache-hit ratio | 95.00% | 94.88% | 94.86% |
| External share of cached KV | 1.07% | 93.74% | 99.99% |
| KV usage P95 | 72.5% | 96.8% | 98.0% |
| GPU utilization average | 52.2% | 74.7% | 86.3% |

## 2.1 Local saturation knee

The strongest local result is the transition from c1 to c4:

- TTFT median: **0.563 → 8.175 s** (~14.5×)
- queue median: **0.012 → 7.328 s** (~611×)
- weighted decode TPS: **93.05 → 63.72 tok/s** (68.5% retention)
- KV usage P95: **72.5% → 96.8%**
- waiting-positive bins: **0.29% → 66.1%**

This indicates that the serving system has already entered a saturation regime by c4.

## 2.2 c4 → c8 is primarily backlog growth

From c4 to c8:

- root concurrency doubles: 4 → 8
- wall output TPS rises only **117.17 → 130.73 tok/s** (+11.6%)
- queue median rises **7.328 → 24.385 s** (+233%)
- TTFT median rises **8.175 → 26.682 s** (+226%)
- decode TPS changes only **63.72 → 61.71 tok/s** (-3.2%)
- TTFT−queue proxy changes only **1.776 → 1.812 s** (+2.0%)

Thus c4→c8 mostly adds **scheduler/admission backlog** rather than causing another large collapse in execution-side service rate.

## 2.3 Cache behavior

The local cache hit ratio remains ~95% across c1/c4/c8, so the large TTFT increase is not explained by falling cache-hit probability.

However, the location of reusable KV changes dramatically:

```text
External share of cached KV
c1   1.07%
c4  93.74%
c8  99.99%
```

At the same time, KV usage P95 rises to 96.8–98.0%. This is evidence that concurrency pushes the local system into a high-KV-pressure regime where nearly all reused KV is served through the external cache tier.

This does **not** prove that LMCache transfer alone causes the decode/service degradation. Other concurrent effects include TP2 batch contention, aggregated prefill/decode interference, memory pressure, synchronization, and scheduling.

---

# 3. Public H200 c8 realized load and scheduler state

Public c8 does **not** mean eight simultaneous backend requests.

Across 957 successful profiling request intervals:

| Public H200 c8 HTTP overlap metric | Value |
| --- | ---: |
| Max in-flight | **11** |
| Time-weighted mean | **3.968** |
| P50 | 4 |
| P75 | 5 |
| P90 | 7 |
| P95 | 8 |
| P99 | 9 |
| Fraction of time ≥8 | 5.26% |
| Fraction of time ≥12 | 0% |

Therefore the public c8 workload spends most of its time at only about 4–7 concurrent HTTP/profile intervals.

### Public scheduler evidence

Prefill `sglang:num_queue_reqs` rank-series summary:

- P50 = 0
- P90 = 0
- P95 ≈ 1
- observed rank-series maximum = 5

Decode `sglang:num_queue_reqs`:

- observed value = 0 throughout the exported series

Public prefill queue-time histograms show a **very small median** (roughly 2–3 ms) but non-trivial long tails on some rank-series. Decode queue-time histogram values are sub-millisecond.

Important scope caveat: the public `max waiting = 5` is a **rank-series maximum**, not a cluster-wide total and must not be directly divided into the local global `max waiting = 25`.

The valid qualitative comparison is:

> Local c8 has persistent queueing (waiting-positive 93%, queue median 24.385 s), whereas public H200 c8 is typically in a low-waiting operating regime.

---

# 4. ID03 exact paired c8 comparison

The local c8 copy1 and public H200 c8 ID03 comparison has unusually strong workload alignment:

```text
Exact source match:      119 / 119
Same output length:      119 / 119
Strict TTFT subset:      119 / 119
Strict decode subset:    119 / 119
Strict E2E subset:       119 / 119
```

Observed comparison:

| Metric | Local c8 copy1 | Public H200 c8 ID03 | Local/H200 |
| --- | ---: | ---: | ---: |
| Aggregate TTFT median | 26.69 s | 1.081 s | 24.70× |
| Weighted decode TPS | 59.15 | 90.45 | 0.654× |
| Request-wise TTFT ratio median | — | — | **18.85×** |
| TTFT ratio P25 | — | — | 6.33× |
| TTFT ratio P75 | — | — | 31.04× |
| TTFT ratio P90 | — | — | 38.93× |
| Request-wise TPS ratio median | — | — | **0.656×** |
| Request-wise E2E ratio median | — | — | **7.15×** |

The request-wise ratio median is the preferred paired statistic because it preserves all 119 exact request pairs.

### Interpretation

The very large TTFT gap cannot be explained by decode speed alone:

- TTFT is ~19× worse request-wise at the median.
- Decode TPS is only ~35% lower.

This is consistent with local scheduler/admission queueing being the dominant source of the c8 first-token latency gap.

However, this is **not** an equal-load c8 benchmark: local HTTP in-flight peaks at 29 while public c8 peaks at 11 and usually runs at 4–7. The raw `26.69 s vs 1.081 s` comparison is therefore a valid observed system result, but not an apples-to-apples concurrency-capacity ratio.

---

# 5. Three useful comparison views

## 5.1 Low-contention service baseline

A useful descriptive comparison is Local c1 vs Public H200 c8 ID03 because both operate with little typical queue pressure.

| Metric | Local c1 | Public H200 c8 ID03 |
| --- | ---: | ---: |
| TTFT median | **0.563 s** | **1.081 s** |
| Weighted decode TPS | **93.05** | **90.45** |
| Local/H200 TTFT | ~0.52× | — |
| Local/H200 decode TPS | ~1.029× | — |

This does **not** mean 2 H200 GPUs outperform 32 H200 GPUs. The models and serving stacks are different. It only shows that the local system is not intrinsically a 60 tok/s / 27-second-TTFT system under low contention.

Use label:

> **Low-contention service baseline comparison**

Do not label it a concurrency-matched or GPU-efficiency comparison.

## 5.2 Local c8 queue-adjusted service-side view

Local c8 mean proxy:

```text
TTFT − measured queue ≈ 1.812 s
```

Public H200 c8 ID03 median TTFT:

```text
≈ 1.081 s
```

These are both in the same 1-second order of magnitude. This supports the interpretation that much of local c8 raw TTFT is backlog rather than intrinsic first-token computation.

Caveats:

- 1.812 s is currently a mean proxy while 1.081 s is a median.
- H200 TTFT still contains its own routing/queue/prefill/transfer components.
- models and serving architectures differ.

The preferred follow-up statistic is request-level:

```text
median_i[(local_ttft_i - local_queue_i) / h200_ttft_i]
```

for the 119 exact pairs.

## 5.3 Raw user-visible system behavior

Raw c8:

```text
Local TTFT median ≈ 26.7 s
Public H200 ID03 TTFT median ≈ 1.08 s
```

This is the correct view when the question is:

> “What latency does each deployed configuration actually expose under its own c8 experiment?”

It is **not** the correct view when the question is pure inference-engine speed.

---

# 6. Why the two `c8` labels are not equivalent

The request-plane load differs materially:

| Metric | Local c8 | Public H200 c8 |
| --- | ---: | ---: |
| Root lanes/copies | 8 | 8 |
| Workload composition | same ID03 copied 8× | mixed-root AgentX |
| Max HTTP in-flight | **29** | **11** |
| Waiting behavior | persistent | mostly absent/low |
| Local waiting-positive 1s bins | **93%** | no directly identical cluster-global metric |

Hence:

```text
root concurrency = 8
```

is a workload-generator parameter, not a guarantee of equal offered load or equal backend saturation.

The local c8 test is a **deep-saturation point**. The public H200 c8 run is generally a **headroom / low-waiting point**, with occasional prefill long-tail queue events.

---

# 7. KV footprint and capacity notes

Approximate runtime primary GPU-KV footprint inferred from allocation/capacity observations:

| System | Approx. primary KV footprint |
| --- | ---: |
| Local GLM-4.7-Flash | ~52.9 KiB/token/rank |
| Public GLM-5.2 FP8 decode | ~60 KiB/token/rank |

Do not multiply the public per-rank value by eight and claim a cluster-wide `~480 KiB/token`. The public runtime evidence is rank-scoped under TP/DP-attention, and the study intentionally avoids unsupported aggregation across ranks.

Likewise, the raw token-capacity numbers:

```text
Local: 258,864 tokens/rank
Public decode runtime profile: 218,560 tokens/rank
```

must not be interpreted as a simple statement that the local system has greater total KV capacity. Topology, sharding semantics, dtype, page size, worker count, and external cache strategy differ.

---

# 8. Main conclusions

## Evidence-backed conclusions

1. **Local c1 is effectively queue-free**, with TTFT median 0.563 s and decode TPS 93.05 tok/s.
2. **Local saturation begins by c4**: queue median becomes 7.328 s, waiting is present in 66.1% of 1-second bins, KV P95 reaches 96.8%, and decode TPS falls to 63.72 tok/s.
3. **Local c8 is deep saturation**: queue median 24.385 s, waiting-positive bins 93%, max HTTP in-flight 29, max waiting 25, KV P95 98%.
4. **c4→c8 mostly adds backlog**: wall throughput gains only 11.6%, while queue median rises 233% and execution-side proxy changes only ~2%.
5. **Public H200 c8 is not equivalently saturated**: HTTP max 11, time-weighted mean 3.97, P90 7, P95 8; prefill waiting is usually 0 and decode waiting is 0 in the exported rank-series.
6. **The exact ID03 pair quality is high**: 119/119 source matches, 119/119 equal output length, and all 119 valid for TTFT/decode/E2E paired comparison.
7. **Raw local c8 TTFT is ~19× worse request-wise at the median, while decode TPS is only ~35% lower**, strongly indicating that queue/admission behavior explains much more of the TTFT gap than active decoding speed.
8. **Local c1 and public H200 c8 show similar-order decode TPS (~93 vs ~90 tok/s)**, but this must not be interpreted as a hardware efficiency result because model and architecture differ.

## Inference

The best current system-level interpretation is:

> The local 2×H200 aggregated stack has adequate low-contention service speed, but its capacity knee occurs between c1 and c4 for this AgentX workload. By c8, request fan-out and KV pressure exceed sustainable admission/service capacity, producing persistent scheduler backlog. The public 32×H200 P/D-disaggregated MTP system experiences a much lower realized request-plane load and remains mostly outside that persistent-waiting regime.

## Unknown / not causally isolated

The available comparison does **not** isolate how much of the difference is caused individually by:

- GPU count
- GLM-4.7-Flash vs GLM-5.2
- BF16 vs FP8
- MTP
- P/D disaggregation
- TP2 vs TP8/DP-attention
- external LMCache vs GPU-resident KV
- KV page/block size
- request scheduling policy

A controlled ablation would be required for causal attribution.

---

# 9. Recommended usage of the comparison

For future reporting, keep three labels separate:

1. **Low-contention baseline:** Local c1 vs Public H200 c8 ID03.
2. **Queue-adjusted service-side comparison:** Local c8 `TTFT - measured queue` vs Public H200 c8 TTFT.
3. **Observed deployment-level comparison:** Local c8 raw TTFT/E2E vs Public H200 c8 raw TTFT/E2E.

Never describe any of these as a pure `2 GPU vs 32 GPU hardware benchmark`.

---

# 10. Public reference files

Public H200 evidence used by this report is versioned in:

```text
studies/h200_gpu_resident_mtp/processed/id03_h200_reference_requests.csv
studies/h200_gpu_resident_mtp/processed/c8_concurrency_reconstruction_summary.csv
studies/h200_gpu_resident_mtp/processed/c8_prefill_scheduler_summary.csv
studies/h200_gpu_resident_mtp/processed/c8_decode_scheduler_summary.csv
studies/h200_gpu_resident_mtp/processed/id03_c8_with_system_load.csv
studies/h200_gpu_resident_mtp/reports/11_id03_deep_dive.md
studies/h200_gpu_resident_mtp/reports/13_c8_concurrency_scheduler_reconstruction.md
```

Local values in this report are export-safe summary measurements supplied directly by the user; internal raw files are intentionally not stored in this repository.
