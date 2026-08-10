#!/usr/bin/env python3
"""Render study reports, figures, and the GitHub-first ChatGPT handoff."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import matplotlib
import pandas as pd

# The analysis is designed to run headlessly in CI/remote Codex sessions.
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
STUDY_ROOT_DEFAULT = REPOSITORY_ROOT / "studies/h200_gpu_resident_mtp"
ANALYSIS_START_COMMIT = "5411307f0be9e481a37a80d5ee477faf81c16c8c"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-root", type=Path, default=STUDY_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.study_root
    processed = root / "processed"
    reports = root / "reports"
    figures = root / "figures"
    handoff = root / "handoff"
    for path in (reports, figures, handoff):
        path.mkdir(parents=True, exist_ok=True)
    tables = {path.stem: _read_csv(path) for path in processed.glob("*.csv")}
    tables["artifact_inventory"] = _read_csv(root / "manifests" / "artifact_inventory.csv")
    recipe = _read_json(root / "manifests/source_recipe_evidence.json")
    runtime = _read_json(root / "manifests/runtime_log_evidence.json")
    _augment_runtime_configuration(processed, tables.get("runtime_configuration", pd.DataFrame()), runtime)
    tables["runtime_configuration"] = _read_csv(processed / "runtime_configuration.csv")
    _augment_mtp_metrics(processed, tables.get("mtp_metrics", pd.DataFrame()), runtime)
    tables["mtp_metrics"] = _read_csv(processed / "mtp_metrics.csv")
    _write_kv_runtime(processed, recipe, runtime)
    tables["kv_cache_runtime"] = _read_csv(processed / "kv_cache_runtime.csv")
    _build_figures(figures, tables)
    _build_reports(reports, tables, recipe, runtime)
    _build_handoff(handoff, tables, recipe, runtime)
    print(json.dumps({"status": "completed", "report_dir": str(reports)}, ensure_ascii=False))
    return 0


def _build_reports(
    reports: Path,
    tables: dict[str, pd.DataFrame],
    recipe: dict[str, Any],
    runtime: dict[str, Any],
) -> None:
    concurrency = tables.get("concurrency_summary", pd.DataFrame())
    cache = tables.get("cache_metrics", pd.DataFrame())
    mtp = tables.get("mtp_metrics", pd.DataFrame())
    resolution = tables.get("requested_id_resolution", pd.DataFrame())
    comparison = tables.get("h200_c8_hisparse_vs_gpu_resident", pd.DataFrame())
    validation = tables.get("validation_summary", pd.DataFrame())
    runtime_text = _runtime_evidence_text(runtime)
    _write(
        reports / "00_provenance.md",
        "# 00. Provenance\n\n"
        "## Evidence\n\n"
        f"- Public InferenceX Actions run: `{_recipe_value(recipe, ['actions_run', 'id']) or 'Unknown'}`.\n"
        f"- Canonical execution SHA: `{_recipe_value(recipe, ['actions_run', 'head_sha']) or 'Unknown'}`.\n"
        f"- Associated PR: `#{_recipe_value(recipe, ['pull_request', 'number']) or 'Unknown'}`.\n"
        "- Raw result, aggregate, and server-log artifact inventory is recorded in "
        "`../manifests/artifact_inventory.csv`.\n\n"
        "## Inference\n\n"
        "- The at-run SHA, not current `main` or a post-merge PR head, is the canonical configuration ref.\n\n"
        "## Unknown\n\n"
        "- Artifact evidence alone cannot establish per-request GPU affinity or independent request samples.\n",
    )
    _write(
        reports / "01_runtime_architecture.md",
        "# 01. Runtime architecture\n\n"
        "## Evidence\n\n"
        + _table(tables.get("runtime_configuration", pd.DataFrame()))
        + "\n\n"
        + runtime_text
        + "\n\n## Inference\n\n"
        "- The runtime logs resolve the prefill TP discrepancy in favor of TP=8 with attention-CP=8. The shared 32×H200 backend allocation is not a per-ID hardware assignment.\n\n"
        "## Unknown\n\n"
        "- The 40-GPU resource-snapshot count includes non-backend allocation; it is not the benchmark backend GPU total. Per-request GPU affinity is not exposed.\n",
    )
    _write(
        reports / "02_kv_cache_runtime.md",
        "# 02. KV-cache runtime\n\n"
        "## Evidence\n\n"
        + _table(tables.get("kv_cache_runtime", pd.DataFrame()))
        + "\n\n"
        + _table(cache)
        + "\n\n## Inference\n\n"
        "- Server logs directly show FP8 allocation records and disabled CPU/KV offload paths. Their rank-scoped GiB values must not be summed or multiplied into an unsupported cluster-wide physical capacity.\n\n"
        "## Unknown\n\n"
        "- A profile `usage_prompt_cache_read_tokens` counter is retained as observed evidence, but it is not promoted to a logical-prompt ratio when its scope is incompatible or unverified.\n"
        "- Do not treat source theoretical prefix reuse as actual server cache residency.\n",
    )
    _write(
        reports / "03_mtp_runtime.md",
        "# 03. MTP runtime\n\n"
        "## Evidence\n\n"
        "- Configured EAGLE MTP: three speculative steps, top-k 1, four draft tokens, and simulated acceptance length 2.99.\n\n"
        + _table(mtp)
        + "\n\n"
        + runtime_text
        + "\n\n## Inference\n\n"
        "- Weighted decode TPS is an observed replay metric under the configured MTP behavior; it is not a non-MTP single-model decode-TPS estimate.\n\n"
        "## Unknown\n\n"
        "- Request-profile rows may omit accepted/drafted token counters even when server logs contain aggregate/runtime acceptance messages.\n",
    )
    _write(
        reports / "04_concurrency_results.md",
        "# 04. c8 / c12 / c16 concurrency results\n\n"
        "## Evidence\n\n"
        + _table(_select(concurrency, [
            "concurrency", "profiled_request_count", "root_id_count", "input_sequence_length_total",
            "output_tokens_total", "wall_span_s", "ttft_mean_ms", "ttft_median_ms", "ttft_p90_ms",
            "weighted_decode_tps", "wall_output_tps", "itl_sample_count", "error_count_all_rows",
            "cancellation_count_all_rows",
        ]))
        + "\n\n### Source-root vs source-subagent origin\n\n"
        + _table(tables.get("root_subagent_summary", pd.DataFrame()))
        + "\n\n## Inference\n\n"
        "- Cross-concurrency changes are interpreted only after observed source-ID coverage and source-key matching; fixed-duration replay can change workload coverage.\n\n"
        "## Unknown\n\n"
        "- No individual conversation ID is assigned a fixed GPU, GPU count, or hardware affinity.\n",
    )
    _write(
        reports / "05_requested_ids_analysis.md",
        "# 05. Requested ID analysis\n\n"
        "## Evidence\n\n"
        + _table(resolution)
        + "\n\n"
        + _requested_tables_text(tables)
        + "\n\n### ID03 follow-up\n\n"
        "- The resolved 07dd405 ID is analysed at request/source-key level in "
        "[11_id03_deep_dive.md](11_id03_deep_dive.md). Its c8/c12/c16 coverage and "
        "strict matching are deliberately kept separate from the all-ID aggregate tables above.\n"
        "- **Evidence:** ID01 c8 has one ITL-valid request in the current public table; its "
        "weighted TPS is marked descriptive only and is suppressed from comparative TPS plots.\n"
        + "\n\n## Inference\n\n"
        "- Prefixes are only used as canonical IDs after strict `startswith()` resolution is unique.\n\n"
        "## Unknown\n\n"
        "- A not-observed ID is not evidence that it was never eligible for replay; run duration, warmup, recycling, and routing affect coverage.\n",
    )
    _write(
        reports / "06_cross_concurrency.md",
        "# 06. Cross-concurrency matching\n\n"
        "## Evidence\n\n"
        + _table(tables.get("cross_concurrency_match_summary", pd.DataFrame()))
        + "\n\n### ID03 strict source-key subsets\n\n"
        + _table(tables.get("id03_cross_concurrency_summary", pd.DataFrame()))
        + "\n\n- Per-pair request rows are versioned in "
        "../processed/id03_exact_match_c8_c12.csv, "
        "../processed/id03_exact_match_c8_c16.csv, and "
        "../processed/id03_exact_match_c12_c16.csv; three-way overlap is in "
        "../processed/id03_exact_match_all.csv.\n"
        + "\n\n## Inference\n\n"
        "- Pair rows collapse repeated records to a source-key/concurrency median before ratios; raw request rows are not treated as independent replicates.\n\n"
        "## Unknown\n\n"
        "- Identical source keys do not ensure identical output lengths under a speculative-decoding replay. Strict decode subsets require the observed output length to agree.\n",
    )
    _write(
        reports / "07_hisparse_c8_vs_gpu_resident_c8.md",
        "# 07. HiSparse c8 vs GPU-resident MTP c8\n\n"
        "## Evidence\n\n"
        + _table(comparison)
        + "\n\n"
        + _table(tables.get("exact_match_c8_summary", pd.DataFrame()))
        + "\n\n### Approximate decode-worker-normalized context\n\n"
        + _table(tables.get("h200_worker_normalized_comparisons", pd.DataFrame()))
        + "\n\n- **Evidence:** the comparison CSV separates hisparse_request_count, "
        "gpu_resident_request_count, exact_matched_source_key_count, strict_ttft_count, "
        "and strict_decode_count. A single generic sample count is not used for both unpaired "
        "and exact-match evidence.\n"
        + "\n\n## Inference\n\n"
        "- Every ratio is an **observed system-level difference**, not a causal HiSparse effect: GPU count, P/D topology, KV dtype/residency, MTP, routing, and software can all differ.\n\n"
        "- The c4 HiSparse ↔ c8 GPU-resident MTP and c8 HiSparse ↔ c16 GPU-resident MTP rows are "
        "only approximate decode-worker-normalized contexts (one versus two decode workers). They do "
        "not establish equal per-worker load or a causal architecture effect.\n\n"
        "## Unknown\n\n"
        "- The available evidence cannot isolate the contribution of any one of those changes.\n",
    )
    _write(
        reports / "08_local_2gpu_contextual_reference.md",
        "# 08. User-reported 2-GPU contextual reference\n\n"
        "## Evidence\n\n"
        + _table(tables.get("local_2gpu_user_reported_reference", pd.DataFrame()))
        + "\n\n### ID03 cpy1–cpy8 follow-up\n\n"
        "- The public reference and local extraction contract are prepared in "
        "[11_id03_deep_dive.md](11_id03_deep_dive.md), "
        "[12_id03_local_cpy_comparison_plan.md](12_id03_local_cpy_comparison_plan.md), and "
        "[../handoff/id03_local_join_contract.md](../handoff/id03_local_join_contract.md).\n"
        "- **Unknown:** a local label such as 07dd405_cpy8 is not yet evidence that it means "
        "global concurrency 8, eight independent root sessions, or eight copies of the same trace.\n"
        + "\n\n## Inference\n\n"
        "- These two rows are a provenance-labelled user-reported aggregate reference, useful for later review but not request-level evidence.\n\n"
        "## Unknown\n\n"
        "- No direct apples-to-apples conclusion is possible against 32×H200, 2P2D, MTP-enabled public replay without local raw logs and configuration evidence.\n",
    )
    _write(
        reports / "09_validation.md",
        "# 09. Aggregate validation\n\n"
        "## Evidence\n\n"
        + _table(validation)
        + "\n\n"
        + _table(_select(tables.get("aggregate_validation", pd.DataFrame()), [
            "concurrency", "metric", "raw_value", "published_value", "validation_status", "validation_note",
        ]))
        + "\n\n## Inference\n\n"
        "- A pass is limited to the documented filtering, units, percentile convention, and available aggregate metric path.\n\n"
        "## Unknown\n\n"
        "- A not-comparable aggregate field is not a validation pass.\n",
    )
    _write(
        reports / "10_limitations.md",
        "# 10. Limitations\n\n"
        "## Evidence\n\n"
        "- The workload’s source Claude labels are preserved only as source-workload provenance. The target replay model is GLM-5.2 FP8.\n"
        "- Source `api_time` is not an H200 latency measurement.\n"
        "- Raw profile records can repeat a source key; a shared H200 system serves all requests.\n\n"
        "## Inference\n\n"
        "- c8/c12/c16 coverage differences can bias unpaired averages.\n\n"
        "## Unknown\n\n"
        "- Per-ID GPU utilisation, exact GPU allocation, and physical cache residency cannot be inferred from a conversation ID.\n"
        "- MTP acceptance and KV allocation require actual runtime counters/log scope; absent metrics remain Unknown.\n",
    )
    _write_id03_deep_dive(reports / "11_id03_deep_dive.md", tables)
    _write_id03_local_cpy_plan(reports / "12_id03_local_cpy_comparison_plan.md", tables)
    _write_korean_summary(reports / "results_summary_ko.md", tables, recipe, runtime)


def _id03_resolution_table(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return the one requested-ID resolution row without assuming a hard-coded source universe."""

    frame = tables.get("requested_id_resolution", pd.DataFrame())
    if frame.empty or "id_label" not in frame:
        return pd.DataFrame()
    return frame.loc[frame["id_label"].astype("string") == "ID03"].copy()


