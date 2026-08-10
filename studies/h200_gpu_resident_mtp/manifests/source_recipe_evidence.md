# Source recipe evidence — run 31235207041

## Evidence

- The successful GitHub Actions run is [31235207041](https://github.com/SemiAnalysisAI/InferenceX/actions/runs/31235207041), titled `Run Sweep - Refresh GLM-5.2 FP8 H200 AgentX 2P2D with MTP`.  Its canonical run head is [`48ec5aa103dbf8e671580cd191eeef7e7186c802`](https://github.com/SemiAnalysisAI/InferenceX/commit/48ec5aa103dbf8e671580cd191eeef7e7186c802), not the PR's later post-run head `bc83b176...`.
- The associated PR is [#2529](https://github.com/SemiAnalysisAI/InferenceX/pull/2529), which added the recipe and changed the benchmark matrix, changelog, and H200 launcher.
- The canonical at-run recipe is [`benchmarks/multi_node/srt-slurm-recipes/sglang/glm5.2/agentic/disagg-h200-2p2d-pcp8-tp8-dp8-mtp.yaml`](https://github.com/SemiAnalysisAI/InferenceX/blob/48ec5aa103dbf8e671580cd191eeef7e7186c802/benchmarks/multi_node/srt-slurm-recipes/sglang/glm5.2/agentic/disagg-h200-2p2d-pcp8-tp8-dp8-mtp.yaml). Its Git blob SHA-1 is `8b02f5e857fb30fa2713f3250e0ba1c41e7544c1`; SHA-256 of the fetched raw bytes is `e73585b96e942f094b349b6f36fbf52ac1e71f6e10884feff1d6b504414a4bbe`.
- The execution matrix is [`configs/nvidia-master.yaml`, lines 7585–7650](https://github.com/SemiAnalysisAI/InferenceX/blob/48ec5aa103dbf8e671580cd191eeef7e7186c802/configs/nvidia-master.yaml#L7585-L7650). It selects the recipe for exactly c8, c12, and c16, sets `spec-decoding: mtp` and `kv-offloading: none`, and declares two prefill workers with `tp: 1`, `pcp-size: 8`, plus two decode workers with `tp: 8`, `dp-attn: true`.
- The finished matrix jobs are c8 (`93046426099`), c12 (`93046426106`), and c16 (`93046426113`). Their job labels identify `2P (TP1/PCP8) x 2D (TP8/DPA) mtp` on `cluster:h200-dgxc`.

### Relevant at-run recipe extract

The key/value excerpts below preserve source values and line ranges; they are not a standalone, parseable YAML document. Use the linked full recipe and its SHA-256 for reproduction.

```yaml
# lines 3-6
# The released SGLang image does not combine MTP with HiSparse, so decode KV
# cache remains GPU-resident.

# lines 8-28
model:
  path: "hf:zai-org/GLM-5.2-FP8"
  container: "lmsysorg/sglang:v0.5.16-cu130"
  precision: "fp8"
resources:
  gpu_type: h200
  gpus_per_node: 8
  prefill_nodes: 2
  decode_nodes: 2
  prefill_workers: 2
  decode_workers: 2
  gpus_per_prefill: 8
  gpus_per_decode: 8

# lines 34-46
frontend:
  type: dynamo
  nginx_session_affinity: true
  nginx_session_affinity_header: X-Correlation-ID
  args:
    router-mode: "kv"

# lines 59-70
decode_environment:
  SGLANG_MOONCAKE_CUSTOM_MEM_POOL: "True"
  SGLANG_SIMULATE_ACC_LEN: "2.99"
  SGLANG_SIMULATE_ACC_METHOD: "match-expected"
  SGLANG_SIMULATE_ACC_TOKEN_MODE: "real-draft-token"

# prefill lines 80-101
tp-size: 8
attn-cp-size: 8
enable-prefill-cp: true
disaggregation-transfer-backend: mooncake
disaggregation-mode: prefill
kv-cache-dtype: fp8_e4m3
context-length: 1048576
max-total-tokens: 1048576
max-running-requests: 32
speculative-algorithm: EAGLE
speculative-num-steps: 3
speculative-eagle-topk: 1
speculative-num-draft-tokens: 4
enable-cache-report: true

# decode lines 110-131
tp-size: 8
dp-size: 8
enable-dp-attention: true
disaggregation-transfer-backend: mooncake
disaggregation-mode: decode
kv-cache-dtype: fp8_e4m3
dsa-decode-backend: flashmla_kv
context-length: 1048576
max-total-tokens: 1048576
max-running-requests: 200
page-size: 64
disable-radix-cache: true
speculative-algorithm: EAGLE
speculative-num-steps: 3
speculative-eagle-topk: 1
speculative-num-draft-tokens: 4
enable-cache-report: true

# lines 140-153
benchmark:
  command: bash /infmax-workspace/benchmarks/multi_node/agentic_srt.sh
  env:
    AIPERF_REQUIRED_SERVER_METRIC_PREFIX: "sglang:"
    WEKA_LOADER_OVERRIDE: "semianalysis_cc_traces_weka_062126"
```

The full structured evidence, checksums, source URLs, API values, and caveats are in [source_recipe_evidence.json](source_recipe_evidence.json).

## Inference

- The allocation implied by the recipe is **32 H200 GPUs**: `(2 prefill nodes × 8) + (2 decode nodes × 8)`. This is a topology calculation, not per-conversation GPU attribution.
- GPU-resident decode KV and HiSparse-off are the intended configuration with high confidence: the matrix explicitly says `kv-offloading: none`, and the recipe comment says MTP and HiSparse are not combined in the released image.

## Unknown

- The actual server invocation must resolve a source-level discrepancy: `nvidia-master.yaml` and Actions labels specify **TP1/PCP8** prefill, whereas the selected recipe's prefill `sglang_config` lists `tp-size: 8` and `attn-cp-size: 8`. Server startup logs are the required authority for effective runtime flags.
- The recipe cannot prove observed physical KV blocks, token slots, GiB, remaining HBM, runtime cache residency, accepted/drafted MTP tokens, or actual worker routing. Those require the separate server-log and raw-artifact analysis.
