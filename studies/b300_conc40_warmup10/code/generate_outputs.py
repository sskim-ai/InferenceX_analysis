import csv
import hashlib
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from datetime import UTC, datetime
from itertools import islice
from pathlib import Path

BASE = Path("/tmp/b300_conc40_analysis")
OUT = BASE / "output"
ART = BASE / "artifact" / "extracted"
JSONL = ART / "aiperf_artifacts" / "profile_export.jsonl"
LOG = ART / "aiperf_artifacts" / "logs" / "aiperf.log"
CORPUS_PREFIX = BASE / "corpus_prefix_500m.bin"
OUT.mkdir(parents=True, exist_ok=True)

ARTIFACT_NAME = "agentic_minimaxm3_tp4_conc40_kvdram-vllm-simple_spec-mtp_fp4_vllm_tp4-pp1-dcp1-pcp1-ep1-dpafalse_disagg-false_spec-mtp_conc40_b300-nv_14"
ARTIFACT_ID = 8878177167
ARTIFACT_SIZE = 24315650
ARTIFACT_DIGEST = "c4e6e61f255ebcc10c71f55c9ec036150295768bebb8ef837a03f89205ec04c0"


def iso_ns(value):
    if not isinstance(value, int):
        return ""
    dt = datetime.fromtimestamp(value / 1_000_000_000, tz=UTC)
    return dt.isoformat(timespec="microseconds").replace("+00:00", "Z")


def idx_display(outer, inner):
    if outer is None:
        return ""
    return str(outer) if inner is None else f"{outer}.{inner}"


def percentile_linear(values, q):
    xs = sorted(values)
    if not xs:
        return math.nan
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return float(xs[lo])
    return xs[lo] * (hi - pos) + xs[hi] * (pos - lo)


def truth(v):
    return "true" if v else "false"


def write_csv(path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",
            lineterminator="\n",
        )
        w.writeheader()
        w.writerows(rows)


# Artifact inventory and digest.
zip_path = BASE / "artifact" / "b300_conc40_artifact.zip"
zip_digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
inventory_lines = [
    "actions_run_id\t30849838984",
    f"artifact_id\t{ARTIFACT_ID}",
    f"artifact_name\t{ARTIFACT_NAME}",
    f"api_size_in_bytes\t{ARTIFACT_SIZE}",
    f"api_digest\tsha256:{ARTIFACT_DIGEST}",
    "api_expired\tfalse",
    f"downloaded_zip_size\t{zip_path.stat().st_size}",
    f"downloaded_zip_sha256\t{zip_digest}",
    f"digest_match\t{truth(zip_digest == ARTIFACT_DIGEST)}",
    "",
    "artifact_file\tsize_bytes",
]
artifact_dir = BASE / "artifact"
for p in sorted(
    x
    for x in artifact_dir.rglob("*")
    if x.is_file() and len(x.relative_to(artifact_dir).parts) <= 4
):
    inventory_lines.append(f"{p}\t{p.stat().st_size}")
(OUT / "01_artifact_inventory.txt").write_text("\n".join(inventory_lines) + "\n", encoding="utf-8")

# Read records without materializing prompt/response bodies (they are absent from this JSONL).
records = []
path_presence = Counter()
path_types = defaultdict(Counter)
phase_values = defaultdict(Counter)