def _id03_canonical_id(tables: dict[str, pd.DataFrame]) -> str:
    frame = _id03_resolution_table(tables)
    if frame.empty or "resolved_full_source_trace_id" not in frame:
        return "Unknown"
    value = frame.iloc[0]["resolved_full_source_trace_id"]
    return str(value) if pd.notna(value) else "Unknown"


def _id03_scheduling_evidence_text(tables: dict[str, pd.DataFrame]) -> str:
    """Render raw-log scheduling evidence only when the extractor produced it."""

    evidence = tables.get("id03_replay_scheduling_evidence", pd.DataFrame())
    if evidence.empty:
        return (
            "- **Unknown:** the generated raw-log scheduling evidence table was unavailable when "
            "this report was rendered. Do not use this report to attribute coverage to a specific "
            "scheduler decision.\n"
        )
    return (
        _table(evidence)
        + "\n\n- **Evidence:** these rows preserve the relevant AIPerf log evidence for the "
        "fixed profiling duration, randomized trajectory starts, warmup handoff, and root recycling. "
        "They describe the replay process; they do not assign a causal latency effect to one mechanism.\n"
    )


def _id03_source_turn_detail_text(coverage: pd.DataFrame) -> str:
    """Render exact source-request positions without inventing schedule causality."""

    if coverage.empty or "concurrency" not in coverage:
        return ""
    lines = ["### Exact observed source-position coverage\n"]
    for concurrency in (12, 16):
        row = coverage.loc[pd.to_numeric(coverage["concurrency"], errors="coerce") == concurrency]
        if row.empty:
            continue
        item = row.iloc[0]
        warmup = _compact_index_ranges(item.get("warmup_source_request_indices"))
        profile = _compact_index_ranges(item.get("profiling_source_request_indices"))
        lines.append(
            f"- **Evidence (c{concurrency}):** warmup source-request indices: "
            f"`{warmup}`; successful profiling source-request indices: "
            f"`{profile}`. The full exact index list is retained in "
            "`../processed/id03_source_coverage_by_concurrency.csv`.\n"
        )
    return "\n".join(lines) + "\n" if len(lines) > 1 else ""


def _compact_index_ranges(value: Any) -> str:
    """Render semicolon-delimited source indices as compact inclusive ranges."""

    if value is None or pd.isna(value):
        return "none"
    try:
        numbers = sorted({int(item) for item in str(value).split(";") if item})
    except ValueError:
        return str(value)
    if not numbers:
        return "none"
    ranges: list[str] = []
    start = previous = numbers[0]
    for number in numbers[1:]:
        if number == previous + 1:
            previous = number
            continue
        ranges.append(str(start) if start == previous else f"{start}–{previous}")
        start = previous = number
    ranges.append(str(start) if start == previous else f"{start}–{previous}")
    return "; ".join(ranges)


