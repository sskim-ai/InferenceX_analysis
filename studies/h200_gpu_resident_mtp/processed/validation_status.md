# Validation status — decode occupancy sanity check

Run after regenerating the public H200 c8 worker/cluster reconstruction and
reports. All commands completed with exit code `0`.

| Command | Result | Exit code |
| --- | --- | ---: |
| `make test` | PASS — 92 tests passed | 0 |
| `make lint` | PASS — Ruff reported no checks failed | 0 |
| `make secret-scan` | PASS — no assignment-like sensitive patterns in tracked/unignored text files | 0 |

This validation covers only the public analysis repository. No local/internal
server artifacts or credentials were added to the study.
