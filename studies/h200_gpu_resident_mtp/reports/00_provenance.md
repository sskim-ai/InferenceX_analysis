# 00. Provenance

## Evidence

- Public InferenceX Actions run: `31235207041`.
- Canonical execution SHA: `48ec5aa103dbf8e671580cd191eeef7e7186c802`.
- Associated PR: `#2529`.
- Raw result, aggregate, and server-log artifact inventory is recorded in `../manifests/artifact_inventory.csv`.

## Inference

- The at-run SHA, not current `main` or a post-merge PR head, is the canonical configuration ref.

## Unknown

- Artifact evidence alone cannot establish per-request GPU affinity or independent request samples.