def _write_id03_deep_dive(path: Path, tables: dict[str, pd.DataFrame]) -> None:
    """Write the reviewable public-reference report for the resolved ID03 trace."""

    canonical_id = _id03_canonical_id(tables)
    resolution = _id03_resolution_table(tables)
    coverage = tables.get("id03_source_coverage_by_concurrency", pd.DataFrame())
    scaling = tables.get("id03_h200_scaling_curve", pd.DataFrame())
    matching = tables.get("id03_cross_concurrency_summary", pd.DataFrame())
    distribution = tables.get("id03_c8_latency_distribution", pd.DataFrame())
    source_buckets = tables.get("id03_c8_source_input_buckets", pd.DataFrame())
    context_status = tables.get("id03_context_202752_subset_status", pd.DataFrame())
    text = "# 11. ID03 public H200 deep dive\n\n"
    text += "## Canonical ID resolution\n\n"
    text += "### Evidence\n\n"
    text += (
        f"- Primary trace: {canonical_id}. The requested prefix 07dd405 is accepted only because "
        "the versioned resolution table reports a unique full source-trace ID.\n\n"
    )
    text += _table(resolution) + "\n\n"
    text += "## c8 / c12 / c16 source-turn coverage\n\n"
    text += "### Evidence\n\n"
    text += _table(
        _select(
            coverage,
            [
                "concurrency",
                "all_request_count",
                "warmup_count",
                "profiling_phase_count",
                "successful_profiling_count",
                "distinct_exact_source_key_count_profile",
                "source_coverage_ratio_profile",
                "source_request_index_min",
                "source_request_index_max",
                "source_input_tokens_min",
                "source_input_tokens_max",
                "wall_span_s",
                "error_count",
                "cancellation_count",
                "duplicate_exact_source_key_count_profile",
            ],
        )
    )
    text += "\n\n### Replay scheduling evidence\n\n"
    text += _id03_scheduling_evidence_text(tables)
    text += _id03_source_turn_detail_text(coverage)
    text += "\n## Inference\n\n"
    text += (
        "- c8 is the primary public comparison reference because it covers all 119 distinct ID03 "
        "source keys as successful profiling requests and has 119 ITL-valid requests. c12 covers "
        "112/119 keys after seven ID03 warmup rows; c16 covers 13/119 profiling keys and is a "
        "late-tail subset rather than a whole-trace estimate.\n"
    )
    text += (
        "- The fixed 3,600-second profiling window, randomized trajectory start positions, warmup "
        "handoff, recycling, and mixed-workload scheduling are evidence-backed contributors to coverage "
        "differences. They do not identify one sufficient cause for every missing ID03 source key.\n"
    )
    text += "\n## Unknown\n\n"
    text += (
        "- The public data does not expose the counterfactual schedule that would prove exactly why a "
        "specific key was absent in a run, nor does it make the c16 tail a random or representative "
        "sample of the full ID03 trace.\n\n"
    )
    text += "## Exact c8 ↔ c12 ↔ c16 request matching\n\n"
    text += "### Evidence\n\n"
    text += _table(matching) + "\n\n"
    text += (
        "- Matching key: source_trace_id + source_outer_idx + source_inner_idx. Source conversation "
        "path and turn index are retained as validation fields. Pair rows first collapse repeated "
        "source-key/concurrency records before ratios.\n"
        "- Full reviewable pair data: ../processed/id03_exact_match_c8_c12.csv, "
        "../processed/id03_exact_match_c8_c16.csv, ../processed/id03_exact_match_c12_c16.csv, and "
        "../processed/id03_exact_match_all.csv.\n\n"
    )
    text += "### Inference\n\n"
    text += (
        "- On the large c8↔c12 overlap, median TTFT rises while weighted ITL changes modestly. "
        "The c8↔c16 overlap is only 13 exact keys, so it supports a tail-subset comparison rather "
        "than a full-trace concurrency curve.\n\n"
    )
    text += "### Unknown\n\n"
    text += (
        "- Matching a source key controls workload identity, not all system state, queue position, "
        "MTP behavior, route, or cache residency. It cannot isolate a pure concurrency effect.\n\n"
    )
    text += "## ID03 H200 scaling curve\n\n"
    text += "### Evidence\n\n"
    text += _table(scaling) + "\n\n"
    text += (
        "- TTFT inflation is relative to ID03 c8. TPS retention is based on output-transition-token-"
        "weighted ITL; wall output TPS is a parallel-system rate and is intentionally distinct.\n\n"
    )
    text += "### Inference\n\n"
    text += (
        "- c12/c16 preserve much of the observed active decode TPS for the covered keys, whereas "
        "TTFT and wall-output outcomes are more coverage- and scheduling-sensitive. This is not an "
        "apples-to-apples local scaling conclusion.\n\n"
    )
    text += "### Unknown\n\n"
    text += (
        "- No per-ID GPU allocation, GPU utilization, or fixed worker affinity follows from this "
        "curve; the public run is a shared 32×H200 system.\n\n"
    )
    text += "## c8 latency and workload-shape reference\n\n"
    text += "### Evidence\n\n"
    text += _table(distribution) + "\n\n"
    text += "### Source-workload input proxy buckets\n\n"
    text += _table(source_buckets) + "\n\n"
    text += (
        "- The plotted c8 ordinal curves are in ../figures/id03_source_input_vs_ordinal.png, "
        "../figures/id03_ttft_vs_ordinal.png, ../figures/id03_itl_vs_ordinal.png, and "
        "../figures/id03_output_tokens_vs_ordinal.png.\n"
        "- Source input tokens are a workload proxy only. They are not target GLM logical context "
        "tokens or a measured GPU prefill-throughput denominator.\n\n"
    )
    text += "## 202,752-context compatible subset\n\n"
    text += "### Evidence\n\n"
    text += _table(context_status) + "\n\n"
    text += (
        "- The companion CSV ../processed/id03_context_202752_compatible_requests.csv is intentionally "
        "header-only when the exact target-tokenization fit condition cannot be evaluated.\n\n"
    )
    text += "### Inference\n\n"
    text += (
        "- A future local comparison must use exact local target logical prompt tokens plus requested "
        "output limit, or the documented loader/server fit rule, before declaring a public request "
        "compatible with max_model_len 202752.\n\n"
    )
    text += "### Unknown\n\n"
    text += (
        "- No request-level target-model logical prompt metric, requested output limit, or joinable "
        "frontend metric exists in the public profile package. input_sequence_length and source_input_tokens "
        "must not be substituted for that missing condition.\n\n"
    )
    text += "## Why ID03 is the primary local-comparison candidate\n\n"
    text += "### Evidence\n\n"
    text += (
        "- ID03 has whole-trace c8 profiling coverage, 119 ITL-valid c8 observations, per-source-key "
        "c8/c12/c16 exact-match exports, and c8 latency/output-shape distributions.\n"
        "- The canonical public request reference is ../processed/id03_h200_reference_requests.csv.\n\n"
    )
    text += "### Inference\n\n"
    text += (
        "- This makes ID03 the strongest available public H200 reference for a later local cpy comparison, "
        "provided the local extractor demonstrates matching source keys and workload semantics.\n\n"
    )
    text += "### Unknown\n\n"
    text += (
        "- It does not make public c8 equivalent to local cpy8: public c8 is mixed-root global concurrency "
        "on 2P2D 32×H200 with MTP, whereas the meaning of local cpy labels still requires raw local "
        "configuration and request evidence.\n"
    )
    _write(path, text)


def _write_id03_local_cpy_plan(path: Path, tables: dict[str, pd.DataFrame]) -> None:
    """Write an evidence contract, not a fabricated local-server analysis."""

    canonical_id = _id03_canonical_id(tables)
    scaling = tables.get("id03_h200_scaling_curve", pd.DataFrame())
    text = "# 12. ID03 local cpy comparison plan\n\n"
    text += "## Public reference selected for the later comparison\n\n"
    text += "### Evidence\n\n"
    text += f"- Canonical ID03 source trace: {canonical_id}.\n\n"
    text += _table(scaling) + "\n\n"
    text += (
        "- Public c8 is the primary H200 reference because it has full ID03 source-key profiling coverage. "
        "Its request-level source-key table is ../processed/id03_h200_reference_requests.csv.\n\n"
    )
    text += "### Inference\n\n"
    text += (
        "- Later analysis should compare both absolute matched-request values and scaling direction, "
        "not promote public c8 and local cpy8 to equivalent workloads.\n\n"
    )
    text += "### Unknown\n\n"
    text += (
        "- No local raw logs or local cpy measurements are present in this public study. No local metric "
        "is calculated here.\n\n"
    )
    text += "## Meaning of local cpy1–cpy8 to verify first\n\n"
    text += "### Required local evidence for every cpy label\n\n"
    text += (
        "- cpy label; configured concurrency; observed maximum simultaneous requests; independent root-session "
        "count; distinct conversation-ID count; source-trace-ID count; request and successful-request counts "
        "per copy; start timestamps; and end timestamps.\n"
        "- Show whether each copy executes the canonical ID03 sequence independently and whether AIPerf "
        "concurrency is actually N for cpyN.\n\n"
    )
    text += "### Unknown\n\n"
    text += (
        "- Whether cpyN is a same-trace replication label, global concurrency N, or N independent "
        "sessions remains unknown until the preceding fields are extracted from local config/logs.\n\n"
    )
    text += "## Exact join contract\n\n"
    text += (
        "- Read ../handoff/id03_local_join_contract.md before extracting local data. The canonical exact key is "
        "source_trace_id + source_outer_idx + source_inner_idx. Source conversation path and turn index validate "
        "the candidate match; a missing or conflicting validation field must be reported rather than silently "
        "accepted.\n"
        "- For a strict TTFT subset: exact key, successful request on both systems, and both TTFT values. "
        "For a strict decode subset: strict TTFT conditions plus output_tokens > 1, ITL present, and equal observed "
        "output length.\n\n"
    )
    text += "## Context-limit contract\n\n"
    text += "### Evidence\n\n"
    text += (
        "- Public H200 uses a 1,048,576-token context; the stated local maximum is 202,752. The public "
        "202,752-compatible subset status is unavailable_exact_target_tokenization.\n\n"
    )
    text += "### Required local/public fit rule\n\n"
    text += (
        "- Use target logical prompt tokens + requested output limit <= 202752, or a documented exact loader/server "
        "fit condition. Do not replace target logical prompt tokens with public input_sequence_length or "
        "source_input_tokens.\n\n"
    )
    text += "## Metrics to calculate after local extraction\n\n"
    text += (
        "| Area | Required comparable metrics |\n"
        "| --- | --- |\n"
        "| Coverage | successful/transmitted/failed requests; first/last successful exact key; first failed key; context-overflow position |\n"
        "| Tokens | total/mean/median/max input with semantics; cache read/load/store with scope; output tokens |\n"
        "| TTFT | mean, median, P90, P95, max (ms) |\n"
        "| Decode | ITL sample count; weighted ITL; weighted decode TPS; median decode TPS |\n"
        "| End-to-end | E2E mean/median/P90; wall span; wall output TPS |\n"
        "| System | GPU utilization; HBM used/free; KV block/token use; scheduler running/waiting requests, if available |\n\n"
    )
    text += "## Scaling definitions\n\n"
    text += (
        "- Local TPS retention at cpyN = weighted_decode_tps_cpyN / weighted_decode_tps_cpy1.\n"
        "- Local median TTFT inflation at cpyN = median_ttft_cpyN / median_ttft_cpy1.\n"
        "- Local wall-throughput scaling at cpyN = wall_output_tps_cpyN / wall_output_tps_cpy1.\n"
        "- Public ID03 reference direction uses c8 as baseline: c12/c8 and c16/c8 in "
        "../processed/id03_h200_scaling_curve.csv.\n\n"
    )
    text += "## Interpretation boundaries\n\n"
    text += "### Evidence\n\n"
    text += (
        "- Public c8/c12/c16 is a mixed-root 2P2D, 32×H200, MTP-enabled replay. The public table retains "
        "coverage differences and MTP behavior.\n\n"
    )
    text += "### Inference\n\n"
    text += (
        "- Scaling behavior (where TTFT inflates, whether ITL/TPS retains, and wall-throughput changes) may be "
        "more informative than an unqualified absolute hardware ratio.\n\n"
    )
    text += "### Unknown\n\n"
    text += (
        "- Without local topology, MTP, KV, context-fit, and request-level evidence, no apples-to-apples "
        "hardware-efficiency or causal cache conclusion is allowed.\n"
    )
    _write(path, text)


