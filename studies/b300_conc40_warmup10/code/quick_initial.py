import json
import re
from collections import Counter

log = (
    open("/tmp/b300_conc40_analysis/artifact/extracted/aiperf_artifacts/logs/aiperf.log")
    .read()
    .splitlines()
)
pat = re.compile(r"lane=(\d+)\s+sample_time=.*trace_id=([0-9a-f]+)$")
initial = []
for line in log:
    m = pat.search(line)
    if m:
        initial.append((int(m.group(1)), m.group(2)))
rows = []
for line in open(
    "/tmp/b300_conc40_analysis/artifact/extracted/aiperf_artifacts/profile_export.jsonl"
):
    m = json.loads(line)["metadata"]
    rows.append(m)
for lane, tid in initial:
    wr = [r for r in rows if r["source_trace_id"] == tid and r["benchmark_phase"] == "warmup"]
    pr = [r for r in rows if r["source_trace_id"] == tid and r["benchmark_phase"] == "profiling"]
    print(
        lane,
        tid,
        len(wr),
        len(pr),
        Counter(r["agent_depth"] for r in wr),
        min(
            (
                r["source_outer_idx"],
                r.get("source_inner_idx", -1) if r.get("source_inner_idx") is not None else -1,
            )
            for r in wr
        ),
        max(
            (
                r["source_outer_idx"],
                r.get("source_inner_idx", -1) if r.get("source_inner_idx") is not None else -1,
            )
            for r in wr
        ),
        min(
            (
                (
                    r["source_outer_idx"],
                    r.get("source_inner_idx", -1) if r.get("source_inner_idx") is not None else -1,
                )
                for r in pr
            ),
            default=None,
        ),
    )
print(
    "initial both",
    sum(
        any(r["source_trace_id"] == t and r["benchmark_phase"] == "profiling" for r in rows)
        for _, t in initial
    ),
)
