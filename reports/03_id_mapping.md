# 03. Conversation-ID and root-trace mapping

## Evidence

- **Evidence:** source root universe는 `393`개이고, profiling H200 row는 `2,491`개 / 관측 root trace는 `11`개다.
- **Evidence:** `metadata.source_trace_id`가 root provenance로 기록된 row는 `2,491/2,491` (100.0%)이다. 이는 `::sa:` 문자열 절단 추정이 아니라 loader가 보존한 명시적 source-root metadata다.
- **Evidence:** source root ID 집합과 일치한 profiling row는 `2,491/2,491` (100.0%)이다.
- **Evidence:** loader metadata association (`source_trace_id` + source outer/inner request index)은 `2,491/2,491` (100.0%)이고, input length까지 호환되어 strict exact-turn으로 분류된 row는 `21/2,491` (0.8%)이다.
- **Evidence:** Per-concurrency mapping summary:

| concurrency | h200_request_count | h200_root_ids | matched_root_ids | root_match_rate | loader_metadata_turn_match_rate | exact_turn_match_count | exact_turn_match_rate | explicit_source_trace_id_match_rate |
|---|---|---|---|---|---|---|---|---|
| 1 | 355 | 2 | 2 | 1 | 1 | 1 | 0.0028169 | 1 |
| 2 | 395 | 4 | 4 | 1 | 1 | 1 | 0.00253165 | 1 |
| 3 | 455 | 7 | 7 | 1 | 1 | 5 | 0.010989 | 1 |
| 4 | 379 | 8 | 8 | 1 | 1 | 5 | 0.0131926 | 1 |
| 5 | 250 | 7 | 7 | 1 | 1 | 2 | 0.008 | 1 |
| 6 | 197 | 9 | 9 | 1 | 1 | 3 | 0.0152284 | 1 |
| 7 | 241 | 9 | 9 | 1 | 1 | 3 | 0.0124481 | 1 |
| 8 | 219 | 11 | 11 | 1 | 1 | 1 | 0.00456621 | 1 |
- **Evidence:** Normalization rules across all raw H200 rows:

| concurrency | normalization_rule | h200_request_count | distinct_conversation_ids | distinct_root_trace_ids | source_matched_request_count | source_request_match_rate |
|---|---|---|---|---|---|---|
| 1 | explicit_metadata_source_trace_id | 638 | 30 | 5 | 638 | 1 |
| 2 | explicit_metadata_source_trace_id | 954 | 49 | 7 | 954 | 1 |
| 3 | explicit_metadata_source_trace_id | 1025 | 65 | 10 | 1025 | 1 |
| 4 | explicit_metadata_source_trace_id | 584 | 47 | 10 | 584 | 1 |
| 5 | explicit_metadata_source_trace_id | 300 | 18 | 7 | 300 | 1 |
| 6 | explicit_metadata_source_trace_id | 241 | 32 | 9 | 241 | 1 |
| 7 | explicit_metadata_source_trace_id | 313 | 39 | 9 | 313 | 1 |
| 8 | explicit_metadata_source_trace_id | 302 | 38 | 11 | 302 | 1 |

## Inference

- **Inference:** a `::sa:` split remains a fallback normalization rule. Where `metadata.source_trace_id` is present, the direct loader field is stronger root-ID evidence.

## Unknown

- **Unknown:** loader metadata association is not, by itself, a strict source/H200 turn identity. This pipeline labels a strict exact turn only when that association also has compatible input length; it does not claim independently verified request timing/order identity.
- **Unknown:** The absence of an unmatched-example row does not prove full source-turn coverage; it only means no unmatched H200 root-ID example was emitted by this stage.

_No unmatched H200 root-ID example rows were emitted._