def _id03_handoff_text(tables: dict[str, pd.DataFrame]) -> str:
    """Keep the primary local-comparison evidence near the top-level handoff."""

    canonical_id = _id03_canonical_id(tables)
    scaling = tables.get("id03_h200_scaling_curve", pd.DataFrame())
    matching = tables.get("id03_cross_concurrency_summary", pd.DataFrame())
    coverage = tables.get("id03_source_coverage_by_concurrency", pd.DataFrame())
    context_status = tables.get("id03_context_202752_subset_status", pd.DataFrame())
    return (
        "\n\n## ID03 Deep Dive\n\n"
        "### Evidence\n\n"
        f"- Canonical ID: {canonical_id}.\n"
        "### Public c8/c12/c16 coverage\n\n"
        + _table(
            _select(
                coverage,
                [
                    "concurrency",
                    "profiling_phase_count",
                    "successful_profiling_count",
                    "distinct_exact_source_key_count_profile",
                    "source_coverage_ratio_profile",
                    "warmup_count",
                ],
            )
        )
        + "\n\n### TTFT / TPS scaling\n\n"
        + _table(
            _select(
                scaling,
                [
                    "concurrency",
                    "ttft_median_ms",
                    "ttft_p90_ms",
                    "weighted_decode_tps",
                    "itl_sample_count",
                    "ttft_inflation_vs_c8",
                    "tps_retention_vs_c8",
                    "wall_throughput_ratio_vs_c8",
                ],
            )
        )
        + "\n\n### Exact overlap\n\n"
        + _table(
            _select(
                matching,
                [
                    "pair",
                    "matched_source_key_count",
                    "same_output_length_count",
                    "strict_ttft_count",
                    "strict_decode_count",
                    "median_ttft_ratio_right_over_left",
                    "weighted_itl_ratio_right_over_left",
                    "coverage_overlap_ratio_jaccard",
                ],
            )
        )
        + "\n\n### Context/token metric limitation\n\n"
        + _table(context_status)
        + "\n\n- Raw AIPerf log scheduling evidence is in "
        "processed/id03_replay_scheduling_evidence.csv; it documents time-limited profiling, "
        "randomized starts, warmup handoff, and recycling without claiming a single causal mechanism.\n"
        "### Inference\n\n"
        "- c8 is the primary public reference because it has full observed ID03 source-key profiling "
        "coverage and enough ITL-valid requests for a reviewable decode-TPS distribution; c12/c16 retain "
        "narrower matched subsets.\n\n"
        "### Unknown\n\n"
        "- The public package has no request-level target logical prompt token metric "
        "or requested output limit, so a 202,752-compatible exact subset is unavailable.\n"
        "- Public c8 is mixed-root global concurrency on 2P2D 32×H200 with MTP. "
        "It is not established as equivalent to any local cpyN label.\n\n"
        "### Files for ID03 comparison\n\n"
        "1. studies/h200_gpu_resident_mtp/reports/11_id03_deep_dive.md\n"
        "2. studies/h200_gpu_resident_mtp/reports/12_id03_local_cpy_comparison_plan.md\n"
        "3. studies/h200_gpu_resident_mtp/processed/id03_h200_reference_requests.csv\n"
        "4. studies/h200_gpu_resident_mtp/processed/id03_source_coverage_by_concurrency.csv\n"
        "5. studies/h200_gpu_resident_mtp/processed/id03_cross_concurrency_summary.csv\n"
        "6. studies/h200_gpu_resident_mtp/processed/id03_exact_match_c8_c12.csv\n"
        "7. studies/h200_gpu_resident_mtp/processed/id03_exact_match_c8_c16.csv\n"
        "8. studies/h200_gpu_resident_mtp/processed/id03_exact_match_c12_c16.csv\n"
        "9. studies/h200_gpu_resident_mtp/handoff/id03_local_join_contract.md\n"
    )


def _write_id03_local_join_contract(handoff: Path, canonical_id: str) -> None:
    """Write a portable contract for a private extractor; it contains no local measurements."""

    text = "# ID03 local cpy join contract\n\n"
    text += "## Scope\n\n"
    text += (
        f"- Public comparison trace: {canonical_id}.\n"
        "- This is an extraction and matching contract for a later private analysis. It is not a "
        "claim that any local cpy label equals public H200 concurrency.\n\n"
    )
    text += "## Required local fields\n\n"
    text += (
        "| Group | Fields |\n"
        "| --- | --- |\n"
        "| Copy identity | local_run_label; local_copy_label; local_copy_index; configured_concurrency; observed_max_simultaneous_requests; independent_root_session_count; conversation_id; session_num |\n"
        "| Source identity | source_trace_id; source_outer_idx; source_inner_idx; source_conversation_path; turn_index; source_branch_type; source_branch_request_index |\n"
        "| Timing and routing | local_raw_record_ordinal; local_source_file_or_log_partition; request_start; request_end; request ID/correlation ID if available; worker/routing ID |\n"
        "| Token semantics | input_tokens; input_token_semantics; cache_read_tokens; cache_read_metric_semantics; cache_write_tokens; cache_write_metric_semantics; output_tokens; requested_output_limit; context_fit_rule_or_config_source |\n"
        "| Outcome and filtering | ttft_ms; itl_ms; e2e_ms; success; success_filter_version; error; error_text_or_category; context_overflow |\n\n"
    )
    text += "## Canonical exact key\n\n"
    text += (
        "source_trace_id + source_outer_idx + source_inner_idx\n\n"
        "- Preserve raw source indices and also publish normalized join fields. The public reference uses "
        "`source_inner_idx_exact_key_normalized=-1` for a documented root-level null inner index. "
        "Use -1 only for that established root-level-null case; do not invent a sentinel when the local "
        "source-inner value is genuinely unknown.\n"
        "- source_conversation_path and turn_index are validation fields. Report match_validation_status "
        "as `high_confidence_exact`, `key_match_validation_missing`, `key_match_validation_conflict`, or "
        "`unmatched` rather than silently accepting a conflict.\n"
        "- Preserve local_copy_label and local_copy_index outside the exact key. They identify separate "
        "local replay instances and must not be deduplicated as if they were duplicate requests.\n\n"
    )
    text += "## Required cpy1–cpy8 semantics check\n\n"
    text += (
        "- For each label, report configured concurrency, observed maximum simultaneous requests, "
        "independent root sessions, distinct conversation IDs, source trace IDs, requests per copy, "
        "successful requests per copy, and start/end timestamps.\n"
        "- Only then determine whether cpy8 means eight independent same-trace sessions, AIPerf "
        "concurrency 8, another copy mechanism, or an unknown experiment label.\n\n"
    )
    text += "## Strict comparison subsets\n\n"
    text += (
        "- Strict TTFT: high-confidence exact key, successful request in both systems, TTFT present.\n"
        "- Strict decode: strict TTFT conditions, output_tokens > 1, ITL present, and equal observed output "
        "length. Keep output-length-different rows for coverage analysis but not strict ITL/TPS ratios.\n"
        "- Keep unmatched, key-match-validation-missing, key-match-validation-conflict, error, cancellation, and context-overflow "
        "rows as explicit categories.\n\n"
    )
    text += "## Context-fit rule\n\n"
    text += (
        "- A local 202,752-context compatibility label requires target logical prompt tokens plus requested "
        "output limit <= 202752, or the exact documented loader/server fit condition. Do not use source "
        "input tokens or public profile input_sequence_length as substitutes.\n\n"
    )
    text += "## Post-extraction metric definitions\n\n"
    text += (
        "- weighted ITL = sum(itl_ms * (output_tokens - 1)) / sum(output_tokens - 1) for valid decode rows.\n"
        "- weighted decode TPS = 1000 / weighted ITL.\n"
        "- wall span = max(request_end) - min(request_start); wall output TPS = total output tokens / wall span.\n"
        "- cpyN TPS retention = weighted_decode_tps_cpyN / weighted_decode_tps_cpy1; median TTFT inflation "
        "= median_ttft_cpyN / median_ttft_cpy1.\n\n"
    )
    text += "## Interpretation guardrails\n\n"
    text += (
        "- Public H200 c8/c12/c16 is mixed-root, P/D-disaggregated, 32×H200, and MTP-enabled. "
        "Local cpy data may have a different workload composition, topology, MTP state, and context limit.\n"
        "- Treat source model labels as workload provenance only. Do not infer GPU affinity, per-ID GPU count, "
        "or a causal HiSparse/KV/MTP contribution from this contract.\n"
    )
    _write(handoff / "id03_local_join_contract.md", text)


