# H200 GPU-resident KV + MTP AgentX study

This study analyzes public InferenceX run `31235207041` (c8, c12, and c16) while preserving the existing run `29820102138` HiSparse analysis as a historical baseline.

The target is the GLM-5.2 FP8 replay on a shared H200 system. Claude labels in the source trace file identify the collected workload only; they are not H200 target-model labels.

## Layout

- `manifests/`: API/run/artifact/source-recipe/runtime-log provenance.
- `processed/`: compact, reviewable CSV summaries. Full request Parquet is local-only.
- `figures/`: figures created from the versioned summaries.
- `reports/`: evidence-first analysis, including Korean summary.
- `handoff/`: the package for the next ChatGPT analysis phase.

Raw public artifacts live under `data/raw/h200_gpu_resident_mtp/` and are intentionally ignored by Git. Do not add archives, logs, JSONL, Parquet, credentials, or Hugging Face caches to a commit.

## Reproduction

```sh
make mtp-analyze
make mtp-report
```

`mtp-analyze` streams `profile_export.jsonl` into local Parquet, joins public source IDs, recalculates aggregate metrics, and writes review CSVs. `mtp-report` renders figures, reports, and the GitHub-first handoff package. Acquisition uses authenticated `gh` and is recorded in `manifests/artifact_inventory.csv`; see `NEEDS_INPUT.md` if authentication is unavailable.

## Interpretation limits

- Compare HiSparse c8 with GPU-resident MTP c8 as an observed system-level difference only: GPU count, topology, KV dtype/residency, MTP, routing, and software can differ together.
- `usage_prompt_cache_read_tokens`, frontend cache metrics, theoretical source prefix reuse, and physical KV allocation have distinct scopes. Never equate them without direct evidence.
- Replayed requests and source IDs are not independent GPU-level samples and do not imply hardware affinity.
