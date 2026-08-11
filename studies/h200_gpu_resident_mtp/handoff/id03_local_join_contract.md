# ID03 local cpy join contract

## Scope

- Public comparison trace: 07dd40536557a1d6440a923557c3129dc929.
- This is an extraction and matching contract for a later private analysis. It is not a claim that any local cpy label equals public H200 concurrency.

## Required local fields

| Group | Fields |
| --- | --- |
| Copy identity | local_run_label; local_copy_label; local_copy_index; configured_concurrency; observed_max_simultaneous_requests; independent_root_session_count; conversation_id; session_num |
| Source identity | source_trace_id; source_outer_idx; source_inner_idx; source_conversation_path; turn_index; source_branch_type; source_branch_request_index |
| Timing and routing | local_raw_record_ordinal; local_source_file_or_log_partition; request_start; request_end; request ID/correlation ID if available; worker/routing ID |
| Token semantics | input_tokens; input_token_semantics; cache_read_tokens; cache_read_metric_semantics; cache_write_tokens; cache_write_metric_semantics; output_tokens; requested_output_limit; context_fit_rule_or_config_source |
| Outcome and filtering | ttft_ms; itl_ms; e2e_ms; success; success_filter_version; error; error_text_or_category; context_overflow |

## Canonical exact key

source_trace_id + source_outer_idx + source_inner_idx

- Preserve raw source indices and also publish normalized join fields. The public reference uses `source_inner_idx_exact_key_normalized=-1` for a documented root-level null inner index. Use -1 only for that established root-level-null case; do not invent a sentinel when the local source-inner value is genuinely unknown.
- source_conversation_path and turn_index are validation fields. Report match_validation_status as `high_confidence_exact`, `key_match_validation_missing`, `key_match_validation_conflict`, or `unmatched` rather than silently accepting a conflict.
- Preserve local_copy_label and local_copy_index outside the exact key. They identify separate local replay instances and must not be deduplicated as if they were duplicate requests.

## Required cpy1–cpy8 semantics check

- For each label, report configured concurrency, observed maximum simultaneous requests, independent root sessions, distinct conversation IDs, source trace IDs, requests per copy, successful requests per copy, and start/end timestamps.
- Only then determine whether cpy8 means eight independent same-trace sessions, AIPerf concurrency 8, another copy mechanism, or an unknown experiment label.

## Strict comparison subsets

- Strict TTFT: high-confidence exact key, successful request in both systems, TTFT present.
- Strict decode: strict TTFT conditions, output_tokens > 1, ITL present, and equal observed output length. Keep output-length-different rows for coverage analysis but not strict ITL/TPS ratios.
- Keep unmatched, key-match-validation-missing, key-match-validation-conflict, error, cancellation, and context-overflow rows as explicit categories.

## Context-fit rule

- A local 202,752-context compatibility label requires target logical prompt tokens plus requested output limit <= 202752, or the exact documented loader/server fit condition. Do not use source input tokens or public profile input_sequence_length as substitutes.

## Post-extraction metric definitions

- weighted ITL = sum(itl_ms * (output_tokens - 1)) / sum(output_tokens - 1) for valid decode rows.
- weighted decode TPS = 1000 / weighted ITL.
- wall span = max(request_end) - min(request_start); wall output TPS = total output tokens / wall span.
- cpyN TPS retention = weighted_decode_tps_cpyN / weighted_decode_tps_cpy1; median TTFT inflation = median_ttft_cpyN / median_ttft_cpy1.

## Interpretation guardrails

- Public H200 c8/c12/c16 is mixed-root, P/D-disaggregated, 32×H200, and MTP-enabled. Local cpy data may have a different workload composition, topology, MTP state, and context limit.
- Treat source model labels as workload provenance only. Do not infer GPU affinity, per-ID GPU count, or a causal HiSparse/KV/MTP contribution from this contract.
