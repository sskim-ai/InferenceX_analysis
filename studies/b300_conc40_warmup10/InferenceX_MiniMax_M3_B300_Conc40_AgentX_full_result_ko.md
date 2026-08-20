# InferenceX MiniMax-M3 B300 Conc40 AgentX — 전체 수행 결과

이 문서는 GitHub Actions run `30849838984`의 지정 공개 artifact와 InferenceX commit `8767d90c11860a10668f2d66179711a9c24fc8bd`, AIPerf gitlink `818c3a5a2922c535af6271ff296ed374e292b8e4`, 공개 corpus revision `23f152f6f0f9399a85901b89a6458def0ef16729`를 기준으로 작성한 단일 통합 보고서다.

- 원본 InferenceX repository/workspace 수정 없음; 본 공개본만 `InferenceX_analysis`의 별도 study로 관리
- Raw prompt/response 본문 출력 없음
- Artifact ZIP SHA-256 검증 완료
- Initial/recycled root 94개 모두 source total 해결; `UNRESOLVED` 없음
- `gh auth status`의 저장 토큰은 무효였으며, 설치된 signed-in GitHub connector를 통해 동일 공개 artifact를 다운로드함

## B300 Conc40 `warmup-requests-per-lane=10` 실제 동작 분석

### 1. 결론

이 run의 `10`은 **각 initial root의 warmup row를 10개로 맞춘 값이 아니라, 40개 live trajectory lane 각각에 필수 snapshot primer 이후 추가로 허용한 model-request 10개**였다. Artifact에는 필수 primer 44개와 추가 pressure request 400개, 합계 444개의 warmup record가 있다. pressure replay 도중 tree가 끝나면 같은 lane에서 새 root가 turn 0부터 이어져 quota를 소비했으므로 initial root별 warmup record 수는 동일하지 않다.

### 2. Global summary

| 항목 | 값 | 근거 종류 |
|---|---:|---|
| configured_concurrency | 40 | artifact command |
| distinct_initial_roots | 40 | artifact log 직접 확인 |
| initial_root_count_matches_concurrency | true | derived: 40 == 40 |
| distinct_recycled_roots | 54 | derived: total - initial |
| distinct_total_roots | 94 | artifact 직접 확인 |
| total_warmup_requests | 444 | artifact 직접 확인 |
| total_profile_requests | 4973 | artifact 직접 확인 |
| expected_warmup_if_exact_10_per_lane | 400 | derived |
| actual_total_warmup_requests | 444 | artifact 직접 확인 |
| difference_from_400 | 44 | derived; mandatory primers |
| mandatory_snapshot_primers | 44 | artifact log + request-start gap |
| additional_cache_pressure_requests | 400 | artifact log + derived |
| initial_roots_with_exactly_10_warmup | 2 | artifact derived |
| initial_roots_not_equal_10_warmup | 38 | artifact derived |
| warmup root-conversation requests | 302 | artifact 직접 확인 |
| warmup subagent requests | 142 | artifact 직접 확인 |
| pressure-stage root requests | 269 | artifact derived stage split |
| pressure-stage subagent requests | 131 | artifact derived stage split |

Initial-root warmup 분포: min=2, p25=10, median=11, p75=11, max=14, mean=9.725. Frequency는 `07_warmup_distribution.csv`에 있다.

Initial root는 warmup phase에 보였다는 이유로 정하지 않았다. Artifact log가 01:16:15에 `built 40 trajectories from 393 traces`와 lane 00-39를 기록했고, 01:16:17에 44-primer warmup이 시작됐으며 profiling setup에서도 live lane population이 40이었다. 이 40개 log trace ID만 initial로 사용했다. Warmup 전체의 distinct root ID는 50개였으므로 그 집합을 initial로 간주하면 10개 warmup-time recycle root가 섞인다.

### 3. Initial 40개 표

