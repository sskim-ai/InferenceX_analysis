# Preliminary local-server evidence needed

This is a checklist for the next analysis phase, not the final internal-GPT prompt.

## Configuration and topology

- Exact target checkpoint, quantization/precision, GPU SKU/count, TP/DP/PP/EP, and aggregated topology evidence.
- MTP/speculative algorithm, steps, draft tokens, acceptance configuration, and max model/batch limits.
- KV dtype, page/block size, physical GPU KV slots/GiB, prefix-cache configuration, offload policy, and max running requests.

## Request-level evidence

- source_trace_id, source_outer_idx, source_inner_idx, source_conversation_path, turn_index, timestamps, worker/routing ID.
- input tokens with documented semantics; cache-read/load/store counters with scope; output tokens; TTFT; ITL/decode-duration definition; E2E; cancellation/error and context-overflow fields.

## IDs to check locally

- Confirm whether each resolved public ID appears in local data: `0196085d85d2075a50b74cd8795ffbdcea9a`, `02bc0afb13f7a2d9efa86c28511261d85c0e`, `07dd40536557a1d6440a923557c3129dc929`, `264478eebbb2068593da2293ea8b67b31d4e`, `debc7f69e2c2fb94909ecdca600b0a4abd48`.

## ID03 cpy1–cpy8 evidence contract

- For each local label 07dd405_cpy1 through 07dd405_cpy8, extract configured concurrency; observed maximum simultaneous requests; independent root-session count; distinct conversation IDs; source-trace-ID count; request/success count per copy; and start/end timestamps.
- Verify whether cpyN means N copies of the same canonical trace, AIPerf concurrency N, or something else. Until that proof exists, do not write cpyN == concurrency N as Evidence.
- Extract the exact join fields and metric semantics in handoff/id03_local_join_contract.md, including source indices, source path/turn validation, TTFT, ITL, E2E, output length, cache counters, success, error, and context-overflow status.
- Apply the 202,752 context-fit rule only with target logical prompt tokens plus requested output limit or a documented loader/server rule; do not substitute public source-input or profile input sequence tokens.

## Why these fields matter

- Public MTP replay exposes a profile cache counter whose ratio to usage prompt tokens can exceed one, so exact local metric scope is essential before comparison.
- Physical KV allocation and MTP acceptance require startup/runtime evidence rather than architecture assumptions.