def _build_handoff(
    handoff: Path,
    tables: dict[str, pd.DataFrame],
    recipe: dict[str, Any],
    runtime: dict[str, Any],
) -> None:
    concurrency = tables.get("concurrency_summary", pd.DataFrame())
    ids = tables.get("requested_id_resolution", pd.DataFrame())
    comparison = tables.get("h200_c8_hisparse_vs_gpu_resident", pd.DataFrame())
    artifacts = tables.get("artifact_inventory", pd.DataFrame())
    _write(
        handoff / "codex_to_chatgpt.md",
        "# Codex → ChatGPT handoff: H200 GPU-resident MTP\n\n"
        "## Git / Run Provenance\n\n"
        f"- Analysis repository: `https://github.com/sskim-ai/InferenceX_analysis`\n"
        f"- Analysis branch: `analysis/h200-gpu-resident-mtp`\n"
        f"- Analysis starting commit: `{ANALYSIS_START_COMMIT}`\n"
        f"- InferenceX Actions run: `{_recipe_value(recipe, ['actions_run', 'id'])}`\n"
        f"- Canonical run SHA: `{_recipe_value(recipe, ['actions_run', 'head_sha'])}`\n"
        f"- PR: `#{_recipe_value(recipe, ['pull_request', 'number'])}`\n\n"
        "## Downloaded Artifacts\n\n"
        + _artifact_handoff_table(artifacts)
        + "\n\n- **Evidence:** each selected archive has `expired=false`, local SHA-256 matching the GitHub digest, and a passing ZIP CRC check. Full local paths/checksums are in `../manifests/artifact_inventory.csv`.\n\n"
        "## Confirmed Architecture\n\n"
        + _table(tables.get("runtime_configuration", pd.DataFrame()))
        + "\n\n## Runtime KV Findings\n\n"
        + _handoff_kv_highlights()
        + "\n\n"
        + _table(tables.get("kv_cache_runtime", pd.DataFrame()))
        + "\n\n## MTP Findings\n\n"
        + _table(tables.get("mtp_metrics", pd.DataFrame()))
        + "\n\n## Routing / Worker Distribution\n\n"
        "- **Evidence:** frontend logs select both prefill workers and both decode workers across decode DP ranks.\n"
        "- **Unknown:** profile `worker_id` is an observed request field, not proof of a fixed backend worker or GPU affinity. See `../processed/worker_distribution.csv`.\n"
        + "\n\n## c8/c12/c16 Key Metrics\n\n"
        + _table(_select(concurrency, [
            "concurrency", "profiled_request_count", "ttft_mean_ms", "ttft_median_ms", "ttft_p90_ms",
            "itl_weighted_ms", "weighted_decode_tps", "wall_output_tps", "output_tokens_total",
        ]))
        + "\n\n## Requested ID Resolution\n\n"
        + _table(ids)
        + "\n\n## ID01 Key Metrics\n\n"
        + _requested_metrics_table(tables.get("id01_by_concurrency", pd.DataFrame()))
        + "\n\n- **Evidence:** ID01 c8 has one ITL-valid request. Its weighted decode TPS is descriptive "
        "only (n=1) and is excluded from the default comparative TPS figure.\n"
        + "\n\n## ID02 Key Metrics\n\n"
        + _requested_metrics_table(tables.get("id02_by_concurrency", pd.DataFrame()))
        + _id03_handoff_text(tables)
        + "\n\n- **Scope warning:** full per-ID CSVs retain `usage_prompt_cache_read_tokens` only as a raw profile counter; `raw_profile_cache_counter_tps` is not a validated logical-prompt or physical-KV metric.\n"
        + "\n\n## HiSparse c8 vs GPU-resident c8\n\n"
        + _table(comparison)
        + "\n\n## Approximate worker-normalized H200 context\n\n"
        + _table(tables.get("h200_worker_normalized_comparisons", pd.DataFrame()))
        + "\n\n- **Inference:** these rows align one HiSparse decode worker with two GPU-resident "
        "MTP decode workers only as an architectural context. Routing and active load are not proven "
        "equal, and every other system difference remains confounded.\n"
        + "\n\n## User 2GPU Contextual Comparison\n\n"
        + _table(tables.get("local_2gpu_user_reported_reference", pd.DataFrame()))
        + "\n\n## Evidence\n\n"
        "- Public artifacts, their checksums, aggregate validation, and recipe/runtime-log findings are versioned in this study.\n\n"
        "## Inference\n\n"
        "- GPU-resident versus HiSparse c8 findings are observed system-level ratios, not isolated causal effects.\n\n"
        "## Unknown\n\n"
        "- Do not infer per-ID GPU attribution, physical KV allocation beyond log scope, or request-level local-server behavior without private raw evidence.\n\n"
        "## Important Caveats\n\n"
        "- Source workload model labels are not target-model labels.\n"
        "- MTP changes output behavior; strict decode ratios require matching output lengths.\n"
        "- Cache metrics have explicit scope labels; do not conflate a frontend/cache counter with physical KV residency.\n"
        "- Server logs show dynamic routing across two prefill and two decode workers. Request `worker_id` is not demonstrated GPU or backend-worker affinity; see `../processed/worker_distribution.csv`.\n\n"
        "## Files ChatGPT Should Read Next\n\n"
        "1. `studies/h200_gpu_resident_mtp/reports/results_summary_ko.md`\n"
        "2. `studies/h200_gpu_resident_mtp/processed/concurrency_summary.csv`\n"
        "3. `studies/h200_gpu_resident_mtp/processed/schema_mapping.csv`\n"
        "4. `studies/h200_gpu_resident_mtp/processed/profile_field_inventory.csv`\n"
        "5. `studies/h200_gpu_resident_mtp/processed/profile_metric_inventory.csv`\n"
        "6. `studies/h200_gpu_resident_mtp/processed/requested_id_resolution.csv`\n"
        "7. `studies/h200_gpu_resident_mtp/processed/h200_c8_hisparse_vs_gpu_resident.csv`\n"
        "8. `studies/h200_gpu_resident_mtp/processed/exact_match_c8_summary.csv`\n"
        "9. `studies/h200_gpu_resident_mtp/processed/kv_cache_runtime.csv`\n"
        "10. `studies/h200_gpu_resident_mtp/processed/worker_distribution.csv`\n"
        "11. `studies/h200_gpu_resident_mtp/manifests/provenance.json`\n"
        "12. `studies/h200_gpu_resident_mtp/handoff/local_server_evidence_needed.md`\n",
    )
    _write_id03_local_join_contract(handoff, _id03_canonical_id(tables))
    resolved_ids = [
        str(value)
        for value in ids.get("resolved_full_source_trace_id", pd.Series(dtype="string")).dropna()
        if str(value)
    ]
    checklist = "# Preliminary local-server evidence needed\n\n"
    checklist += "This is a checklist for the next analysis phase, not the final internal-GPT prompt.\n\n"
    checklist += "## Configuration and topology\n\n"
    checklist += "- Exact target checkpoint, quantization/precision, GPU SKU/count, TP/DP/PP/EP, and aggregated topology evidence.\n"
    checklist += "- MTP/speculative algorithm, steps, draft tokens, acceptance configuration, and max model/batch limits.\n"
    checklist += "- KV dtype, page/block size, physical GPU KV slots/GiB, prefix-cache configuration, offload policy, and max running requests.\n\n"
    checklist += "## Request-level evidence\n\n"
    checklist += "- source_trace_id, source_outer_idx, source_inner_idx, source_conversation_path, turn_index, timestamps, worker/routing ID.\n"
    checklist += "- input tokens with documented semantics; cache-read/load/store counters with scope; output tokens; TTFT; ITL/decode-duration definition; E2E; cancellation/error and context-overflow fields.\n\n"
    checklist += "## IDs to check locally\n\n"
    if resolved_ids:
        checklist += "- Confirm whether each resolved public ID appears in local data: " + ", ".join(f"`{v}`" for v in resolved_ids) + ".\n"
    else:
        checklist += "- Requested public IDs were not yet resolved in available public data.\n"
    checklist += "\n## ID03 cpy1–cpy8 evidence contract\n\n"
    checklist += (
        "- For each local label 07dd405_cpy1 through 07dd405_cpy8, extract configured concurrency; "
        "observed maximum simultaneous requests; independent root-session count; distinct conversation IDs; "
        "source-trace-ID count; request/success count per copy; and start/end timestamps.\n"
    )
    checklist += (
        "- Verify whether cpyN means N copies of the same canonical trace, AIPerf concurrency N, or something "
        "else. Until that proof exists, do not write cpyN == concurrency N as Evidence.\n"
    )
    checklist += (
        "- Extract the exact join fields and metric semantics in handoff/id03_local_join_contract.md, including "
        "source indices, source path/turn validation, TTFT, ITL, E2E, output length, cache counters, success, "
        "error, and context-overflow status.\n"
    )
    checklist += (
        "- Apply the 202,752 context-fit rule only with target logical prompt tokens plus requested output limit "
        "or a documented loader/server rule; do not substitute public source-input or profile input sequence tokens.\n"
    )
    checklist += "\n## Why these fields matter\n\n"
    checklist += "- Public MTP replay exposes a profile cache counter whose ratio to usage prompt tokens can exceed one, so exact local metric scope is essential before comparison.\n"
    checklist += "- Physical KV allocation and MTP acceptance require startup/runtime evidence rather than architecture assumptions.\n"
    _write(handoff / "local_server_evidence_needed.md", checklist)