| lane | root_id | source_total | observed | warmup | profile | first warmup | last warmup | first profile |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | `002001296e8a8c38ad9d7cc436d691afc602` | 198 | 45 | 11 | 34 | 88 | 98 | 99 |
| 1 | `006c98de37d819e95b0840e25426bb7ca99d` | 33 | 29 | 11 | 18 | 4 | 14 | 15 |
| 2 | `00ca01c4aaeccee751ae6285beb54dea262f` | 35 | 6 | 6 | 0 | 26 | 31 | — |
| 3 | `0196085d85d2075a50b74cd8795ffbdcea9a` | 233 | 58 | 11 | 47 | 87 | 97 | 98 |
| 4 | `02bc0afb13f7a2d9efa86c28511261d85c0e` | 466 | 8 | 8 | 0 | 254 | 261 | — |
| 5 | `03e110ac6921c2fe9ac7772a9654314a2beb` | 107 | 63 | 11 | 52 | 23 | 33 | 34 |
| 6 | `0470d446a4514dfe0c6ad0be92853bd13287` | 795 | 187 | 11 | 176 | 400 | 619.1 | 402 |
| 7 | `04dba6fe621301a1d01fd63b8d02c9645c48` | 25 | 5 | 5 | 0 | 2 | 7 | — |
| 8 | `05c249572509162371b7b82339674db64b5d` | 36 | 3 | 3 | 0 | 33 | 35 | — |
| 9 | `05f72f78a037cfa5cd4e4541960a574701d9` | 52 | 4 | 4 | 0 | 48 | 51 | — |
| 10 | `063179eb93f4337a662e859c5a2c5638e03f` | 73 | 23 | 11 | 12 | 16 | 26 | 27 |
| 11 | `069d7bf5f1efb4e76e3c84510367e6af78a5` | 352 | 11 | 11 | 0 | 217 | 227 | — |
| 12 | `077ea9e6554f45bbad9c24a8462bae9a8512` | 35 | 10 | 10 | 0 | 25 | 34 | — |
| 13 | `07dd40536557a1d6440a923557c3129dc929` | 119 | 26 | 13 | 13 | 7 | 9.49 | 9.50 |
| 14 | `085411a4cc4b15108dd9b50007261a2efb65` | 102 | 97 | 11 | 86 | 5 | 9.2 | 10.2 |
| 15 | `085aacf44ac5428ad3c6b4f6cd431e083832` | 1778 | 71 | 11 | 60 | 375 | 385 | 386 |
| 16 | `0a279af1bec84c6ab033bb03f5d8bfd6b08d` | 150 | 95 | 11 | 84 | 19 | 29 | 30 |
| 17 | `0a688303b1ae62a97607af8021f2130c2caf` | 31 | 11 | 11 | 0 | 20 | 30 | — |
| 18 | `0b7f3ca692f15ae2651a310d9411d70794aa` | 172 | 11 | 11 | 0 | 161 | 171 | — |
| 19 | `0bc9c4f798d321286bf39f2543c0c4e4c059` | 102 | 11 | 11 | 0 | 10 | 20 | — |
| 20 | `0bcd99353218b9a386b1c4aec13d77abecdb` | 35 | 6 | 6 | 0 | 21 | 26 | — |
| 21 | `0bed163ac9566086e14ffd85c7481096d49d` | 53 | 23 | 11 | 12 | 30 | 40 | 41 |
| 22 | `0d41be2aa98333f3662682210647e5971c7b` | 33 | 28 | 11 | 17 | 5 | 15 | 16 |
| 23 | `0d8a816e4819b765d81ff748da94d463f3b2` | 28 | 13 | 11 | 2 | 15 | 25 | 26 |
| 24 | `0db32e2f852a2ea24ed616b31975a84da5e4` | 60 | 50 | 11 | 39 | 3 | 20 | 21 |
| 25 | `0dedb07b5e4362b028db9d8ab90fff7fd4ad` | 44 | 2 | 2 | 0 | 42 | 43 | — |
| 26 | `0e4206535a79f980e2b1091181202ea987fe` | 27 | 19 | 11 | 8 | 8 | 18 | 19 |
| 27 | `0ede42538334da8586bc60008762abfc0ab7` | 163 | 103 | 11 | 92 | 6 | 16 | 17 |
| 28 | `0f909e7d63c0d5e1f060d727ada25d910d89` | 49 | 18 | 11 | 7 | 31 | 41 | 42 |
| 29 | `1007f04d2c64580308858bb42f292992929d` | 133 | 19 | 11 | 8 | 67 | 77 | 78 |
| 30 | `11310dce936f02050cadaeae295bcdd1ce7f` | 1098 | 68 | 11 | 57 | 264 | 274 | 275 |
| 31 | `117ebe75819d050f308a0a81647893abd02d` | 282 | 236 | 12 | 224 | 30 | 36.1 | 31.5 |
| 32 | `12bd4c7c82ae413b035253cb800fc5312111` | 40 | 30 | 14 | 16 | 2 | 8 | 6.12 |
| 33 | `12cfecf98c158ab54fb65980602421f00d69` | 20 | 2 | 2 | 0 | 18 | 19 | — |
| 34 | `12e6fd87f4d3d1f93f96bd7bb6a520043805` | 94 | 40 | 11 | 29 | 54 | 64 | 65 |
| 35 | `13b532ee3aaa0a52b05c3bcc472355ab62b4` | 167 | 40 | 11 | 29 | 97 | 107 | 108 |
| 36 | `13e0b7038bafff59abfdc31aad12dbcd4a2f` | 241 | 84 | 11 | 73 | 35 | 41.2 | 40.3 |
| 37 | `14129d470e508b236be22188aa78548ef805` | 27 | 14 | 11 | 3 | 13 | 23 | 24 |
| 38 | `1493faffdc8942e99daa22277f44871a40b8` | 78 | 8 | 8 | 0 | 70 | 77 | — |
| 39 | `1499c406c828e8fe6b6af697e7799c6a715b` | 140 | 48 | 10 | 38 | 17 | 26 | 27 |

