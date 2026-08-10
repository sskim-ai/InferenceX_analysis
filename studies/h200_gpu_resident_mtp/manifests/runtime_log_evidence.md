# Runtime server-log evidence — run 31235207041

This manifest uses only the downloaded server-log artifacts for c8, c12, and c16.  Line references are one-based line numbers in the named member inside the corresponding `multinode_server_logs.tar.gz`.  Raw log archives remain outside Git.

## Evidence

- All three launch logs report `32 backend / 40 configured (8/node, h200)`.  The extra eight configured GPUs belong to the five-node allocation context; the c8 resource snapshot records four backend nodes with eight backend GPUs each.  The launcher starts four backend processes and waits for `2 prefills and 2 decodes`.

  - c8: `sweep_67841.log:111-117,130-146,173-175`; `resource_snapshot.json:gpus,cpus.backend_node_allocations`
  - c12: `sweep_67842.log:111-117,130-146,173-175`
  - c16: `sweep_67843.log:112-118,131-147,174-176`

- The actual prefill command is `--tp-size 8 --attn-cp-size 8 --enable-prefill-cp`, with Mooncake transfer, FP8 E4M3 KV, a 1,048,576 token limit, 32 running requests, and EAGLE `steps=3`, `topk=1`, `draft-tokens=4`.  The prefill `ServerArgs` repeat the material flags (`worker-*_prefill_w0.out:36`).

- The actual decode command is `--tp-size 8 --dp-size 8 --enable-dp-attention`, with Mooncake, FP8 E4M3 KV, 64-token pages, 200 running requests, and `--disable-radix-cache`.  Decode `ServerArgs` directly record `enable_hisparse=False`, `cpu_offload_gb=0`, `enable_lmcache=False`, and `disaggregation_decode_enable_offload_kvcache=False` (`worker-*_decode_w0.out:36`).  Each decode worker also logs: “KV cache is forced as chunk cache for decode server” (`worker-*_decode_w0.out:16`).

- Prefill startup records a scheduler pool of **16,384 blocks × 64 tokens = 1,048,576 logical tokens** for a prefill worker.  Individual prefill ATTN_CP/TP ranks log FP8 allocation components of **6.93 GB or 7.70 GB**, plus a separately logged **0.77 GB** component.  Representative references are c8 `worker-9_prefill_w0.out:544-575,581,691`; the same values occur in c12 `worker-5_prefill_w0.out:544-575,599,691` and c16 `worker-5_prefill_w0.out:544-575,603,691`.

- Decode startup replaces the configured `max_total_tokens=1048576` with a logged **profiled value of 218,560**.  Individual DP/TP ranks then log FP8 allocation components of **12.51 GB** and separately **0.16 GB**.  Representative references are c8 `worker-4_decode_w0.out:528-567`, c12 `worker-8_decode_w0.out:528-567`, and c16 `worker-8_decode_w0.out:528-567`.

- The actual decode-process environment contains `SGLANG_SIMULATE_ACC_LEN=2.99`, `SGLANG_SIMULATE_ACC_METHOD=match-expected`, and `SGLANG_SIMULATE_ACC_TOKEN_MODE=real-draft-token` in all three runs (c8 `sweep_67841.log:139,143`; c12 `sweep_67842.log:139,143`; c16 `sweep_67843.log:140,144`).  Later decode-batch lines report sampled `accept len` values of 2.98–3.00 and `accept rate` values of 0.66–0.67 (c8 `worker-4_decode_w0.out:1071-1074`; c12 `worker-8_decode_w0.out:1073-1076`; c16 `worker-8_decode_w0.out:1076-1079`).

- Dynamo frontend logs show dynamic selection across both prefill workers and both decode workers, with decode DP ranks: c8 `worker-7_frontend_2.out:148-161`, c12 `worker-8_frontend_1.out:120-131`, and c16 `worker-9_frontend_0.out:150-167`.  This is routing evidence, not a workload-balance calculation.

- AIPerf warned in all three runs that `usage.prompt_tokens_details.cached_tokens` was absent despite cache reporting being enabled: c8 `benchmark.out:437-438`, c12 `benchmark.out:447-448`, c16 `benchmark.out:458-459`.  That establishes missing **request-usage cache-read telemetry**, not absence of cache activity.

## Inference

- **High confidence:** Runtime launch commands resolve the source-level TP1/PCP8 versus recipe discrepancy: effective prefill launch was TP8 with attention CP8 and prefill CP enabled.  The conclusion comes from the actual launch command and `ServerArgs`, not a matrix label.

- **High confidence:** Decode KV was GPU-resident for this replay in the practical configuration sense: FP8 CUDA KV allocation is logged, HiSparse is false, and CPU/offload/LMCache paths are disabled.  This does not give a per-conversation hardware attribution.

- **High confidence:** MTP/EAGLE with the synthetic acceptance configuration was active during replay.  Its benchmark decode TPS therefore includes this MTP behavior and must not be treated as a non-speculative decode-only result.

- **Medium confidence:** A decode rank’s logged allocation is 12.51 GB plus a separate 0.16 GB component (12.67 GB if additive).  Preserve the two values separately until the DSA layer-split memory semantics are confirmed; do not multiply them into a cluster-wide physical KV total.

## Unknown

- The physical semantics of the separately logged DSA allocation components, including a definitive global/per-GPU KV pool total.
- Run-wide accepted-token and draft-token totals or a request-weighted acceptance rate.  The logs provide samples, not a canonical aggregate.
- Request-level cache-read tokens.  AIPerf explicitly reports the standard cached-token field as absent.
- Complete worker balance and any fixed request/conversation-to-GPU affinity.  Dynamic routing is observable, but the shared 32×H200 system cannot support fixed ID-to-GPU claims.

The machine-readable companion is [runtime_log_evidence.json](runtime_log_evidence.json).