def _write_korean_summary(
    path: Path, tables: dict[str, pd.DataFrame], recipe: dict[str, Any], runtime: dict[str, Any]
) -> None:
    concurrency = tables.get("concurrency_summary", pd.DataFrame())
    ids = tables.get("requested_id_resolution", pd.DataFrame())
    comparison = tables.get("h200_c8_hisparse_vs_gpu_resident", pd.DataFrame())
    text = "# 분석 대상\n\n"
    text += f"- Public InferenceX run `{_recipe_value(recipe, ['actions_run', 'id'])}`의 GLM-5.2 FP8 H200 replay를 분석했다. source Claude label은 workload provenance이며 target model이 아니다.\n\n"
    text += "# H200 환경 검증\n\n"
    text += _table(tables.get("runtime_configuration", pd.DataFrame())) + "\n\n"
    text += "# 데이터와 ID 연결 방식\n\n"
    text += "- **Evidence:** profile metadata의 `source_trace_id`와 `source_outer_idx`를 source table에 연결했다. prefix ID는 strict `startswith()` 후보가 하나일 때만 full ID로 확정했다.\n"
    text += "- **Unknown:** conversation ID는 GPU affinity나 ID별 GPU 수를 뜻하지 않는다.\n\n"
    text += "# ID coverage\n\n" + _table(ids) + "\n\n"
    text += "# ID별 성능 핵심 결과\n\n" + _requested_tables_text(tables) + "\n\n"
    text += "# ID03 Deep Dive 및 사내 cpy 비교 준비\n\n"
    text += (
        "- **Evidence:** ID03 prefix 07dd405는 "
        f"{_id03_canonical_id(tables)}로 unique resolution되었다. c8/c12/c16의 source-key "
        "coverage, request-level reference, exact-match table, latency distribution을 별도 version했다.\n\n"
    )
    text += _table(
        _select(
            tables.get("id03_h200_scaling_curve", pd.DataFrame()),
            [
                "concurrency",
                "profile_request_count",
                "coverage_ratio",
                "ttft_median_ms",
                "ttft_p90_ms",
                "weighted_decode_tps",
                "itl_sample_count",
                "ttft_inflation_vs_c8",
                "tps_retention_vs_c8",
            ],
        )
    ) + "\n\n"
    text += _table(
        _select(
            tables.get("id03_cross_concurrency_summary", pd.DataFrame()),
            [
                "pair",
                "matched_source_key_count",
                "strict_ttft_count",
                "strict_decode_count",
                "median_ttft_ratio_right_over_left",
                "weighted_itl_ratio_right_over_left",
                "coverage_overlap_ratio_jaccard",
            ],
        )
    ) + "\n\n"
    text += (
        "- **Inference:** ID03 c8은 119개 profiling/ITL-valid source key를 갖는 primary public "
        "reference다. c12는 112개, c16은 13개 profiling key만 cover하므로 c16은 full-trace "
        "concurrency curve가 아니라 late-tail subset으로 해석한다.\n"
        "- **Unknown:** public profile에는 request-level target logical prompt token 및 requested "
        "output limit이 없어 202,752 context-compatible exact subset은 unavailable이다. "
        "input_sequence_length 또는 source_input_tokens로 대체하지 않는다.\n"
        "- **Unknown:** 사내 cpy1~cpy8 수치는 이 repository에 없으며 생성하지 않았다. 이후 계약은 "
        "handoff/id03_local_join_contract.md와 reports/12_id03_local_cpy_comparison_plan.md를 따른다.\n\n"
    )
    text += "# Concurrency c8 / c12 / c16 비교\n\n"
    text += "- 이 study의 public run은 c8/c12/c16이며, 고정 시간 replay이므로 coverage를 동반해 비교한다.\n"
    text += _table(_select(concurrency, [
        "concurrency", "profiled_request_count", "ttft_median_ms", "weighted_decode_tps", "wall_output_tps",
    ])) + "\n\n"
    text += "# Root agent와 subagent 비교\n\n"
    text += _table(tables.get("root_subagent_summary", pd.DataFrame())) + "\n\n"
    text += "# Context 및 theoretical cache reuse 영향\n\n"
    text += "- **Evidence:** profile cache counter와 aggregate frontend-cache metrics는 별도 scope로 보존했다.\n"
    text += "- **Unknown:** theoretical source prefix reuse는 actual H200 cache residency/hit와 동일하지 않다.\n\n"
    text += _table(tables.get("context_cache_relationship", pd.DataFrame())) + "\n\n"
    text += "# 가장 부담이 큰 trace IDs\n\n" + _table(_select(tables.get("top_ids_by_workload_or_latency", pd.DataFrame()).head(20), [
        "concurrency", "root_trace_id", "profiled_request_count", "input_sequence_length_total", "output_tokens_total", "ttft_median_ms",
    ])) + "\n\n"
    text += "# Aggregate 결과 재현 검증\n\n" + _table(tables.get("validation_summary", pd.DataFrame())) + "\n\n"
    text += "# 확인된 사실\n\n"
    text += "- **Evidence:** raw profile rows와 published aggregate의 request count, tokens, TTFT, ITL, E2E, throughput은 validation table 범위에서 대조된다.\n\n"
    text += "# 추론\n\n"
    text += "- **Inference (high confidence):** runtime log는 FP8 KV allocation record와 HiSparse/OFFload 비활성화를 직접 보인다. 다만 rank-scoped GiB를 cluster 전체 physical capacity로 합산하지 않는다.\n\n"
    text += "# 확인할 수 없는 것\n\n"
    text += "- **Unknown:** HiSparse 단독 효과, ID별 GPU attribution, 사내 2-GPU의 request-level behavior, and unsupported cache/MTP counter semantics.\n\n"
    text += "# 데이터 한계\n\n"
    text += "- warmup/recycling, shared system, repeated source IDs, MTP output variance, and cache metric scope prevent naïve request-independence or apples-to-apples conclusions.\n\n"
    text += "# 재현 방법\n\n"
    text += "```sh\nmake mtp-analyze\nmake mtp-report\n```\n\n"
    text += "# 기존 HiSparse c8와의 observed difference\n\n" + _table(comparison) + "\n"
    _write(path, text)