`source_total`은 artifact observed count가 아니라 공개 corpus revision의 원본 model request 수(outer normal/streaming request + nested subagent inner request)다. `first/last`는 JSONL row 순서가 아니라 historical loader의 global metric-prepass 순서 `(t, outer_idx, stream_idx, k)`에 맞춘 provenance index다. 실제 AgentX 실행은 하나의 flat queue가 아니라 conversation DAG와 timestamp로 진행된다.

### 4. `warmup=10`의 정확한 의미

- H1(각 initial root가 정확히 10 warmup rows): **거짓**. 정확히 10인 initial root는 2/40개뿐이고 범위는 2-14다. 다만 코드의 lane counter와 run log는 **각 lane의 추가 pressure quota가 정확히 10**에 도달했다고 확인한다.
- H2(그 10개가 profiling 직전 source request 10개): **거짓**. 필수 primer는 t* 직전의 각 live stream별 마지막 request이고, 추가 10개는 t* 이후 live DAG 실행이다. Initial root 기준 source-contiguous warmup은 32/40개이고, profile이 실제 존재한 26개 중 전체 warmup set이 첫 profile source request를 즉시 선행한 경우는 19/26개뿐이다. 나머지는 DAG stream 간 source-order interleave 또는 gap이 있다.
- H3(10 root turns): **거짓**. 전체 warmup 444개 중 root conversation 302, subagent 142; 추가 pressure 400개만 보아도 root 269, subagent 131다.
- H4(t* 이전/이후): **두 단계**다. 44개 mandatory primer는 t* 이전 마지막 request이고, 그 뒤 400개 pressure request는 post-snapshot/t* 이후 경로를 zero-idle, one-token으로 진행한다.

### 5. Recycled trace 검증

Artifact에서 profiling-only root는 44개이며 모두 `warmup_requests=0`, `profile_requests>0`이다. 그중 source 전체가 관측된 root는 18개이고, 이 중 18개는 historical source order의 첫 request부터 profiling이 시작했다. Initial 40 중 profiling까지 같은 root로 남은 것은 26개이며, 나머지 14개는 warmup pressure 중 끝났다. Warmup 단계 자체에서도 새 root 10개가 등장했다. 상세 분류는 `05_recycled_root_summary.csv`에 있다.

### 6. AIPerf 818c3a5a 코드 근거

