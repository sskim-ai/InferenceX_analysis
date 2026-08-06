# 02. H200 profile_export schema inventory

## Evidence

- **Evidence:** H200 raw record rows `4,357`, valid profiling rows `2,491`, excluded rows `1,866`.

| concurrency | record_count | profiling_phase_count | warmup_count | missing_phase_count | error_count | cancelled_count |
|---|---|---|---|---|---|---|
| 1 | 638 | 355 | 283 | 0 | 0 | 0 |
| 2 | 954 | 395 | 559 | 0 | 0 | 0 |
| 3 | 1025 | 455 | 570 | 0 | 0 | 0 |
| 4 | 584 | 379 | 205 | 0 | 0 | 0 |
| 5 | 300 | 250 | 50 | 0 | 0 | 0 |
| 6 | 241 | 197 | 44 | 0 | 0 | 0 |
| 7 | 313 | 241 | 72 | 0 | 0 | 0 |
| 8 | 302 | 219 | 83 | 0 | 0 | 0 |

Field inventory:

| field | presence_rate | dtype | null_rate | min | max | observed_unit | observed_unit_values | inferred_unit |
|---|---|---|---|---|---|---|---|---|
| metadata.agent_depth | 1 | int | 0 | 0 | 1 |  |  | unknown |
| metadata.benchmark_phase | 1 | str | 0 |  |  |  |  | unknown |
| metadata.context_overflow_skip | 1 | bool | 0 |  |  |  |  | unknown |
| metadata.conversation_id | 1 | str | 0 |  |  |  |  | unknown |
| metadata.credit_issued_ns | 1 | int | 0 | 1.78464e+18 | 1.78464e+18 |  |  | nanoseconds |
| metadata.parent_correlation_id | 0.479624 | str | 0 |  |  |  |  | unknown |
| metadata.record_processor_id | 1 | str | 0 |  |  |  |  | unknown |
| metadata.request_ack_ns | 1 | int | 0 | 1.78464e+18 | 1.78464e+18 |  |  | nanoseconds |
| metadata.request_end_ns | 1 | int | 0 | 1.78464e+18 | 1.78464e+18 |  |  | nanoseconds |
| metadata.request_start_ns | 1 | int | 0 | 1.78464e+18 | 1.78464e+18 |  |  | nanoseconds |
| metadata.root_correlation_id | 1 | str | 0 |  |  |  |  | unknown |
| metadata.session_num | 1 | int | 0 | 0 | 355 |  |  | unknown |
| metadata.source_inner_idx | 0.315047 | int | 0 | 0 | 33 |  |  | unknown |
| metadata.source_kind | 1 | str | 0 |  |  |  |  | unknown |
| metadata.source_outer_idx | 1 | int | 0 | 0 | 201 |  |  | unknown |
| metadata.source_trace_id | 1 | str | 0 |  |  |  |  | unknown |
| metadata.turn_index | 1 | int | 0 | 0 | 190 |  |  | unknown |
| metadata.was_cancelled | 1 | bool | 0 |  |  |  |  | unknown |
| metadata.worker_id | 1 | str | 0 |  |  |  |  | unknown |
| metadata.x_correlation_id | 1 | str | 0 |  |  |  |  | unknown |
| metadata.x_request_id | 1 | str | 0 |  |  |  |  | unknown |
| metrics.e2e_output_token_throughput.unit | 1 | str | 0 |  |  |  |  | unknown |
| metrics.e2e_output_token_throughput.value | 1 | float | 0 | 0.0124844 | 34.5836 | tokens/sec/user | tokens/sec/user | tokens/sec/user |
| metrics.http_req_blocked.unit | 1 | str | 0 |  |  |  |  | unknown |
| metrics.http_req_blocked.value | 1 | float | 0 | 0 | 0 | ms | ms | ms |
| metrics.http_req_chunks_received.unit | 1 | str | 0 |  |  |  |  | unknown |
| metrics.http_req_chunks_received.value | 1 | int | 0 | 1 | 172 | count | count | count |
| metrics.http_req_chunks_sent.unit | 1 | str | 0 |  |  |  |  | unknown |
| metrics.http_req_chunks_sent.value | 1 | int | 0 | 1 | 1 | count | count | count |
| metrics.http_req_connecting.unit | 1 | str | 0 |  |  |  |  | unknown |
| metrics.http_req_connecting.value | 1 | float | 0 | 0 | 20.334 | ms | ms | ms |
| metrics.http_req_connection_overhead.unit | 1 | str | 0 |  |  |  |  | unknown |
| metrics.http_req_connection_overhead.value | 1 | float | 0 | 0 | 20.334 | ms | ms | ms |
| metrics.http_req_connection_reused.unit | 1 | str | 0 |  |  |  |  | unknown |
| metrics.http_req_connection_reused.value | 1 | int | 0 | 0 | 1 | ratio | ratio | ratio |
| metrics.http_req_data_received.unit | 1 | str | 0 |  |  |  |  | unknown |
| metrics.http_req_data_received.value | 1 | float | 0 | 0.584961 | 86.9912 | KB | KB | KB |
| metrics.http_req_data_sent.unit | 1 | str | 0 |  |  |  |  | unknown |
| metrics.http_req_data_sent.value | 1 | float | 0 | 2.0166 | 2662.24 | KB | KB | KB |
| metrics.http_req_dns_lookup.unit | 1 | str | 0 |  |  |  |  | unknown |

Key request-metric fields (per concurrency):