def _write_kv_runtime(processed: Path, recipe: dict[str, Any], runtime: dict[str, Any]) -> None:
    rows = [
        {
            "concurrency": "configured",
            "component": "configured_decode",
            "field": "kv_cache_dtype",
            "value": "fp8_e4m3",
            "scope": "configured recipe",
            "classification": "Evidence",
        },
        {
            "concurrency": "configured",
            "component": "configured_decode",
            "field": "kv_offloading",
            "value": "none",
            "scope": "configured matrix",
            "classification": "Evidence",
        },
        {
            "concurrency": "configured",
            "component": "configured_decode",
            "field": "page_size",
            "value": "64",
            "scope": "configured recipe",
            "classification": "Evidence",
        },
        {
            "concurrency": "configured",
            "component": "configured_decode",
            "field": "max_running_requests",
            "value": "200",
            "scope": "configured recipe",
            "classification": "Evidence",
        },
    ]
    for item in _runtime_items(runtime):
        subject = str(item.get("subject") or item.get("field") or "runtime_log")
        value = item.get("value")
        scope = item.get("scope") or item.get("details") or item.get("source") or "server log"
        references = item.get("references")
        concurrencies = sorted(
            {
                str(reference.get("concurrency"))
                for reference in references
                if isinstance(reference, dict) and reference.get("concurrency") is not None
            }
        ) if isinstance(references, list) else []
        source = "; ".join(
            f"c{reference.get('concurrency')}:{reference.get('member')}:{reference.get('lines', reference.get('json_path', ''))}"
            for reference in references[:3]
            if isinstance(reference, dict)
        ) if isinstance(references, list) else "server log"
        flattened = value.items() if isinstance(value, dict) else [(subject, value)]
        for key, item_value in flattened:
            rows.append(
                {
                    "concurrency": ";".join(concurrencies) if concurrencies else "runtime",
                    "component": subject,
                    "field": key,
                    "value": json.dumps(item_value, ensure_ascii=False, sort_keys=True)
                    if isinstance(item_value, (dict, list))
                    else item_value,
                    "scope": scope,
                    "source": source,
                    "classification": item.get("classification") or "Evidence",
                }
            )
    if not runtime:
        rows.append(
            {
                "component": "runtime_log",
                "concurrency": "runtime",
                "field": "physical_kv_allocation",
                "value": None,
                "scope": "server logs not yet parsed",
                "source": None,
                "classification": "Unknown",
            }
        )
    pd.DataFrame(rows).to_csv(processed / "kv_cache_runtime.csv", index=False)


def _augment_mtp_metrics(processed: Path, frame: pd.DataFrame, runtime: dict[str, Any]) -> None:
    if frame.empty:
        return
    result = frame.copy()
    finding = next(
        (item for item in _runtime_items(runtime) if item.get("subject") == "mtp_launch_and_runtime_behavior"),
        None,
    )
    if not finding or not isinstance(finding.get("value"), dict):
        result.to_csv(processed / "mtp_metrics.csv", index=False)
        return
    value = finding["value"]
    for source, target in (
        ("runtime_decode_batch_sample_accept_length_range", "runtime_sample_acceptance_length_range"),
        ("runtime_decode_batch_sample_accept_rate_range", "runtime_sample_acceptance_rate_range"),
        ("simulate_acceptance_length", "runtime_configured_simulated_acceptance_length"),
        ("simulate_acceptance_method", "runtime_configured_acceptance_method"),
        ("simulate_acceptance_token_mode", "runtime_configured_acceptance_token_mode"),
    ):
        result[target] = json.dumps(value[source]) if isinstance(value.get(source), list) else value.get(source)
    result["runtime_log_status"] = "sampled_decode_batch_evidence_not_request_weighted"
    result["runtime_evidence_classification"] = "Evidence"
    result.to_csv(processed / "mtp_metrics.csv", index=False)


def _augment_runtime_configuration(processed: Path, frame: pd.DataFrame, runtime: dict[str, Any]) -> None:
    if frame.empty:
        return
    result = frame.copy()
    if "field" not in result:
        return
    selected: dict[str, tuple[str, str]] = {
        "backend_hardware_and_pd_topology.backend_gpu_count": ("runtime_backend_gpu_count", "backend GPU count"),
        "backend_hardware_and_pd_topology.prefill_workers": ("runtime_prefill_workers", "server log"),
        "backend_hardware_and_pd_topology.decode_workers": ("runtime_decode_workers", "server log"),
        "effective_prefill_server_flags.tp_size": ("runtime_prefill_tp_size", "server log resolves matrix/recipe discrepancy"),
        "effective_prefill_server_flags.attn_cp_size": ("runtime_prefill_attn_cp_size", "server log"),
        "effective_decode_server_flags_and_kv_residency_controls.enable_hisparse": ("runtime_enable_hisparse", "server log"),
        "effective_decode_server_flags_and_kv_residency_controls.cpu_offload_gb": ("runtime_cpu_offload_gb", "server log"),
        "effective_decode_server_flags_and_kv_residency_controls.disaggregation_decode_enable_offload_kvcache": ("runtime_decode_kv_offload", "server log"),
        "effective_decode_server_flags_and_kv_residency_controls.kv_cache_dtype": ("runtime_decode_kv_dtype", "server log"),
    }
    additions = []
    for item in _runtime_items(runtime):
        subject = str(item.get("subject"))
        value = item.get("value")
        if not isinstance(value, dict):
            continue
        for key, item_value in value.items():
            requested = selected.get(f"{subject}.{key}")
            if not requested:
                continue
            field, source = requested
            additions.append(
                {
                    "field": field,
                    "value": item_value,
                    "classification": item.get("classification", "Evidence"),
                    "source": source,
                }
            )
    if additions:
        result = pd.concat([result, pd.DataFrame(additions)], ignore_index=True, sort=False)
    result.drop_duplicates(subset=["field"], keep="last").to_csv(
        processed / "runtime_configuration.csv", index=False
    )


def _build_figures(figures: Path, tables: dict[str, pd.DataFrame]) -> None:
    summary = tables.get("concurrency_summary", pd.DataFrame())
    _line_plot(summary, "ttft_median_ms", "TTFT median (ms)", figures / "ttft_vs_concurrency.png")
    _line_plot(summary, "weighted_decode_tps", "Weighted decode TPS (tok/s)", figures / "weighted_decode_tps_vs_concurrency.png")
    _line_plot(summary, "wall_output_tps", "Wall output TPS (tok/s)", figures / "wall_output_tps_vs_concurrency.png")
    for label in ("id01", "id02"):
        frame = tables.get(f"{label}_by_concurrency", pd.DataFrame())
        _line_plot(frame, "ttft_median_ms", f"{label.upper()} TTFT median (ms)", figures / f"{label}_ttft.png")
        _comparative_tps_plot(
            frame,
            f"{label.upper()} weighted decode TPS (tok/s)",
            figures / f"{label}_tps.png",
        )
    cache = tables.get("cache_metrics", pd.DataFrame())
    _line_plot(cache, "server_frontend_cache_hit_rate", "Server frontend cache hit rate", figures / "cache_read_ratio.png")
    mtp = tables.get("mtp_metrics", pd.DataFrame())
    _mtp_acceptance_plot(mtp, figures / "mtp_acceptance_metric.png")
    _branch_plot(tables.get("root_subagent_summary", pd.DataFrame()), "ttft_median_ms", "TTFT median (ms)", figures / "root_vs_subagent_ttft.png")
    _branch_plot(tables.get("root_subagent_summary", pd.DataFrame()), "weighted_decode_tps", "Weighted decode TPS (tok/s)", figures / "root_vs_subagent_tps.png")
    comparison = tables.get("h200_c8_hisparse_vs_gpu_resident", pd.DataFrame())
    _comparison_plot(comparison, figures / "hisparse_c8_vs_gpu_resident_mtp_c8.png")