gitlink와 checkout 모두 `818c3a5a2922…`로 고정했다. 구현은 (1) t* snapshot 선택, (2) live stream별 pre-t* predecessor primer, (3) primer와 별개인 lane별 10회 admission counter, (4) zero-idle/1-token pressure replay, (5) live-state profiling handoff, (6) profiling recycle의 fresh turn-0 시작 순서다. 정확한 파일·라인과 A-I 답은 `08_aiperf_818c3a5a_source_evidence.md`에 정리했다.

### 7. 남은 불확실성

- JSONL에는 literal `lane_id`가 없다. Initial lane은 artifact log의 TrajectorySource 표에서 확정했지만 recycled root의 lane 번호는 request record만으로 복원하지 않았다.
- `session_num`은 historical source상 credit number이므로 session identity로 쓰지 않았다. Summary의 `session_id`는 tree-level `root_correlation_id`, detail의 `session_id`는 per-conversation `x_correlation_id`다.
- Profiling phase log에는 마지막 grace에서 cancelled request 10개가 있으나 성공 request JSONL에는 4,973개만 남는다. 본 보고서의 phase record count는 요청대로 JSONL record 기준이다.

### 요구 형식 최종 판정

이 B300 Conc40 run에서 `--warmup-requests-per-lane 10`은 **40개 live trajectory lane 각각에 mandatory t* snapshot primer와 별도로 추가 model request 10개를 허용하는 cache-pressure quota**였다. 각 initial lane의 시작 root에서 실제 관측된 warmup request 수는 **2-14개(평균 9.725)**였고, lane 전체로는 **각각 추가 10개**였으며 총 warmup은 **44 primer + 400 pressure = 444개**였다. 이 request들은 source trace의 **각 live stream별 t* 직전 predecessor primer와, 그 뒤 post-t* live-DAG request(필요하면 warmup 중 recycle된 새 root의 turn 0 포함)**에 해당했다. 따라서 “직전 10개 turn을 warmup한다”라는 설명은 **틀림**이다. 그 이유는 artifact가 444 warmup rows, 50 warmup root IDs, root/subagent 혼합을 보이고 historical AIPerf가 primer와 per-lane post-snapshot quota를 별도 구현하기 때문이다. Recycled trace에는 **profiling 중에는 미적용**되며, profiling-only 44개 root의 warmup count가 모두 0이고 historical recycle 코드가 fresh turn 0을 직접 profiling으로 dispatch하는 것으로 확인된다.


---

## 부록 A. Request JSONL schema 및 identity/index 규칙

