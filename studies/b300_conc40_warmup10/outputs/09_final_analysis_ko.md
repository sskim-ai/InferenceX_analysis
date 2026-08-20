# B300 Conc40 `warmup-requests-per-lane=10` 실제 동작 분석

## 1. 결론

이 run의 `10`은 **각 initial root의 warmup row를 10개로 맞춘 값이 아니라, 40개 live trajectory lane 각각에 필수 snapshot primer 이후 추가로 허용한 model-request 10개**였다. Artifact에는 필수 primer 44개와 추가 pressure request 400개, 합계 444개의 warmup record가 있다. pressure replay 도중 tree가 끝나면 같은 lane에서 새 root가 turn 0부터 이어져 quota를 소비했으므로 initial root별 warmup record 수는 동일하지 않다.

## 2. Global summary

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

## 3. Initial 40개 표

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

## 4. `warmup=10`의 정확한 의미

- H1(각 initial root가 정확히 10 warmup rows): **거짓**. 정확히 10인 initial root는 2/40개뿐이고 범위는 2-14다. 다만 코드의 lane counter와 run log는 **각 lane의 추가 pressure quota가 정확히 10**에 도달했다고 확인한다.
- H2(그 10개가 profiling 직전 source request 10개): **거짓**. 필수 primer는 t* 직전의 각 live stream별 마지막 request이고, 추가 10개는 t* 이후 live DAG 실행이다. Initial root 기준 source-contiguous warmup은 32/40개이고, profile이 실제 존재한 26개 중 전체 warmup set이 첫 profile source request를 즉시 선행한 경우는 19/26개뿐이다. 나머지는 DAG stream 간 source-order interleave 또는 gap이 있다.
- H3(10 root turns): **거짓**. 전체 warmup 444개 중 root conversation 302, subagent 142; 추가 pressure 400개만 보아도 root 269, subagent 131다.
- H4(t* 이전/이후): **두 단계**다. 44개 mandatory primer는 t* 이전 마지막 request이고, 그 뒤 400개 pressure request는 post-snapshot/t* 이후 경로를 zero-idle, one-token으로 진행한다.

## 5. Recycled trace 검증

Artifact에서 profiling-only root는 44개이며 모두 `warmup_requests=0`, `profile_requests>0`이다. 그중 source 전체가 관측된 root는 18개이고, 이 중 18개는 historical source order의 첫 request부터 profiling이 시작했다. Initial 40 중 profiling까지 같은 root로 남은 것은 26개이며, 나머지 14개는 warmup pressure 중 끝났다. Warmup 단계 자체에서도 새 root 10개가 등장했다. 상세 분류는 `05_recycled_root_summary.csv`에 있다.

## 6. AIPerf 818c3a5a 코드 근거

gitlink와 checkout 모두 `818c3a5a2922…`로 고정했다. 구현은 (1) t* snapshot 선택, (2) live stream별 pre-t* predecessor primer, (3) primer와 별개인 lane별 10회 admission counter, (4) zero-idle/1-token pressure replay, (5) live-state profiling handoff, (6) profiling recycle의 fresh turn-0 시작 순서다. 정확한 파일·라인과 A-I 답은 `08_aiperf_818c3a5a_source_evidence.md`에 정리했다.

## 7. 남은 불확실성

- JSONL에는 literal `lane_id`가 없다. Initial lane은 artifact log의 TrajectorySource 표에서 확정했지만 recycled root의 lane 번호는 request record만으로 복원하지 않았다.
- `session_num`은 historical source상 credit number이므로 session identity로 쓰지 않았다. Summary의 `session_id`는 tree-level `root_correlation_id`, detail의 `session_id`는 per-conversation `x_correlation_id`다.
- Profiling phase log에는 마지막 grace에서 cancelled request 10개가 있으나 성공 request JSONL에는 4,973개만 남는다. 본 보고서의 phase record count는 요청대로 JSONL record 기준이다.

## 요구 형식 최종 판정

이 B300 Conc40 run에서 `--warmup-requests-per-lane 10`은 **40개 live trajectory lane 각각에 mandatory t* snapshot primer와 별도로 추가 model request 10개를 허용하는 cache-pressure quota**였다. 각 initial lane의 시작 root에서 실제 관측된 warmup request 수는 **2-14개(평균 9.725)**였고, lane 전체로는 **각각 추가 10개**였으며 총 warmup은 **44 primer + 400 pressure = 444개**였다. 이 request들은 source trace의 **각 live stream별 t* 직전 predecessor primer와, 그 뒤 post-t* live-DAG request(필요하면 warmup 중 recycle된 새 root의 turn 0 포함)**에 해당했다. 따라서 “직전 10개 turn을 warmup한다”라는 설명은 **틀림**이다. 그 이유는 artifact가 444 warmup rows, 50 warmup root IDs, root/subagent 혼합을 보이고 historical AIPerf가 primer와 per-lane post-snapshot quota를 별도 구현하기 때문이다. Recycled trace에는 **profiling 중에는 미적용**되며, profiling-only 44개 root의 warmup count가 모두 0이고 historical recycle 코드가 fresh turn 0을 직접 profiling으로 dispatch하는 것으로 확인된다.