def walk(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            yield path, v
            yield from walk(v, path)
    elif isinstance(obj, list):
        for v in obj[:1]:
            yield from walk(v, prefix + "[]")


with JSONL.open(encoding="utf-8") as f:
    for jsonl_ordinal, line in enumerate(f):
        obj = json.loads(line)
        m = obj["metadata"]
        metrics = obj.get("metrics", {})
        rec = dict(m)
        rec["jsonl_ordinal"] = jsonl_ordinal
        rec["output_sequence_length"] = metrics.get("output_sequence_length", {}).get("value")
        records.append(rec)
        for path, value in walk(obj):
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

by_exec = sorted(range(len(records)), key=lambda i: (records[i]["request_start_ns"], i))
by_complete = sorted(range(len(records)), key=lambda i: (records[i]["request_end_ns"], i))
for ordinal, i in enumerate(by_exec):
    records[i]["execution_ordinal"] = ordinal
for ordinal, i in enumerate(by_complete):
    records[i]["completion_ordinal"] = ordinal

# Historical sequential sampler's first 94 public source rows cover every observed source_trace_id.
source_rows = []
with CORPUS_PREFIX.open(encoding="utf-8") as f:
    for line in islice(f, 94):
        source_rows.append(json.loads(line))

source_by_root = {}
source_key_meta = {}
ambiguous_same_time_outer_groups = 0
for row_idx, row in enumerate(source_rows):
    items = []
    for outer_idx, req in enumerate(row["requests"]):
        if req.get("type") == "subagent":
            for inner_idx, child in enumerate(req.get("requests", [])):
                items.append(
                    {
                        "key": (outer_idx, inner_idx),
                        "t": float(child["t"]),
                        "raw_kind": "nested_subagent_request",
                    }
                )
        else:
            items.append(
                {
                    "key": (outer_idx, None),
                    "t": float(req["t"]),
                    "raw_kind": "outer_model_request",
                }
            )
    tie_counts = Counter((x["t"], x["key"][0]) for x in items)
    ambiguous_same_time_outer_groups += sum(1 for n in tie_counts.values() if n > 1)
    # Historical metric prepass uses (t, outer_idx, stream_idx, k). There are no
    # equal-(t, outer_idx) request groups in these 94 rows, so provenance inner
    # index is never used to resolve an ordering tie here.
    items.sort(key=lambda x: (x["t"], x["key"][0], -1 if x["key"][1] is None else x["key"][1]))
    for pos, item in enumerate(items):
        item["position"] = pos
        source_key_meta[(row["id"], item["key"][0], item["key"][1])] = item
    source_by_root[row["id"]] = {
        "dataset_row_idx": row_idx,
        "items": items,
        "count": len(items),
        "first_key": items[0]["key"] if items else None,
    }

observed_roots = {r["source_trace_id"] for r in records}
assert observed_roots <= set(source_by_root), sorted(observed_roots - set(source_by_root))
assert ambiguous_same_time_outer_groups == 0

for r in records:
    k = (r["source_trace_id"], r["source_outer_idx"], r.get("source_inner_idx"))
    sm = source_key_meta.get(k)
    if sm is None:
        raise AssertionError(f"artifact source key missing from public corpus prefix: {k}")
    r["source_position"] = sm["position"]
    r["source_timestamp_seconds"] = sm["t"]

# Parse exact initial lane population from the artifact's trajectory table.
lane_pat = re.compile(
    r"lane=(\d+)\s+sample_time=.*?root_next=\s*(\d+)/(\d+).*?live=(\d+)\s+ready=(\d+).*?trace_id=([0-9a-f]+)$"
)
initial = []
for line in LOG.read_text(encoding="utf-8").splitlines():
    m = lane_pat.search(line)
    if m:
        initial.append(
            {
                "lane_id": int(m.group(1)),
                "root_next": int(m.group(2)),
                "root_turns": int(m.group(3)),
                "live_at_t_star": int(m.group(4)),
                "ready_at_t_star": int(m.group(5)),
                "root_id": m.group(6),
            }
        )
assert len(initial) == 40
initial_by_root = {x["root_id"]: x for x in initial}
initial_roots = set(initial_by_root)

by_root = defaultdict(list)
for r in records:
    by_root[r["source_trace_id"]].append(r)


def summarize_root(root_id, lane_id=""):
    rr = by_root.get(root_id, [])
    warm = [r for r in rr if r["benchmark_phase"].lower() == "warmup"]
    prof = [r for r in rr if r["benchmark_phase"].lower() == "profiling"]
    wsrc = sorted(warm, key=lambda r: (r["source_position"], r["request_start_ns"]))
    psrc = sorted(prof, key=lambda r: (r["source_position"], r["request_start_ns"]))
    wexec = sorted(warm, key=lambda r: r["request_start_ns"])
    pexec = sorted(prof, key=lambda r: r["request_start_ns"])
    root_corrs = sorted({r["root_correlation_id"] for r in rr})
    session_id = root_corrs[0] if len(root_corrs) == 1 else "|".join(root_corrs)
    positions = sorted({r["source_position"] for r in warm})
    warm_contig = bool(positions) and positions == list(range(positions[0], positions[-1] + 1))
    first_prof_pos = psrc[0]["source_position"] if psrc else None
    immediately = (
        bool(positions)
        and first_prof_pos is not None
        and positions == list(range(first_prof_pos - len(positions), first_prof_pos))
    )
    signed_between = (
        "" if first_prof_pos is None or not positions else first_prof_pos - positions[-1] - 1
    )
    relation = ""
    if first_prof_pos is not None and positions:
        relation = (
            "after"
            if first_prof_pos > positions[-1]
            else ("adjacent" if first_prof_pos == positions[-1] + 1 else "source_order_overlap")
        )
        if first_prof_pos == positions[-1] + 1:
            relation = "adjacent"
    source = source_by_root[root_id]
    observed_keys = {(r["source_outer_idx"], r.get("source_inner_idx")) for r in rr}
    first_source_key = source["first_key"]
    return {
        "root_id": root_id,
        "lane_id": lane_id,
        "session_id": session_id,
        "source_total_requests": source["count"],
        "observed_requests": len(rr),
        "observed_distinct_source_requests": len(observed_keys),
        "warmup_requests": len(warm),
        "profile_requests": len(prof),
        "first_warmup_outer_idx": wsrc[0]["source_outer_idx"] if wsrc else "",
        "first_warmup_inner_idx": wsrc[0].get("source_inner_idx")
        if wsrc and wsrc[0].get("source_inner_idx") is not None
        else "",
        "last_warmup_outer_idx": wsrc[-1]["source_outer_idx"] if wsrc else "",
        "last_warmup_inner_idx": wsrc[-1].get("source_inner_idx")
        if wsrc and wsrc[-1].get("source_inner_idx") is not None
        else "",
        "first_profile_outer_idx": psrc[0]["source_outer_idx"] if psrc else "",
        "first_profile_inner_idx": psrc[0].get("source_inner_idx")
        if psrc and psrc[0].get("source_inner_idx") is not None
        else "",
        "first_profile_turn_index": psrc[0]["turn_index"] if psrc else "",
        "first_warmup_timestamp": iso_ns(wexec[0]["request_start_ns"]) if wexec else "",
        "last_warmup_timestamp": iso_ns(wexec[-1]["request_start_ns"]) if wexec else "",
        "first_profile_timestamp": iso_ns(pexec[0]["request_start_ns"]) if pexec else "",
        "warmup_count_eq_10": truth(len(warm) == 10),
        "first_warmup_source_idx": idx_display(
            wsrc[0]["source_outer_idx"], wsrc[0].get("source_inner_idx")
        )
        if wsrc
        else "",
        "last_warmup_source_idx": idx_display(
            wsrc[-1]["source_outer_idx"], wsrc[-1].get("source_inner_idx")
        )
        if wsrc
        else "",
        "first_profile_source_idx": idx_display(
            psrc[0]["source_outer_idx"], psrc[0].get("source_inner_idx")
        )
        if psrc
        else "",
        "warmup_are_contiguous": truth(warm_contig),
        "warmup_immediately_precede_first_profile": truth(immediately),
        "num_source_requests_between_last_warmup_and_first_profile": signed_between,
        "source_order_relation": relation,
        "warmup_distinct_turn_index": len({r["turn_index"] for r in warm}),
        "warmup_distinct_conversation_id": len({r["conversation_id"] for r in warm}),
        "warmup_distinct_subagent_conversation_id": len(
            {
                r["conversation_id"]
                for r in warm
                if r["conversation_id"] != root_id or r["agent_depth"] > 0
            }
        ),
        "warmup_distinct_source_outer_idx": len({r["source_outer_idx"] for r in warm}),
        "warmup_distinct_source_outer_inner_idx": len(
            {(r["source_outer_idx"], r.get("source_inner_idx")) for r in warm}
        ),
        "warmup_root_conversation_requests": sum(
            r["conversation_id"] == root_id and r["agent_depth"] == 0 for r in warm
        ),
        "warmup_subagent_requests": sum(
            r["conversation_id"] != root_id or r["agent_depth"] > 0 for r in warm
        ),
        "first_profile_is_first_source_request": truth(
            bool(psrc)
            and (psrc[0]["source_outer_idx"], psrc[0].get("source_inner_idx")) == first_source_key
        ),
        "full_source_coverage": truth(len(observed_keys) == source["count"]),
        "dataset_row_idx": source["dataset_row_idx"],
    }


summary_fields = [
    "root_id",
    "lane_id",
    "session_id",
    "source_total_requests",
    "observed_requests",
    "warmup_requests",
    "profile_requests",
    "first_warmup_source_idx",
    "last_warmup_source_idx",
    "first_profile_source_idx",
    "first_warmup_outer_idx",
    "first_warmup_inner_idx",
    "last_warmup_outer_idx",
    "last_warmup_inner_idx",
    "first_profile_outer_idx",
    "first_profile_inner_idx",
    "first_profile_turn_index",
    "first_warmup_timestamp",
    "last_warmup_timestamp",
    "first_profile_timestamp",
    "warmup_count_eq_10",
    "observed_distinct_source_requests",
    "warmup_are_contiguous",
    "warmup_immediately_precede_first_profile",
    "num_source_requests_between_last_warmup_and_first_profile",
    "source_order_relation",
    "warmup_distinct_turn_index",
    "warmup_distinct_conversation_id",
    "warmup_distinct_subagent_conversation_id",
    "warmup_distinct_source_outer_idx",
    "warmup_distinct_source_outer_inner_idx",
    "warmup_root_conversation_requests",
    "warmup_subagent_requests",
    "first_profile_is_first_source_request",
    "full_source_coverage",
    "dataset_row_idx",
    "root_next_at_t_star",
    "root_turns",
    "live_at_t_star",
    "ready_at_t_star",
]
initial_summaries = []
for item in sorted(initial, key=lambda x: x["lane_id"]):
    s = summarize_root(item["root_id"], item["lane_id"])
    s.update(
        {
            "root_next_at_t_star": item["root_next"],
            "root_turns": item["root_turns"],
            "live_at_t_star": item["live_at_t_star"],
            "ready_at_t_star": item["ready_at_t_star"],
        }
    )
    initial_summaries.append(s)
write_csv(OUT / "04_initial40_root_summary.csv", summary_fields, initial_summaries)

recycled_roots = sorted(
    observed_roots - initial_roots, key=lambda r: source_by_root[r]["dataset_row_idx"]
)
recycled_summaries = []
for root_id in recycled_roots:
    s = summarize_root(root_id)
    if s["warmup_requests"] > 0:
        cls = "recycled_during_warmup"
    elif s["profile_requests"] > 0:
        cls = "profiling_only_recycled_or_handoff_deferred"
    else:
        cls = "unclassified"
    s["recycle_class"] = cls
    recycled_summaries.append(s)
write_csv(
    OUT / "05_recycled_root_summary.csv", ["recycle_class"] + summary_fields, recycled_summaries
)

# Stage split is directly visible as the largest warmup request-start gap: first 44
# starts, then a 213.838s gap, matching the log's 44 primers and pressure-stage start.
warmup_records = [r for r in records if r["benchmark_phase"].lower() == "warmup"]
warmup_by_start = sorted(warmup_records, key=lambda r: r["request_start_ns"])
assert len(warmup_by_start) == 444
for rank, r in enumerate(warmup_by_start):
    r["warmup_stage"] = "mandatory_snapshot_primer" if rank < 44 else "additional_cache_pressure"
    r["warmup_start_rank"] = rank

detail_fields = [
    "root_id",
    "lane_id",
    "root_tree_session_id",
    "session_id",
    "conversation_id",
    "is_root_conversation",
    "is_subagent_conversation",
    "agent_depth",
    "source_kind",
    "benchmark_phase",
    "warmup_stage",
    "source_outer_idx",
    "source_inner_idx",
    "source_idx",
    "source_position",
    "source_timestamp_seconds",
    "turn_index",
    "jsonl_ordinal",
    "execution_ordinal",
    "completion_ordinal",
    "execution_timestamp",
    "completion_timestamp",
    "request_start_ns",
    "request_end_ns",
    "output_sequence_length",
    "worker_id",
    "session_num",
]
details = []
for r in sorted(warmup_records, key=lambda r: r["execution_ordinal"]):
    root_id = r["source_trace_id"]
    details.append(
        {
            "root_id": root_id,
            "lane_id": initial_by_root.get(root_id, {}).get("lane_id", ""),
            "root_tree_session_id": r["root_correlation_id"],
            "session_id": r["x_correlation_id"],
            "conversation_id": r["conversation_id"],
            "is_root_conversation": truth(
                r["conversation_id"] == root_id and r["agent_depth"] == 0
            ),
            "is_subagent_conversation": truth(
                r["conversation_id"] != root_id or r["agent_depth"] > 0
            ),
            "agent_depth": r["agent_depth"],
            "source_kind": r["source_kind"],
            "benchmark_phase": r["benchmark_phase"],
            "warmup_stage": r["warmup_stage"],
            "source_outer_idx": r["source_outer_idx"],
            "source_inner_idx": r.get("source_inner_idx", ""),
            "source_idx": idx_display(r["source_outer_idx"], r.get("source_inner_idx")),
            "source_position": r["source_position"],
            "source_timestamp_seconds": r["source_timestamp_seconds"],
            "turn_index": r["turn_index"],
            "jsonl_ordinal": r["jsonl_ordinal"],
            "execution_ordinal": r["execution_ordinal"],
            "completion_ordinal": r["completion_ordinal"],
            "execution_timestamp": iso_ns(r["request_start_ns"]),
            "completion_timestamp": iso_ns(r["request_end_ns"]),
            "request_start_ns": r["request_start_ns"],
            "request_end_ns": r["request_end_ns"],
            "output_sequence_length": r["output_sequence_length"],
            "worker_id": r["worker_id"],
            "session_num": r["session_num"],
        }
    )
write_csv(OUT / "06_warmup_request_detail.csv", detail_fields, details)

dist = Counter(s["warmup_requests"] for s in initial_summaries)
write_csv(
    OUT / "07_warmup_distribution.csv",
    ["warmup_requests", "number_of_initial_roots"],
    [{"warmup_requests": k, "number_of_initial_roots": dist[k]} for k in sorted(dist)],
)

phase_rows = []
for path, values in sorted(phase_values.items()):
    for original, count in sorted(values.items()):
        phase_rows.append(
            {
                "field_path": path,
                "original_value": original,
                "normalized_value": original.lower(),
                "count": count,
            }
        )
write_csv(
    OUT / "03_phase_counts.csv",
    ["field_path", "original_value", "normalized_value", "count"],
    phase_rows,
)

first = json.loads(next(JSONL.open(encoding="utf-8")))
schema_lines = [
    f"request_level_file: {JSONL}",
    f"total_records: {len(records)}",
    f"first_record_top_level_keys: {sorted(first)}",
    f"first_record_metadata_keys: {sorted(first.get('metadata', {}))}",
    f"first_record_metrics_keys: {sorted(first.get('metrics', {}))}",
    "",
    "recursive_phase_fields_and_values:",
]
for path, values in sorted(phase_values.items()):
    schema_lines.append(f"  {path}: {dict(values)}")
schema_lines.extend(["", "metadata_field_presence_and_types:"])
for path in sorted(p for p in path_presence if p.startswith("metadata.") and p.count(".") == 1):
    schema_lines.append(
        f"  {path}: present={path_presence[path]}/{len(records)} types={dict(path_types[path])}"
    )
schema_lines.extend(
    [
        "",
        "identity_rule:",
        "  root_id = metadata.source_trace_id (independent artifact field; never derived from conversation_id)",
        "  validation: conversation_id root prefix before :: matched source_trace_id for all records",
        "  root_tree_session_id = metadata.root_correlation_id",
        "  per-conversation session_id = metadata.x_correlation_id",
        "  metadata.session_num is credit_num (per-request counter), not a stable session identity",
        "  lane_id is absent from JSONL; initial lane_id is joined from the aiperf.log TrajectorySource lane table",
        "",
        "source_index_rule:",
        "  source_outer_idx and source_inner_idx are kept separately; missing inner index remains NULL/blank",
        "  source_position is derived from public corpus chronological order (t, outer_idx, stream/k tie breaker)",
        "  this is the historical loader global metric-prepass total order; execution itself is per-conversation DAG/timestamp replay, not one flattened queue",
        f"  equal-(t,outer_idx) ambiguity groups among observed 94 source roots: {ambiguous_same_time_outer_groups}",
        "",
        "timestamp_rule:",
        "  execution_timestamp = metadata.request_start_ns",
        "  completion_timestamp = metadata.request_end_ns",
        "  execution_ordinal and completion_ordinal are independently ranked; JSONL order is retained separately",
        f"  warmup rows with jsonl_ordinal == execution_ordinal: {sum(r['benchmark_phase'] == 'warmup' and r['jsonl_ordinal'] == r['execution_ordinal'] for r in records)}/444",
        f"  warmup rows with jsonl_ordinal == completion_ordinal: {sum(r['benchmark_phase'] == 'warmup' and r['jsonl_ordinal'] == r['completion_ordinal'] for r in records)}/444",
        f"  warmup rows with execution_ordinal == completion_ordinal: {sum(r['benchmark_phase'] == 'warmup' and r['execution_ordinal'] == r['completion_ordinal'] for r in records)}/444",
    ]
)
(OUT / "02_schema_summary.txt").write_text("\n".join(schema_lines) + "\n", encoding="utf-8")

warm = [r for r in records if r["benchmark_phase"] == "warmup"]
prof = [r for r in records if r["benchmark_phase"] == "profiling"]
warm_counts = [s["warmup_requests"] for s in initial_summaries]
primer = [r for r in warm if r["warmup_stage"] == "mandatory_snapshot_primer"]
pressure = [r for r in warm if r["warmup_stage"] == "additional_cache_pressure"]
warm_root_count = sum(
    r["conversation_id"] == r["source_trace_id"] and r["agent_depth"] == 0 for r in warm
)
warm_sub_count = len(warm) - warm_root_count
pressure_root_count = sum(
    r["conversation_id"] == r["source_trace_id"] and r["agent_depth"] == 0 for r in pressure
)
pressure_sub_count = len(pressure) - pressure_root_count
initial_with_profile = sum(s["profile_requests"] > 0 for s in initial_summaries)
profiling_only = [
    s for s in recycled_summaries if s["warmup_requests"] == 0 and s["profile_requests"] > 0
]
full_profile_only = [s for s in profiling_only if s["full_source_coverage"] == "true"]
full_profile_only_first = [
    s for s in full_profile_only if s["first_profile_is_first_source_request"] == "true"
]
contig = sum(s["warmup_are_contiguous"] == "true" for s in initial_summaries)
immediate = sum(s["warmup_immediately_precede_first_profile"] == "true" for s in initial_summaries)

source_evidence = f"""# AIPerf 818c3a5a source evidence

## Pins

- InferenceX commit: `8767d90c11860a10668f2d66179711a9c24fc8bd`
- `git ls-tree` gitlink: `818c3a5a2922c535af6271ff296ed374e292b8e4 utils/aiperf`
- Historical AIPerf checkout: `818c3a5a2922c535af6271ff296ed374e292b8e4`
- Historical public corpus alias: `semianalysis_cc_traces_weka_062126` -> `semianalysisai/cc-traces-weka-062126`, revision `23f152f6f0f9399a85901b89a6458def0ef16729`.

## Implementation path

1. Flag definition: `src/aiperf/config/flags/cli_config.py:2289-2303`. The description says the budget is per concurrency lane and additional to mandatory snapshot primers.
2. Phase config field: `src/aiperf/config/phases.py:365-377`.
3. Warmup request target: `src/aiperf/timing/phase/runner.py:153-170` computes `sum(baseline_counts) + requests_per_lane * lane_count`; this run logged 44 + 10*40 = 444.
4. t* snapshot construction: `src/aiperf/timing/trajectory_source.py:607-642` samples t* from the 0.25-0.75 time range, then builds the snapshot.
5. Mandatory primer selection: `src/aiperf/timing/trajectory_source.py:74-93` selects `next_turn_index - 1` for each live stream; `:422-449` counts one primer for every live stream having a pre-t* request.
6. Primer dispatch: `src/aiperf/timing/strategies/agentic_replay.py:625-768`; it prepares root and subagent primers and aligns them to t*.
7. Per-lane pressure quota: `src/aiperf/timing/strategies/agentic_replay.py:443-501`; baseline primers do not consume quota, while every later admitted `TurnToSend` increments the lane counter, regardless of root/subagent conversation.
8. Pressure replay: `src/aiperf/timing/strategies/agentic_replay.py:779-825` and `:831-929`; it resumes at the post-snapshot next request, sets max tokens to 1, removes idle delays, and continues the live DAG.
9. Profiling handoff: `src/aiperf/timing/strategies/agentic_replay.py:951-975`, `:1317-1436`, and `:1665-1803` persist the drained live streams and resume their next request in profiling.
10. Recycle: `src/aiperf/timing/strategies/agentic_replay.py:1606-1643` and `:1871-1886`; a recycled trace starts a fresh session at turn 0. The same method can be reached during accelerated warmup, so a lane may change root before its 10-request quota is full. Profiling recycle has no new warmup phase.
11. Output shortening: `_WARMUP_MAX_TOKENS = 1` at `src/aiperf/timing/strategies/agentic_replay.py:86`; all warmup turn builders apply it at `:1888-1902`.
12. Phase recording: `src/aiperf/records/record_processor_service.py:246-266` copies `credit_phase` to `benchmark_phase` and preserves trace/source indices and correlation IDs in export metadata.
13. Source provenance: `src/aiperf/dataset/loader/weka_trace.py:1612-1694` emits root/main turns with `(source_outer_idx, NULL)`; `:1932-1999` emits nested subagent turns with `(source_outer_idx, source_inner_idx)`; `:2003-2091` emits detected flat-agent chains while preserving their outer indices.
14. Historical global source ordering evidence: `src/aiperf/dataset/loader/weka_trace.py:1252-1316` orders shared trace records by `(t, outer_idx, stream_idx, k)`. No equal `(t, outer_idx)` group occurred in the 94 source roots observed here, so the derived source positions have no tie ambiguity.

## Answers A-I

- A: `10` means 10 additional admitted model-request credits per live trajectory lane, not 10 root turns, sessions, or source rows attached to one fixed root.
- B: First, each live stream gets its last request before t* as a mandatory primer. Then the configured 10-request pressure budget replays post-t* requests from the live DAG; if a tree finishes, a fresh root at source turn 0 can continue consuming that lane's quota.
- C: Yes. Subagent requests are ordinary admitted turns for the lane quota. Artifact: pressure stage root={pressure_root_count}, subagent={pressure_sub_count}.
- D: The phase starts with 40 initial lanes, but the quota belongs to lanes, not immutable initial roots. Warmup-time recycling produced additional root IDs.
- E: Profiling-time recycled traces do not receive this warmup; they start fresh at turn 0.
- F: Warmup output is forced to 1 token. Artifact independently shows output_sequence_length=1 for all {len(warm)} warmup records.
- G: Recorded idle gaps are not retained in the pressure stage: it runs with zero idle delay. Mandatory primers are t*-aligned and their lead is capped by the scenario's global system-idle guard (`agentic_replay.py:609-623`); the per-trace runtime idle cap is profiling-only (`timing/phase/runner.py:223-238`).
- H: Yes. Export metadata records phase directly; artifact has `benchmark_phase=warmup` for {len(warm)} rows.
- I: t* is sampled first, the live snapshot is built, pre-t* primers run, and only then the 10 post-snapshot pressure requests per lane run before profiling handoff.
"""
(OUT / "08_aiperf_818c3a5a_source_evidence.md").write_text(source_evidence, encoding="utf-8")

table_header = "| lane | root_id | source_total | observed | warmup | profile | first warmup | last warmup | first profile |\n|---:|---|---:|---:|---:|---:|---:|---:|---:|"
table_rows = []
for s in initial_summaries:
    table_rows.append(
        f"| {s['lane_id']} | `{s['root_id']}` | {s['source_total_requests']} | {s['observed_requests']} | {s['warmup_requests']} | {s['profile_requests']} | {s['first_warmup_source_idx'] or '—'} | {s['last_warmup_source_idx'] or '—'} | {s['first_profile_source_idx'] or '—'} |"
    )

final_md = f"""# B300 Conc40 `warmup-requests-per-lane=10` 실제 동작 분석

## 1. 결론

이 run의 `10`은 **각 initial root의 warmup row를 10개로 맞춘 값이 아니라, 40개 live trajectory lane 각각에 필수 snapshot primer 이후 추가로 허용한 model-request 10개**였다. Artifact에는 필수 primer 44개와 추가 pressure request 400개, 합계 444개의 warmup record가 있다. pressure replay 도중 tree가 끝나면 같은 lane에서 새 root가 turn 0부터 이어져 quota를 소비했으므로 initial root별 warmup record 수는 동일하지 않다.

## 2. Global summary

| 항목 | 값 | 근거 종류 |
|---|---:|---|
| configured_concurrency | 40 | artifact command |
| distinct_initial_roots | {len(initial_roots)} | artifact log 직접 확인 |
| initial_root_count_matches_concurrency | true | derived: 40 == 40 |
| distinct_recycled_roots | {len(recycled_roots)} | derived: total - initial |
| distinct_total_roots | {len(observed_roots)} | artifact 직접 확인 |
| total_warmup_requests | {len(warm)} | artifact 직접 확인 |
| total_profile_requests | {len(prof)} | artifact 직접 확인 |
| expected_warmup_if_exact_10_per_lane | 400 | derived |
| actual_total_warmup_requests | {len(warm)} | artifact 직접 확인 |
| difference_from_400 | {len(warm) - 400} | derived; mandatory primers |
| mandatory_snapshot_primers | {len(primer)} | artifact log + request-start gap |
| additional_cache_pressure_requests | {len(pressure)} | artifact log + derived |
| initial_roots_with_exactly_10_warmup | {sum(x == 10 for x in warm_counts)} | artifact derived |
| initial_roots_not_equal_10_warmup | {sum(x != 10 for x in warm_counts)} | artifact derived |
| warmup root-conversation requests | {warm_root_count} | artifact 직접 확인 |
| warmup subagent requests | {warm_sub_count} | artifact 직접 확인 |
| pressure-stage root requests | {pressure_root_count} | artifact derived stage split |
| pressure-stage subagent requests | {pressure_sub_count} | artifact derived stage split |

Initial-root warmup 분포: min={min(warm_counts)}, p25={percentile_linear(warm_counts, 0.25):g}, median={statistics.median(warm_counts):g}, p75={percentile_linear(warm_counts, 0.75):g}, max={max(warm_counts)}, mean={statistics.mean(warm_counts):.3f}. Frequency는 `07_warmup_distribution.csv`에 있다.

Initial root는 warmup phase에 보였다는 이유로 정하지 않았다. Artifact log가 01:16:15에 `built 40 trajectories from 393 traces`와 lane 00-39를 기록했고, 01:16:17에 44-primer warmup이 시작됐으며 profiling setup에서도 live lane population이 40이었다. 이 40개 log trace ID만 initial로 사용했다. Warmup 전체의 distinct root ID는 50개였으므로 그 집합을 initial로 간주하면 10개 warmup-time recycle root가 섞인다.

## 3. Initial 40개 표

{table_header}
{chr(10).join(table_rows)}

`source_total`은 artifact observed count가 아니라 공개 corpus revision의 원본 model request 수(outer normal/streaming request + nested subagent inner request)다. `first/last`는 JSONL row 순서가 아니라 historical loader의 global metric-prepass 순서 `(t, outer_idx, stream_idx, k)`에 맞춘 provenance index다. 실제 AgentX 실행은 하나의 flat queue가 아니라 conversation DAG와 timestamp로 진행된다.

## 4. `warmup=10`의 정확한 의미

- H1(각 initial root가 정확히 10 warmup rows): **거짓**. 정확히 10인 initial root는 {sum(x == 10 for x in warm_counts)}/40개뿐이고 범위는 {min(warm_counts)}-{max(warm_counts)}다. 다만 코드의 lane counter와 run log는 **각 lane의 추가 pressure quota가 정확히 10**에 도달했다고 확인한다.
- H2(그 10개가 profiling 직전 source request 10개): **거짓**. 필수 primer는 t* 직전의 각 live stream별 마지막 request이고, 추가 10개는 t* 이후 live DAG 실행이다. Initial root 기준 source-contiguous warmup은 {contig}/40개이고, profile이 실제 존재한 26개 중 전체 warmup set이 첫 profile source request를 즉시 선행한 경우는 {immediate}/26개뿐이다. 나머지는 DAG stream 간 source-order interleave 또는 gap이 있다.
- H3(10 root turns): **거짓**. 전체 warmup 444개 중 root conversation {warm_root_count}, subagent {warm_sub_count}; 추가 pressure 400개만 보아도 root {pressure_root_count}, subagent {pressure_sub_count}다.
- H4(t* 이전/이후): **두 단계**다. 44개 mandatory primer는 t* 이전 마지막 request이고, 그 뒤 400개 pressure request는 post-snapshot/t* 이후 경로를 zero-idle, one-token으로 진행한다.

## 5. Recycled trace 검증

Artifact에서 profiling-only root는 {len(profiling_only)}개이며 모두 `warmup_requests=0`, `profile_requests>0`이다. 그중 source 전체가 관측된 root는 {len(full_profile_only)}개이고, 이 중 {len(full_profile_only_first)}개는 historical source order의 첫 request부터 profiling이 시작했다. Initial 40 중 profiling까지 같은 root로 남은 것은 {initial_with_profile}개이며, 나머지 {40 - initial_with_profile}개는 warmup pressure 중 끝났다. Warmup 단계 자체에서도 새 root 10개가 등장했다. 상세 분류는 `05_recycled_root_summary.csv`에 있다.

## 6. AIPerf 818c3a5a 코드 근거

gitlink와 checkout 모두 `818c3a5a2922…`로 고정했다. 구현은 (1) t* snapshot 선택, (2) live stream별 pre-t* predecessor primer, (3) primer와 별개인 lane별 10회 admission counter, (4) zero-idle/1-token pressure replay, (5) live-state profiling handoff, (6) profiling recycle의 fresh turn-0 시작 순서다. 정확한 파일·라인과 A-I 답은 `08_aiperf_818c3a5a_source_evidence.md`에 정리했다.

## 7. 남은 불확실성

- JSONL에는 literal `lane_id`가 없다. Initial lane은 artifact log의 TrajectorySource 표에서 확정했지만 recycled root의 lane 번호는 request record만으로 복원하지 않았다.
- `session_num`은 historical source상 credit number이므로 session identity로 쓰지 않았다. Summary의 `session_id`는 tree-level `root_correlation_id`, detail의 `session_id`는 per-conversation `x_correlation_id`다.
- Profiling phase log에는 마지막 grace에서 cancelled request 10개가 있으나 성공 request JSONL에는 4,973개만 남는다. 본 보고서의 phase record count는 요청대로 JSONL record 기준이다.

## 요구 형식 최종 판정

이 B300 Conc40 run에서 `--warmup-requests-per-lane 10`은 **40개 live trajectory lane 각각에 mandatory t* snapshot primer와 별도로 추가 model request 10개를 허용하는 cache-pressure quota**였다. 각 initial lane의 시작 root에서 실제 관측된 warmup request 수는 **2-14개(평균 {statistics.mean(warm_counts):.3f})**였고, lane 전체로는 **각각 추가 10개**였으며 총 warmup은 **44 primer + 400 pressure = 444개**였다. 이 request들은 source trace의 **각 live stream별 t* 직전 predecessor primer와, 그 뒤 post-t* live-DAG request(필요하면 warmup 중 recycle된 새 root의 turn 0 포함)**에 해당했다. 따라서 “직전 10개 turn을 warmup한다”라는 설명은 **틀림**이다. 그 이유는 artifact가 444 warmup rows, 50 warmup root IDs, root/subagent 혼합을 보이고 historical AIPerf가 primer와 per-lane post-snapshot quota를 별도 구현하기 때문이다. Recycled trace에는 **profiling 중에는 미적용**되며, profiling-only {len(profiling_only)}개 root의 warmup count가 모두 0이고 historical recycle 코드가 fresh turn 0을 직접 profiling으로 dispatch하는 것으로 확인된다.
"""
(OUT / "09_final_analysis_ko.md").write_text(final_md, encoding="utf-8")

print(
    json.dumps(
        {
            "initial_roots": len(initial_roots),
            "recycled_roots": len(recycled_roots),
            "total_roots": len(observed_roots),
            "warmup": len(warm),
            "profiling": len(prof),
            "primer": len(primer),
            "pressure": len(pressure),
            "warmup_root": warm_root_count,
            "warmup_subagent": warm_sub_count,
            "pressure_root": pressure_root_count,
            "pressure_subagent": pressure_sub_count,
            "initial_with_profile": initial_with_profile,
            "profiling_only": len(profiling_only),
            "full_profile_only": len(full_profile_only),
            "full_profile_only_first": len(full_profile_only_first),
            "warm_counts": dict(sorted(dist.items())),
            "contiguous_initial": contig,
            "immediate_initial": immediate,
        },
        indent=2,
    )
)