| concurrency | field | present_count | presence_rate | min | max | observed_unit | inferred_unit |
|---|---|---|---|---|---|---|---|
| 1 | metrics.input_sequence_length.value | 638 | 1 | 1 | 158683 | tokens | tokens |
| 2 | metrics.input_sequence_length.value | 954 | 1 | 1 | 158682 | tokens | tokens |
| 3 | metrics.input_sequence_length.value | 1025 | 1 | 1 | 158683 | tokens | tokens |
| 4 | metrics.input_sequence_length.value | 584 | 1 | 1 | 154539 | tokens | tokens |
| 5 | metrics.input_sequence_length.value | 300 | 1 | 1 | 148188 | tokens | tokens |
| 6 | metrics.input_sequence_length.value | 241 | 1 | 1 | 148189 | tokens | tokens |
| 7 | metrics.input_sequence_length.value | 313 | 1 | 1 | 148186 | tokens | tokens |
| 8 | metrics.input_sequence_length.value | 302 | 1 | 1 | 148187 | tokens | tokens |
| 1 | metrics.inter_token_latency.value | 197 | 0.308777 | 27.3858 | 41.2217 | ms | ms |
| 2 | metrics.inter_token_latency.value | 119 | 0.124738 | 26.8077 | 81.8549 | ms | ms |
| 3 | metrics.inter_token_latency.value | 169 | 0.164878 | 25.6817 | 80.2255 | ms | ms |
| 4 | metrics.inter_token_latency.value | 267 | 0.457192 | 25.9496 | 85.432 | ms | ms |
| 5 | metrics.inter_token_latency.value | 131 | 0.436667 | 27.66 | 86.9787 | ms | ms |
| 6 | metrics.inter_token_latency.value | 128 | 0.53112 | 27.8269 | 108.022 | ms | ms |
| 7 | metrics.inter_token_latency.value | 187 | 0.597444 | 27.7619 | 103.097 | ms | ms |
| 8 | metrics.inter_token_latency.value | 167 | 0.55298 | 26.4688 | 93.3397 | ms | ms |
| 1 | metrics.output_sequence_length.value | 638 | 1 | 1 | 10180 | tokens | tokens |
| 2 | metrics.output_sequence_length.value | 954 | 1 | 1 | 10912 | tokens | tokens |
| 3 | metrics.output_sequence_length.value | 1025 | 1 | 1 | 5814 | tokens | tokens |
| 4 | metrics.output_sequence_length.value | 584 | 1 | 1 | 10180 | tokens | tokens |
| 5 | metrics.output_sequence_length.value | 300 | 1 | 1 | 9543 | tokens | tokens |
| 6 | metrics.output_sequence_length.value | 241 | 1 | 1 | 9186 | tokens | tokens |
| 7 | metrics.output_sequence_length.value | 313 | 1 | 1 | 9186 | tokens | tokens |
| 8 | metrics.output_sequence_length.value | 302 | 1 | 1 | 9186 | tokens | tokens |
| 1 | metrics.request_latency.value | 638 | 1 | 308.538 | 314549 | ms | ms |
| 2 | metrics.request_latency.value | 954 | 1 | 528.497 | 339064 | ms | ms |
| 3 | metrics.request_latency.value | 1025 | 1 | 636.656 | 214077 | ms | ms |
| 4 | metrics.request_latency.value | 584 | 1 | 1000.64 | 391692 | ms | ms |
| 5 | metrics.request_latency.value | 300 | 1 | 1729.8 | 374456 | ms | ms |
| 6 | metrics.request_latency.value | 241 | 1 | 3682.18 | 426637 | ms | ms |
| 7 | metrics.request_latency.value | 313 | 1 | 3987.09 | 541149 | ms | ms |
| 8 | metrics.request_latency.value | 302 | 1 | 3603.97 | 491368 | ms | ms |
| 1 | metrics.time_to_first_output_token.value | 638 | 1 | 308.538 | 80099.9 | ms | ms |
| 2 | metrics.time_to_first_output_token.value | 954 | 1 | 373.577 | 206759 | ms | ms |
| 3 | metrics.time_to_first_output_token.value | 1025 | 1 | 317.361 | 214077 | ms | ms |
| 4 | metrics.time_to_first_output_token.value | 584 | 1 | 341.75 | 196617 | ms | ms |
| 5 | metrics.time_to_first_output_token.value | 300 | 1 | 711.093 | 273036 | ms | ms |
| 6 | metrics.time_to_first_output_token.value | 241 | 1 | 1227.7 | 320695 | ms | ms |
| 7 | metrics.time_to_first_output_token.value | 313 | 1 | 3630.17 | 404334 | ms | ms |
| 8 | metrics.time_to_first_output_token.value | 302 | 1 | 3603.97 | 449510 | ms | ms |
| 1 | metrics.time_to_first_token.value | 638 | 1 | 308.538 | 80099.9 | ms | ms |
| 2 | metrics.time_to_first_token.value | 954 | 1 | 373.577 | 206759 | ms | ms |
| 3 | metrics.time_to_first_token.value | 1025 | 1 | 317.361 | 214077 | ms | ms |
| 4 | metrics.time_to_first_token.value | 584 | 1 | 341.75 | 196617 | ms | ms |
| 5 | metrics.time_to_first_token.value | 300 | 1 | 711.093 | 273036 | ms | ms |
| 6 | metrics.time_to_first_token.value | 241 | 1 | 1227.7 | 320695 | ms | ms |
| 7 | metrics.time_to_first_token.value | 313 | 1 | 3630.17 | 404334 | ms | ms |
| 8 | metrics.time_to_first_token.value | 302 | 1 | 3603.97 | 449510 | ms | ms |

## Inference

- **Inference:** `inter_token_latency` is named request-level ITL/TPOT only to the extent established by the InferenceX aggregation source; it is not a per-GPU decode measurement.

## Unknown

- **Unknown:** ITL is observed for `1,365/2,491` valid profiling rows; missing per-row values and absent actual cache-residency telemetry limit metric interpretation.