```text
request_level_file: /tmp/b300_conc40_analysis/artifact/extracted/aiperf_artifacts/profile_export.jsonl
total_records: 5417
first_record_top_level_keys: ['metadata', 'metrics']
first_record_metadata_keys: ['agent_depth', 'benchmark_phase', 'context_overflow_skip', 'conversation_id', 'credit_issued_ns', 'record_processor_id', 'request_ack_ns', 'request_end_ns', 'request_start_ns', 'root_correlation_id', 'session_num', 'source_kind', 'source_outer_idx', 'source_trace_id', 'turn_index', 'was_cancelled', 'worker_id', 'x_correlation_id', 'x_request_id']
first_record_metrics_keys: ['decode_duration', 'e2e_output_token_throughput', 'http_req_blocked', 'http_req_chunks_received', 'http_req_chunks_sent', 'http_req_connecting', 'http_req_connection_overhead', 'http_req_connection_reused', 'http_req_data_received', 'http_req_data_sent', 'http_req_dns_lookup', 'http_req_duration', 'http_req_receiving', 'http_req_sending', 'http_req_total', 'http_req_waiting', 'input_sequence_length', 'osl_mismatch_diff_pct', 'output_sequence_length', 'output_token_count', 'prefill_throughput_per_user', 'request_latency', 'time_to_first_token', 'usage_completion_tokens', 'usage_prompt_tokens', 'usage_total_tokens']

recursive_phase_fields_and_values:
  metadata.benchmark_phase: {'warmup': 444, 'profiling': 4973}

metadata_field_presence_and_types:
  metadata.agent_depth: present=5417/5417 types={'int': 5417}
  metadata.benchmark_phase: present=5417/5417 types={'str': 5417}
  metadata.context_overflow_skip: present=5417/5417 types={'bool': 5417}
  metadata.conversation_id: present=5417/5417 types={'str': 5417}
  metadata.credit_issued_ns: present=5417/5417 types={'int': 5417}
  metadata.parent_correlation_id: present=2234/5417 types={'str': 2234}
  metadata.phase_index: present=4973/5417 types={'int': 4973}
  metadata.phase_kind: present=4973/5417 types={'str': 4973}
  metadata.phase_name: present=4973/5417 types={'str': 4973}
  metadata.profiling_index: present=4973/5417 types={'int': 4973}
  metadata.record_processor_id: present=5417/5417 types={'str': 5417}
  metadata.request_ack_ns: present=5417/5417 types={'int': 5417}
  metadata.request_end_ns: present=5417/5417 types={'int': 5417}
  metadata.request_start_ns: present=5417/5417 types={'int': 5417}
  metadata.root_correlation_id: present=5417/5417 types={'str': 5417}
  metadata.session_num: present=5417/5417 types={'int': 5417}
  metadata.source_inner_idx: present=1471/5417 types={'int': 1471}
  metadata.source_kind: present=5417/5417 types={'str': 5417}
  metadata.source_outer_idx: present=5417/5417 types={'int': 5417}
  metadata.source_trace_id: present=5417/5417 types={'str': 5417}
  metadata.turn_index: present=5417/5417 types={'int': 5417}
  metadata.was_cancelled: present=5417/5417 types={'bool': 5417}
  metadata.worker_id: present=5417/5417 types={'str': 5417}
  metadata.x_correlation_id: present=5417/5417 types={'str': 5417}
  metadata.x_request_id: present=5417/5417 types={'str': 5417}

identity_rule:
  root_id = metadata.source_trace_id (independent artifact field; never derived from conversation_id)
  validation: conversation_id root prefix before :: matched source_trace_id for all records
  root_tree_session_id = metadata.root_correlation_id
  per-conversation session_id = metadata.x_correlation_id
  metadata.session_num is credit_num (per-request counter), not a stable session identity
  lane_id is absent from JSONL; initial lane_id is joined from the aiperf.log TrajectorySource lane table

source_index_rule:
  source_outer_idx and source_inner_idx are kept separately; missing inner index remains NULL/blank
  source_position is derived from public corpus chronological order (t, outer_idx, stream/k tie breaker)
  this is the historical loader global metric-prepass total order; execution itself is per-conversation DAG/timestamp replay, not one flattened queue
  equal-(t,outer_idx) ambiguity groups among observed 94 source roots: 0

timestamp_rule:
  execution_timestamp = metadata.request_start_ns
  completion_timestamp = metadata.request_end_ns
  execution_ordinal and completion_ordinal are independently ranked; JSONL order is retained separately
  warmup rows with jsonl_ordinal == execution_ordinal: 89/444
  warmup rows with jsonl_ordinal == completion_ordinal: 227/444
  warmup rows with execution_ordinal == completion_ordinal: 98/444
```

---

## 부록 B. Historical AIPerf 818c3a5a 구현 근거

### AIPerf 818c3a5a source evidence

#### Pins

- InferenceX commit: `8767d90c11860a10668f2d66179711a9c24fc8bd`
- `git ls-tree` gitlink: `818c3a5a2922c535af6271ff296ed374e292b8e4 utils/aiperf`
- Historical AIPerf checkout: `818c3a5a2922c535af6271ff296ed374e292b8e4`
- Historical public corpus alias: `semianalysis_cc_traces_weka_062126` -> `semianalysisai/cc-traces-weka-062126`, revision `23f152f6f0f9399a85901b89a6458def0ef16729`.

#### Implementation path