def _line_plot(frame: pd.DataFrame, field: str, ylabel: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    if not frame.empty and {"concurrency", field}.issubset(frame.columns):
        data = frame[["concurrency", field]].dropna().sort_values("concurrency")
        if not data.empty:
            ax.plot(data["concurrency"], data[field], marker="o")
            for _, item in data.iterrows():
                ax.annotate(f"{item[field]:.3g}", (item["concurrency"], item[field]), xytext=(0, 7), textcoords="offset points", ha="center")
        else:
            ax.text(0.5, 0.5, "Unknown / no observed sample", ha="center", va="center", transform=ax.transAxes)
    else:
        ax.text(0.5, 0.5, "Unknown / no observed sample", ha="center", va="center", transform=ax.transAxes)
    ax.set_xlabel("Requested concurrency")
    ax.set_ylabel(ylabel)
    ax.set_title(ylabel + " by concurrency")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _comparison_plot(frame: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    data = frame.loc[frame.get("comparison_scope", pd.Series(dtype="string")) == "run_level_unpaired_observed_system_difference"].copy()
    data = data.loc[data.get("metric", pd.Series(dtype="string")).isin(["weighted_decode_tps", "wall_output_tps"])]
    if not data.empty:
        labels = data["metric"].tolist()
        x = range(len(labels))
        ax.bar([i - 0.18 for i in x], pd.to_numeric(data["hisparse_c8_value"], errors="coerce"), width=0.36, label="HiSparse c8")
        ax.bar([i + 0.18 for i in x], pd.to_numeric(data["gpu_resident_mtp_c8_value"], errors="coerce"), width=0.36, label="GPU-resident MTP c8")
        ax.set_xticks(list(x), labels)
        ax.legend()
    else:
        ax.text(0.5, 0.5, "Unknown / no comparable c8 data", ha="center", va="center", transform=ax.transAxes)
    ax.set_ylabel("tok/s")
    ax.set_title("Observed system-level c8 comparison (not causal)")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _comparative_tps_plot(frame: pd.DataFrame, ylabel: str, path: Path) -> None:
    """Suppress TPS lines where fewer than three ITL-valid requests support a point."""

    fig, ax = plt.subplots(figsize=(7, 4.5))
    required = {"concurrency", "weighted_decode_tps", "itl_sample_count"}
    if not frame.empty and required.issubset(frame.columns):
        data = frame.loc[pd.to_numeric(frame["itl_sample_count"], errors="coerce") >= 3].copy()
        data = data[["concurrency", "weighted_decode_tps"]].dropna().sort_values("concurrency")
        if not data.empty:
            ax.plot(data["concurrency"], data["weighted_decode_tps"], marker="o")
            for _, item in data.iterrows():
                ax.annotate(
                    f"{item['weighted_decode_tps']:.3g}",
                    (item["concurrency"], item["weighted_decode_tps"]),
                    xytext=(0, 7),
                    textcoords="offset points",
                    ha="center",
                )
        else:
            ax.text(
                0.5,
                0.5,
                "Suppressed: fewer than 3 ITL-valid requests per point\n(descriptive only)",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
    else:
        ax.text(0.5, 0.5, "Unknown / no observed sample", ha="center", va="center", transform=ax.transAxes)
    ax.set_xlabel("Requested concurrency")
    ax.set_ylabel(ylabel)
    ax.set_title(ylabel + " by concurrency")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _mtp_acceptance_plot(frame: pd.DataFrame, path: Path) -> None:
    """Plot server-log MTP samples without relabelling them as request averages."""

    fig, ax = plt.subplots(figsize=(7, 4.5))
    rows: list[tuple[float, float, float, float]] = []
    if not frame.empty and {"concurrency", "runtime_sample_acceptance_length_range"}.issubset(frame.columns):
        for _, item in frame.iterrows():
            value = item.get("runtime_sample_acceptance_length_range")
            try:
                parsed = json.loads(value) if isinstance(value, str) else value
                low, high = float(parsed[0]), float(parsed[1])
                concurrency = float(item["concurrency"])
            except (IndexError, TypeError, ValueError, json.JSONDecodeError):
                continue
            rows.append((concurrency, low, high, (low + high) / 2))
    if rows:
        rows.sort()
        x = [row[0] for row in rows]
        y = [row[3] for row in rows]
        lower = [row[3] - row[1] for row in rows]
        upper = [row[2] - row[3] for row in rows]
        ax.errorbar(x, y, yerr=[lower, upper], fmt="o-", capsize=4)
        for concurrency, low, high, midpoint in rows:
            ax.annotate(
                f"{low:.2f}–{high:.2f}",
                (concurrency, midpoint),
                xytext=(0, 7),
                textcoords="offset points",
                ha="center",
            )
    else:
        ax.text(0.5, 0.5, "Unknown / no server-log MTP sample", ha="center", va="center", transform=ax.transAxes)
    ax.set_xlabel("Requested concurrency")
    ax.set_ylabel("Sampled acceptance length")
    ax.set_title("MTP decode-batch acceptance samples (not request-weighted)")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _branch_plot(frame: pd.DataFrame, field: str, ylabel: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    if not frame.empty and {"concurrency", "source_branch_type", field}.issubset(frame.columns):
        data = frame[["concurrency", "source_branch_type", field]].dropna()
        if not data.empty:
            for branch, group in data.groupby("source_branch_type"):
                group = group.sort_values("concurrency")
                ax.plot(group["concurrency"], group[field], marker="o", label=str(branch))
            ax.legend(title="source branch origin")
        else:
            ax.text(0.5, 0.5, "Unknown / no observed sample", ha="center", va="center", transform=ax.transAxes)
    else:
        ax.text(0.5, 0.5, "Unknown / no observed sample", ha="center", va="center", transform=ax.transAxes)
    ax.set_xlabel("Requested concurrency")
    ax.set_ylabel(ylabel)
    ax.set_title("Source-root vs source-subagent origin")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _artifact_handoff_table(frame: pd.DataFrame) -> str:
    """Render the nine requested artifact records, not merely a manifest link."""

    if frame.empty:
        return "- No artifact inventory rows available."
    selected = frame.loc[
        frame.get("category", pd.Series(dtype="string")).isin(
            ["raw_result", "aggregate", "server_logs"]
        )
    ].copy()
    return _table(
        _select(
            selected.sort_values(["concurrency", "category"]),
            [
                "concurrency",
                "category",
                "artifact_id",
                "artifact_name",
                "github_digest",
                "download_status",
                "zip_validation",
                "expired",
            ],
        )
    )


def _handoff_kv_highlights() -> str:
    """Keep the scope-critical runtime KV allocations above long evidence tables."""

    return _table(
        pd.DataFrame(
            [
                {
                    "component": "prefill runtime",
                    "observed allocation": "logical token limit 1,048,576; scheduler 16,384 blocks × page 64; 6.93–7.70 GiB primary + 0.77 GiB secondary allocation records",
                    "scope": "individual logged ATTN_CP/TP rank in one 8-GPU prefill worker; logical pool is per worker, not a 16-GPU/global total",
                    "classification": "Evidence",
                },
                {
                    "component": "decode runtime",
                    "observed allocation": "runtime-profiled token value 218,560; 12.51 GiB primary + 0.16 GiB secondary allocation records; page 64 / FP8 E4M3",
                    "scope": "individual logged DP/TP rank in one decode worker; do not sum or multiply into cluster physical capacity",
                    "classification": "Evidence",
                },
            ]
        )
    )


def _requested_metrics_table(frame: pd.DataFrame) -> str:
    return _table(
        _select(
            frame,
            [
                "root_trace_id",
                "concurrency",
                "all_request_count",
                "warmup_count",
                "profiled_request_count",
                "output_tokens_total",
                "ttft_mean_ms",
                "ttft_median_ms",
                "ttft_p90_ms",
                "itl_sample_count",
                "weighted_decode_tps",
                "e2e_median_ms",
                "wall_span_s",
                "wall_output_tps",
                "error_count",
                "cancellation_count",
                "sample_quality",
                "decode_tps_comparison_status",
            ],
        )
    )


def _requested_tables_text(tables: dict[str, pd.DataFrame]) -> str:
    chunks = []
    for label in ("id01", "id02", "id03", "id04", "id05"):
        frame = tables.get(f"{label}_by_concurrency", pd.DataFrame())
        if frame.empty:
            chunks.append(f"### {label.upper()}\n\n- **Unknown:** no public profiling rows or no unique resolution.\n")
        else:
            chunks.append(
                f"### {label.upper()}\n\n"
                + _table(_select(frame, [
                    "root_trace_id", "concurrency", "profiled_request_count", "ttft_median_ms", "ttft_p90_ms",
                    "weighted_decode_tps", "wall_output_tps", "output_tokens_total", "error_count", "cancellation_count",
                    "decode_tps_comparison_status",
                ]))
            )
    chunks.append(
        "- **Scope warning:** raw `usage_prompt_cache_read_tokens` is retained in full per-ID CSVs, "
        "and `raw_profile_cache_counter_tps`, where present, is an unvalidated raw-profile-counter rate. "
        "Neither is a logical-cache ratio, physical KV-load metric, or cache-load throughput."
    )
    return "\n\n".join(chunks)


def _runtime_evidence_text(runtime: dict[str, Any]) -> str:
    if not runtime:
        return "- **Unknown:** runtime-log evidence file was not available when this report was built."
    rows = []
    for item in _runtime_items(runtime):
        subject = item.get("subject") or item.get("field") or "runtime_log"
        value = item.get("value")
        rows.append(f"- **{item.get('classification', 'Evidence')}:** `{subject}` = `{value}` ({item.get('source', 'server log')}).")
    return "\n".join(rows) if rows else "- **Unknown:** no structured runtime findings were parsed."


def _runtime_items(runtime: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("evidence", "findings", "runtime_findings", "items"):
        value = runtime.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _recipe_value(payload: dict[str, Any], keys: list[str]) -> Any | None:
    value: Any = payload
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path) if path.exists() else pd.DataFrame()
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _select(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return frame[[column for column in columns if column in frame]].copy() if not frame.empty else frame


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "- No comparable rows available."
    view = frame.copy()
    if len(view) > 30:
        view = view.head(30)
    columns = list(view.columns)
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    rows = []
    for values in view.itertuples(index=False, name=None):
        cells = [_cell(value) for value in values]
        rows.append("| " + " | ".join(cells) + " |")
    suffix = "\n\n- Table is truncated to 30 rows." if len(frame) > len(view) else ""
    return "\n".join([header, divider, *rows]) + suffix


def _cell(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _write(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
