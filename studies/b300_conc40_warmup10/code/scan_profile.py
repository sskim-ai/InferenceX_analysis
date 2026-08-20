import json
from collections import Counter, defaultdict
from pathlib import Path

P = Path("/tmp/b300_conc40_analysis/artifact/extracted/aiperf_artifacts/profile_export.jsonl")


def walk(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            yield path, v
            yield from walk(v, path)
    elif isinstance(obj, list):
        for v in obj[:1]:
            yield from walk(v, f"{prefix}[]")


rows = []
path_presence = Counter()
path_types = defaultdict(Counter)
phase_values = defaultdict(Counter)
with P.open() as f:
    for ordinal, line in enumerate(f):
        rec = json.loads(line)
        m = rec.get("metadata", {})
        row = {
            "ordinal": ordinal,
            "phase": m.get("benchmark_phase"),
            "source_trace_id": m.get("source_trace_id"),
            "root_correlation_id": m.get("root_correlation_id"),
            "conversation_id": m.get("conversation_id"),
            "session_num": m.get("session_num"),
            "worker_id": m.get("worker_id"),
            "source_kind": m.get("source_kind"),
            "source_outer_idx": m.get("source_outer_idx"),
            "source_inner_idx": m.get("source_inner_idx"),
            "turn_index": m.get("turn_index"),
            "agent_depth": m.get("agent_depth"),
            "credit_issued_ns": m.get("credit_issued_ns"),
            "request_start_ns": m.get("request_start_ns"),
            "request_end_ns": m.get("request_end_ns"),
        }
        rows.append(row)
        for path, value in walk(rec):
            path_presence[path] += 1
            path_types[path][type(value).__name__] += 1
            leaf = path.rsplit(".", 1)[-1].lower()
            if leaf in {
                "benchmark_phase",
                "phase",
                "profile_phase",
                "request_phase",
            } and not isinstance(value, (dict, list)):
                phase_values[path][str(value)] += 1

print("records", len(rows))
print("phase_paths")
for path, ctr in phase_values.items():
    print(path, dict(ctr))
print("metadata_fields")
for path in sorted(p for p in path_presence if p.startswith("metadata.") and p.count(".") == 1):
    print(path, path_presence[path], dict(path_types[path]))

for phase in sorted({r["phase"] for r in rows}, key=str):
    pr = [r for r in rows if r["phase"] == phase]
    print(
        "PHASE",
        phase,
        "records",
        len(pr),
        "trace_ids",
        len({r["source_trace_id"] for r in pr}),
        "root_corr",
        len({r["root_correlation_id"] for r in pr}),
        "conversation_ids",
        len({r["conversation_id"] for r in pr}),
        "sessions",
        len({r["session_num"] for r in pr}),
        "workers",
        len({r["worker_id"] for r in pr}),
    )

warm = [r for r in rows if str(r["phase"]).lower() == "warmup"]
prof = [r for r in rows if str(r["phase"]).lower() in {"profiling", "profile"}]
print("warmup root_depth", Counter("root" if r["agent_depth"] == 0 else "subagent" for r in warm))
print("warmup source_kind", Counter(r["source_kind"] for r in warm))
print(
    "warmup per source_trace_id freq", Counter(Counter(r["source_trace_id"] for r in warm).values())
)
print(
    "warmup per root_corr freq", Counter(Counter(r["root_correlation_id"] for r in warm).values())
)
print("warmup session_num freq", Counter(r["session_num"] for r in warm))
print("phase time bounds request_start_ns")
for name, rr in [("warmup", warm), ("profiling", prof)]:
    vals = [r["request_start_ns"] for r in rr if isinstance(r["request_start_ns"], int)]
    ends = [r["request_end_ns"] for r in rr if isinstance(r["request_end_ns"], int)]
    print(
        name,
        min(vals) if vals else None,
        max(vals) if vals else None,
        min(ends) if ends else None,
        max(ends) if ends else None,
    )

warm_traces = {r["source_trace_id"] for r in warm}
prof_traces = {r["source_trace_id"] for r in prof}
print(
    "warm_only",
    len(warm_traces - prof_traces),
    "both",
    len(warm_traces & prof_traces),
    "prof_only",
    len(prof_traces - warm_traces),
    "total",
    len(warm_traces | prof_traces),
)
print(
    "source_trace matches conversation root prefix",
    Counter(
        r["source_trace_id"]
        == (
            r["conversation_id"].split("::", 1)[0]
            if isinstance(r["conversation_id"], str)
            else None
        )
        for r in rows
    ),
)
print(
    "suffix examples",
    sorted(
        {
            r["conversation_id"]
            for r in warm
            if isinstance(r["conversation_id"], str) and "::" in r["conversation_id"]
        }
    )[:10],
)