1. Flag definition: `src/aiperf/config/flags/cli_config.py:2289-2303`. The description says the budget is per concurrency lane and additional to mandatory snapshot primers.
2. Phase config field: `src/aiperf/config/phases.py:365-377`.
3. Warmup request target: `src/aiperf/timing/phase/runner.py:153-170` computes `sum(baseline_counts) + requests_per_lane * lane_count`; this run logged 44 + 10*40 = 444.
4. t* snapshot construction: `src/aiperf/timing/trajectory_source.py:607-642` samples t* from the 0.25-0.75 time range, then builds the snapshot.
5. Mandatory primer selection: `src/aiperf/timing/trajectory_source.py:74-93` selects `next_turn_index - 1` for each live stream; `:422-449` counts one primer for every live stream having a pre-t* request.
6. Primer dispatch: `src/aiperf/timing/strategies/agentic_replay.py:625-768`; it prepares root and subagent primers and aligns them to t*.
7. Per-lane pressure quota: `src/aiperf/timing/strategies/agentic_replay.py:443-501`; baseline primers do not consume quota, while every later admitted `TurnToSend` increments the lane counter, regardless of root/subagent conversation.
8. Pressure replay: `src/aiperf/timing/strategies/agentic_replay.py:779-825` and `:831-929`; it resumes at the post-snapshot next request, sets max tokens to 1, removes idle delays, and continues the live DAG.
9. Profiling handoff: `src/aiperf/timing/strategies/agentic_replay.py:951-975`, `:1317-1436`, and `:1665-1803` persist the drained live streams and resume their next request in profiling.
10. Recycle: `src/aiperf/timing/strategies/agentic_replay.py:1606-1643` and `:1871-1886`; a recycled trace starts a fresh session at turn 0. The same method can be reached during accelerated warmup, so a lane may change root before its 10-request quota is full. Profiling recycle has no new warmup phase.
11. Output shortening: `_WARMUP_MAX_TOKENS = 1` at `src/aiperf/timing/strategies/agentic_replay.py:86`; all warmup turn builders apply it at `:1888-1902`.
12. Phase recording: `src/aiperf/records/record_processor_service.py:246-266` copies `credit_phase` to `benchmark_phase` and preserves trace/source indices and correlation IDs in export metadata.
13. Source provenance: `src/aiperf/dataset/loader/weka_trace.py:1612-1694` emits root/main turns with `(source_outer_idx, NULL)`; `:1932-1999` emits nested subagent turns with `(source_outer_idx, source_inner_idx)`; `:2003-2091` emits detected flat-agent chains while preserving their outer indices.
14. Historical global source ordering evidence: `src/aiperf/dataset/loader/weka_trace.py:1252-1316` orders shared trace records by `(t, outer_idx, stream_idx, k)`. No equal `(t, outer_idx)` group occurred in the 94 source roots observed here, so the derived source positions have no tie ambiguity.

#### Answers A-I

- A: `10` means 10 additional admitted model-request credits per live trajectory lane, not 10 root turns, sessions, or source rows attached to one fixed root.
- B: First, each live stream gets its last request before t* as a mandatory primer. Then the configured 10-request pressure budget replays post-t* requests from the live DAG; if a tree finishes, a fresh root at source turn 0 can continue consuming that lane's quota.
- C: Yes. Subagent requests are ordinary admitted turns for the lane quota. Artifact: pressure stage root=269, subagent=131.
- D: The phase starts with 40 initial lanes, but the quota belongs to lanes, not immutable initial roots. Warmup-time recycling produced additional root IDs.
- E: Profiling-time recycled traces do not receive this warmup; they start fresh at turn 0.
- F: Warmup output is forced to 1 token. Artifact independently shows output_sequence_length=1 for all 444 warmup records.
- G: Recorded idle gaps are not retained in the pressure stage: it runs with zero idle delay. Mandatory primers are t*-aligned and their lead is capped by the scenario's global system-idle guard (`agentic_replay.py:609-623`); the per-trace runtime idle cap is profiling-only (`timing/phase/runner.py:223-238`).
- H: Yes. Export metadata records phase directly; artifact has `benchmark_phase=warmup` for 444 rows.
- I: t* is sampled first, the live snapshot is built, pre-t* primers run, and only then the 10 post-snapshot pressure requests per lane run before profiling handoff.


---

## 부록 C. Phase counts CSV

```csv
field_path,original_value,normalized_value,count
metadata.benchmark_phase,profiling,profiling,4973
metadata.benchmark_phase,warmup,warmup,444
```


## 부록 D. Warmup distribution CSV

