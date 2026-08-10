# 10. Limitations

## Evidence

- The workload’s source Claude labels are preserved only as source-workload provenance. The target replay model is GLM-5.2 FP8.
- Source `api_time` is not an H200 latency measurement.
- Raw profile records can repeat a source key; a shared H200 system serves all requests.

## Inference

- c8/c12/c16 coverage differences can bias unpaired averages.

## Unknown

- Per-ID GPU utilisation, exact GPU allocation, and physical cache residency cannot be inferred from a conversation ID.
- MTP acceptance and KV allocation require actual runtime counters/log scope; absent metrics remain Unknown.
