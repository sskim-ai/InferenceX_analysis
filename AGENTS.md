# H200 AgentX Conversation-ID Analysis

## Operating rules

- Keep raw GitHub artifacts, source JSONL, archives, credentials, and caches out of Git.
- Treat source-model labels as workload provenance only. The target under study is the GLM-5.2 FP8 replay on a shared H200 system.
- Label every report conclusion as **Evidence**, **Inference**, or **Unknown**. Do not fabricate completed acquisition or measurements.
- Stream JSONL inputs; do not load an entire raw trace or profile export into a Python list.
- Run `make test`, `make lint`, and `make secret-scan` before a commit.

## Data flow

1. `make acquire-run` inventories and downloads GitHub Actions artifacts.
2. `make acquire-traces` retrieves the public Hugging Face source trace file.
3. `make inspect build-source build-h200 join coverage analyze-ids analyze-concurrency validate figures report` derives results.

When data is unavailable, leave generated metric claims out of reports and record the exact recovery command in `NEEDS_INPUT.md`.