```csv
warmup_requests,number_of_initial_roots
2,2
3,1
4,1
5,1
6,2
8,2
10,2
11,26
12,1
13,1
14,1
```


---

## 부록 E. CSV 행 수

| 파일 | data rows |
|---|---:|
| `03_phase_counts.csv` | 2 |
| `04_initial40_root_summary.csv` | 40 |
| `05_recycled_root_summary.csv` | 54 |
| `06_warmup_request_detail.csv` | 444 |
| `07_warmup_distribution.csv` | 11 |

---

## 부록 F. Artifact inventory 및 digest

```text
actions_run_id	30849838984
artifact_id	8878177167
artifact_name	agentic_minimaxm3_tp4_conc40_kvdram-vllm-simple_spec-mtp_fp4_vllm_tp4-pp1-dcp1-pcp1-ep1-dpafalse_disagg-false_spec-mtp_conc40_b300-nv_14
api_size_in_bytes	24315650
api_digest	sha256:c4e6e61f255ebcc10c71f55c9ec036150295768bebb8ef837a03f89205ec04c0
api_expired	false
downloaded_zip_size	24315650
downloaded_zip_sha256	c4e6e61f255ebcc10c71f55c9ec036150295768bebb8ef837a03f89205ec04c0
digest_match	true

artifact_file	size_bytes
/tmp/b300_conc40_analysis/artifact/artifact.zip	120
/tmp/b300_conc40_analysis/artifact/b300_conc40_artifact.zip	24315650
/tmp/b300_conc40_analysis/artifact/download_headers.txt	1098
/tmp/b300_conc40_analysis/artifact/extracted/aiperf_artifacts/logs/aiperf.log	207686
/tmp/b300_conc40_analysis/artifact/extracted/aiperf_artifacts/profile_export.jsonl	17188529
/tmp/b300_conc40_analysis/artifact/extracted/aiperf_artifacts/profile_export_aiperf.csv	6466
/tmp/b300_conc40_analysis/artifact/extracted/aiperf_artifacts/profile_export_aiperf.json	39217
/tmp/b300_conc40_analysis/artifact/extracted/aiperf_artifacts/profile_export_aiperf_timeslices.csv	122553075
/tmp/b300_conc40_analysis/artifact/extracted/aiperf_artifacts/profile_export_aiperf_timeslices.json	51905884
/tmp/b300_conc40_analysis/artifact/extracted/aiperf_artifacts/profile_export_console.txt	13582
/tmp/b300_conc40_analysis/artifact/extracted/aiperf_artifacts/server_metrics_export.csv	26657
/tmp/b300_conc40_analysis/artifact/extracted/aiperf_artifacts/server_metrics_export.json	120720732
/tmp/b300_conc40_analysis/artifact/extracted/benchmark.log	219809
/tmp/b300_conc40_analysis/artifact/extracted/benchmark_command.txt	713
/tmp/b300_conc40_analysis/artifact/extracted/metrics_plots.png	862944
/tmp/b300_conc40_analysis/artifact/extracted/server.log	1877920
/tmp/b300_conc40_analysis/artifact/extracted/vllm_command.txt	1089
/tmp/b300_conc40_analysis/artifact/extracted/workload_distribution_plots.png	115878
/tmp/b300_conc40_analysis/artifact/extracted/workload_distribution_summary.txt	456
```


---

## 부록 G. 재현 코드

ZIP의 `code/`에는 다음 분석 코드가 포함된다.

- `generate_outputs.py`: public corpus provenance 결합, initial/recycled 분류, 9개 산출물 생성
- `scan_profile.py`: recursive phase/schema/identity frequency scan
- `inspect_corpus_structure.py`: Weka outer/nested request 구조 검사
- `quick_initial.py`: artifact log initial-lane 표와 request counts 교차검사
- `build_delivery.py`: 통합 Markdown 및 검증 manifest/ZIP 생성

코드는 `/tmp/b300_conc40_analysis/`의 다운로드 자료를 입력으로 사용한다. Raw artifact와 500MB corpus prefix 자체는 ZIP 크기를 불필요하게 키우므로 제외했으며, 필요한 artifact/corpus identity와 digest는 본 문서와 inventory에 고정되어 있다.
