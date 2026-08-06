# 08. Limitations

## Evidence

- **Evidence:** source `api_time` is collection-time provenance and is not an observed H200 replay latency.
- **Evidence:** source model labels are workload provenance, not target model identities.
- **Evidence:** the server is a shared system; conversation IDs do not establish GPU allocation or affinity.

## Inference

- **Inference:** theoretical hash-prefix reuse describes source workload shape only unless an artifact provides an actual cache metric at the relevant scope.

## Unknown

- **Unknown:** fixed-duration replay completeness, per-ID GPU utilization, fixed hardware assignment, direct Anthropic-versus-GLM model comparison, and independent-request confidence intervals are not established by these records.
