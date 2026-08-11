#!/usr/bin/env python3
# ruff: noqa: I001
"""Reconstruct public c8 offered load and explicit scheduler evidence.

This is intentionally a two-source analysis:

* profile request timestamps reconstruct **HTTP/client-observed interval overlap**;
* AIPerf's public server-metrics export and frontend logs provide separately
  scoped **runtime scheduler and routing evidence**.

The script never re-labels HTTP overlap as an SGLang running-request count and
never turns configured capacities into observed runtime values.  It streams
the 3.4-GB metrics JSON selectively rather than loading it as one object.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import tarfile
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from h200_agentx_analysis.concurrency_reconstruction import (  # noqa: E402
    reconstruct_http_inflight,
    summarize_http_inflight,
)


ID03_CANONICAL_ID = "07dd40536557a1d6440a923557c3129dc929"
STUDY_ROOT_DEFAULT = REPOSITORY_ROOT / "studies/h200_gpu_resident_mtp"
RAW_ROOT_DEFAULT = REPOSITORY_ROOT / "data/raw/h200_gpu_resident_mtp"

# Selected metrics are explicit runtime gauges/histograms relevant to offered
# load.  CSV inventory retains a wider candidate set; the JSON extractor only
# streams metrics needed for time-series and scheduler summaries.
JSON_TARGET_METRICS = (
    "sglang:num_running_reqs",
    "sglang:num_queue_reqs",
    "sglang:num_prefill_bootstrap_queue_reqs",
    "sglang:num_prefill_inflight_queue_reqs",
    "sglang:num_decode_prealloc_queue_reqs",
    "sglang:num_decode_transfer_queue_reqs",
    "sglang:token_usage",
    "sglang:pending_prealloc_token_usage",
    "sglang:queue_time_seconds",
)
TIMELINE_METRICS = set(JSON_TARGET_METRICS) - {"sglang:queue_time_seconds"}

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
FRONTEND_MEMBER = re.compile(r"(?:^|/)worker-\d+_frontend_\d+\.out$")
COMPLETION_PATTERN = re.compile(
    r"request completed request_id=(?P<router_request_id>[0-9a-f-]+).*?"
    r'x_request_id="(?P<x_request_id>[0-9a-f-]+)".*?'
    r"prefill_worker_id=(?P<prefill_worker_id>\d+)\s+"
    r"decode_worker_id=(?P<decode_worker_id>\d+)",
    flags=re.IGNORECASE,
)
QUEUE_CHECKPOINT_PATTERN = re.compile(
    r"dynamo_kv_router::scheduling::queue: refreshed overlap scores after long queue wait\s+"
    r'request_id="(?P<router_request_id>[0-9a-f-]+)"\s+wait_ms=(?P<wait_ms>\d+)',
    flags=re.IGNORECASE,
)
TIMESTAMP_PATTERN = re.compile(r"(?P<timestamp>\d{4}-\d{2}-\d{2}T[^\s]+Z)")
ARCHIVE_COUNTER_PATTERN = re.compile(
    r"(?P<name>max[_ -]?running[_ -]?(?:reqs|requests)|"
    r"max[_ -]?waiting[_ -]?(?:reqs|requests)|"
    r"(?:num[_ -]?)?running[_ -]?(?:reqs|requests)|"
    r"(?:num[_ -]?)?(?:waiting|queue)[_ -]?(?:reqs|requests))\s*[:=]\s*"
    r"(?P<value>[-+]?\d+(?:\.\d+)?)",
    flags=re.IGNORECASE,
)

SUMMARY_METRICS = {
    "dynamo_component_inflight_requests",
    "dynamo_frontend_inflight_requests",
    "dynamo_frontend_queued_requests",
    "dynamo_frontend_router_queue_pending_isl_tokens",
    "dynamo_frontend_router_queue_pending_requests",
    "dynamo_request_plane_inflight_requests",
    "dynamo_request_plane_queue_seconds",
    "dynamo_work_handler_queue_capacity",
    "dynamo_work_handler_queue_depth",
    "sglang:full_token_usage",
    "sglang:num_decode_prealloc_queue_reqs",
    "sglang:num_decode_transfer_queue_reqs",
    "sglang:num_prefill_bootstrap_queue_reqs",
    "sglang:num_prefill_inflight_queue_reqs",
    "sglang:num_queue_reqs",
    "sglang:num_running_reqs",
    "sglang:num_unique_running_routing_keys",
    "sglang:pending_prealloc_token_usage",
    "sglang:queue_time_seconds",
    "sglang:token_usage",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-root", type=Path, default=STUDY_ROOT_DEFAULT)
    parser.add_argument("--raw-root", type=Path, default=RAW_ROOT_DEFAULT)
    parser.add_argument(
        "--requests",
        type=Path,
        default=STUDY_ROOT_DEFAULT / "processed/h200_requests_profiled.parquet",
    )
    parser.add_argument(
        "--all-requests",
        type=Path,
        default=STUDY_ROOT_DEFAULT / "processed/h200_requests_all.parquet",
    )
    parser.add_argument("--downsample-seconds", type=int, default=10)
    parser.add_argument(
        "--skip-metrics-json",
        action="store_true",
        help="Use the compact public CSV metric export only; no scheduler timeline is made.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.downsample_seconds < 1:
        raise SystemExit("--downsample-seconds must be positive")
    processed = args.study_root / "processed"
    figures = args.study_root / "figures"
    processed.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    if not args.requests.exists() or not args.all_requests.exists():
        raise SystemExit("missing MTP request Parquet; run `make mtp-analyze` first")

    raw_paths = _raw_paths(args.raw_root)
    profile = _load_c8_profiled(args.requests)
    all_c8 = _load_c8_all(args.all_requests)
    request_ids = _read_profile_request_ids(raw_paths["profile_export"])
    profile = _attach_request_ids(profile, request_ids)
    _assert_profile_scope(profile)

    reconstruction = reconstruct_http_inflight(profile)
    http_requests = reconstruction.requests.copy()
    http_timeline = reconstruction.timeline.copy()
    http_summary = summarize_http_inflight(reconstruction)
    http_summary.update(
        {
            "agentx_root_concurrency_configured": 8,
            "profiling_request_count": int(len(profile)),
            "profiling_root_id_count": int(profile["root_trace_id"].nunique()),
            "profiling_root_request_count": int(
                profile["source_branch_type"].astype("string").eq("root").sum()
            ),
            "profiling_subagent_request_count": int(
                profile["source_branch_type"].astype("string").eq("subagent").sum()
            ),
            "interval_semantics": "[request_start_ns, request_end_ns)",
            "same_timestamp_policy": "all end events before starts; start context includes all same-timestamp starts",
        }
    )
    # Requested aliases make the weighting explicit while keeping the report
    # schema easy to read.
    http_summary["mean_root_inflight"] = http_summary.get("time_weighted_mean_root_inflight")
    http_summary["mean_subagent_inflight"] = http_summary.get(
        "time_weighted_mean_subagent_inflight"
    )
    http_timeline.to_csv(processed / "c8_http_inflight_timeline.csv", index=False)
    _select_request_context(http_requests).to_csv(
        processed / "c8_requests_with_inflight_context.csv", index=False
    )
    pd.DataFrame([http_summary]).to_csv(processed / "c8_http_concurrency_summary.csv", index=False)

    frontend = _parse_frontend_log_archive(raw_paths["server_archive"])
    routed = _attach_frontend_routing(http_requests, frontend["completions"])
    routed_profile = routed.loc[routed["interval_valid"].fillna(False)].copy()
    routing_summary = _routing_summary(routed_profile)
    routing_summary.to_csv(processed / "c8_backend_worker_routing_summary.csv", index=False)
    _router_checkpoint_summary(routed_profile).to_csv(
        processed / "c8_router_queue_wait_checkpoint_summary.csv", index=False
    )

    id03 = routed_profile.loc[
        routed_profile["root_trace_id"].astype("string") == ID03_CANONICAL_ID
    ].copy()
    if len(id03) != 119:
        raise SystemExit(f"expected 119 ID03 c8 profiling rows; observed {len(id03)}")
    _select_id03_load(id03).to_csv(processed / "id03_c8_with_system_load.csv", index=False)
    _id03_backend_pressure(id03).to_csv(processed / "id03_c8_backend_pressure.csv", index=False)
    relationships = _load_latency_relationship(id03)
    relationships.to_csv(processed / "id03_c8_load_latency_relationship.csv", index=False)
    _load_buckets(id03).to_csv(processed / "id03_c8_load_buckets.csv", index=False)
    _root_subagent_load_summary(routed_profile, id03).to_csv(
        processed / "c8_root_subagent_offered_load_summary.csv", index=False
    )

    metrics_csv = _metrics_csv_inventory(raw_paths["metrics_csv"])
    archive_candidates = frontend["scheduler_candidates"]
    inventory = pd.concat([metrics_csv, archive_candidates], ignore_index=True, sort=False)
    inventory.to_csv(processed / "c8_scheduler_metric_inventory.csv", index=False)

    scheduler = _empty_scheduler_result()
    if not args.skip_metrics_json and raw_paths["metrics_json"].exists():
        scheduler = _extract_scheduler_metrics(raw_paths["metrics_json"], args.downsample_seconds)
        _write_scheduler_outputs(processed, scheduler)

    summary_rows = _concurrency_reconstruction_rows(
        http_summary=http_summary,
        scheduler=scheduler,
        routed_profile=routed_profile,
        frontend=frontend,
    )
    pd.DataFrame(summary_rows).to_csv(
        processed / "c8_concurrency_reconstruction_summary.csv", index=False
    )
    _build_figures(figures, http_timeline, id03, scheduler)
    _write_run_metadata(processed, all_c8, profile, frontend, scheduler)
    print(
        json.dumps(
            {
                "status": "completed",
                "profile_request_count": int(len(profile)),
                "id03_request_count": int(len(id03)),
                "http_max_inflight": http_summary.get("max_inflight"),
                "scheduler_json_available": bool(scheduler["stats_rows"]),
                "routing_profile_match_count": int(routed_profile["routing_match_status"].eq("exact").sum()),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _raw_paths(raw_root: Path) -> dict[str, Path]:
    result = raw_root / "conc8" / "result" / "9017979109" / "conc_8" / "aiperf_artifacts"
    paths = {
        "profile_export": result / "profile_export.jsonl",
        "metrics_csv": result / "server_metrics_export.csv",
        "metrics_json": result / "server_metrics_export.json",
        "server_archive": raw_root
        / "conc8/server_logs/9017974866/multinode_server_logs.tar.gz",
    }
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        raise SystemExit(f"missing public c8 raw inputs: {', '.join(missing)}")
    return paths


def _load_c8_profiled(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    result = frame.loc[pd.to_numeric(frame["concurrency"], errors="coerce") == 8].copy()
    if "is_profiled_valid" in result:
        result = result.loc[result["is_profiled_valid"].fillna(False)].copy()
    return result.reset_index(drop=True)


def _load_c8_all(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    return frame.loc[pd.to_numeric(frame["concurrency"], errors="coerce") == 8].copy()


def _read_profile_request_ids(path: Path) -> pd.DataFrame:
    """Stream x_request_id from raw JSONL by its canonical one-based ordinal."""

    rows: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as handle:
        for ordinal, line in enumerate(handle, start=1):
            record = json.loads(line)
            metadata = record.get("metadata") or {}
            rows.append(
                {
                    "record_ordinal": ordinal,
                    "x_request_id": metadata.get("x_request_id"),
                    "raw_request_start_ns": metadata.get("request_start_ns"),
                    "raw_request_end_ns": metadata.get("request_end_ns"),
                }
            )
    return pd.DataFrame(rows)


def _attach_request_ids(profile: pd.DataFrame, request_ids: pd.DataFrame) -> pd.DataFrame:
    result = profile.merge(request_ids, on="record_ordinal", how="left", validate="one_to_one")
    if result["x_request_id"].isna().any():
        raise SystemExit("could not attach x_request_id to every c8 profiling profile row")
    for canonical, raw in (
        ("request_start_ns", "raw_request_start_ns"),
        ("request_end_ns", "raw_request_end_ns"),
    ):
        left = pd.to_numeric(result[canonical], errors="coerce")
        right = pd.to_numeric(result[raw], errors="coerce")
        # The original parser previously passed JSON integer nanoseconds through
        # a float-oriented DataFrame path before Parquet.  The raw ordinal and
        # request endpoints agree within the resulting IEEE-754 rounding band;
        # use this only as a merge guard, not as a timestamp rewrite.
        maximum_difference = float((left - right).abs().max())
        if maximum_difference > 512:
            raise SystemExit(f"raw profile ordinal merge failed {canonical} cross-check")
        result[f"{canonical}_raw_join_max_abs_difference_ns"] = maximum_difference
    return result.drop(columns=["raw_request_start_ns", "raw_request_end_ns"])


def _assert_profile_scope(profile: pd.DataFrame) -> None:
    if len(profile) != 957:
        raise SystemExit(f"expected 957 c8 profiled rows; observed {len(profile)}")
    branches = set(profile["source_branch_type"].dropna().astype(str))
    if branches != {"root", "subagent"}:
        raise SystemExit(f"unexpected c8 source branch categories: {sorted(branches)}")
    start = pd.to_numeric(profile["request_start_ns"], errors="coerce")
    end = pd.to_numeric(profile["request_end_ns"], errors="coerce")
    if not (start.notna() & end.notna() & (end > start)).all():
        raise SystemExit("c8 profiling request interval is missing or non-positive")


def _select_request_context(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "request_identity_key",
        "root_trace_id",
        "source_trace_id",
        "source_outer_idx",
        "source_inner_idx",
        "source_conversation_path",
        "source_branch_type",
        "exact_source_key",
        "session_num",
        "turn_index",
        "request_start_ns",
        "request_ack_ns",
        "request_end_ns",
        "ttft_ms",
        "itl_ms",
        "e2e_ms",
        "output_tokens",
        "worker_id",
        "x_request_id",
        "interval_valid",
        "branch_concurrency_group",
        "system_inflight_before_start",
        "system_inflight_at_start",
        "root_inflight_at_start",
        "subagent_inflight_at_start",
        "system_inflight_before_end",
        "system_inflight_after_end",
    ]
    return _available_columns(frame, columns)


def _select_id03_load(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "exact_source_key",
        "source_request_index",
        "source_outer_idx",
        "source_inner_idx",
        "source_conversation_path",
        "source_branch_type",
        "request_start_ns",
        "request_end_ns",
        "ttft_ms",
        "itl_ms",
        "e2e_ms",
        "output_tokens",
        "system_inflight_before_start",
        "system_inflight_at_start",
        "root_inflight_at_start",
        "subagent_inflight_at_start",
        "system_inflight_before_end",
        "system_inflight_after_end",
        "x_request_id",
    ]
    return _available_columns(frame.sort_values("request_start_ns"), columns)


def _load_latency_relationship(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for predictor, outcome in (
        ("system_inflight_at_start", "ttft_ms"),
        ("system_inflight_at_start", "e2e_ms"),
        ("system_inflight_at_start", "itl_ms"),
        ("root_inflight_at_start", "ttft_ms"),
        ("subagent_inflight_at_start", "ttft_ms"),
    ):
        subset = frame[[predictor, outcome]].apply(pd.to_numeric, errors="coerce").dropna()
        if len(subset) < 3 or subset[predictor].nunique() < 2:
            rho = p_value = None
            classification = "Unknown"
            note = "insufficient variation for Spearman correlation"
        else:
            result = spearmanr(subset[predictor], subset[outcome])
            rho = float(result.statistic) if math.isfinite(result.statistic) else None
            p_value = float(result.pvalue) if math.isfinite(result.pvalue) else None
            classification = "Evidence" if rho is not None else "Unknown"
            note = (
                "Spearman on ID03 public c8 profile rows; HTTP interval overlap at request start, "
                "not an SGLang scheduler counter or causal estimate"
            )
        rows.append(
            {
                "predictor": predictor,
                "outcome": outcome,
                "sample_count": int(len(subset)),
                "spearman_rho": rho,
                "p_value": p_value,
                "classification": classification,
                "notes": note,
            }
        )
    return pd.DataFrame(rows)


def _load_buckets(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    level = pd.to_numeric(work["system_inflight_at_start"], errors="coerce")
    bins = [0, 4, 8, 12, 16, 24, np.inf]
    labels = ["1-4", "5-8", "9-12", "13-16", "17-24", "25+"]
    work["inflight_bucket"] = pd.cut(level, bins=bins, labels=labels, include_lowest=True)
    rows: list[dict[str, object]] = []
    for bucket in labels:
        group = work.loc[work["inflight_bucket"].astype("string") == bucket]
        if group.empty:
            continue
        ttft = pd.to_numeric(group["ttft_ms"], errors="coerce").dropna()
        e2e = pd.to_numeric(group["e2e_ms"], errors="coerce").dropna()
        itl = pd.to_numeric(group["itl_ms"], errors="coerce")
        output = pd.to_numeric(group["output_tokens"], errors="coerce")
        valid_decode = (itl > 0) & (output > 1)
        denominator = float((output.loc[valid_decode] - 1).sum())
        weighted_itl = (
            float((itl.loc[valid_decode] * (output.loc[valid_decode] - 1)).sum() / denominator)
            if denominator > 0
            else None
        )
        rows.append(
            {
                "inflight_bucket": bucket,
                "request_count": int(len(group)),
                "ttft_median_ms": _quantile(ttft, 0.5),
                "ttft_p90_ms": _quantile(ttft, 0.9),
                "e2e_median_ms": _quantile(e2e, 0.5),
                "itl_sample_count": int(valid_decode.sum()),
                "weighted_itl_ms": weighted_itl,
                "weighted_decode_tps": 1000.0 / weighted_itl if weighted_itl else None,
                "metric_scope": "ID03 public c8; request-start HTTP overlap bucket, not scheduler running",
            }
        )
    return pd.DataFrame(rows)


def _root_subagent_load_summary(all_rows: pd.DataFrame, id03: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for scope, frame in (("all_c8", all_rows), ("id03_c8", id03)):
        for branch, group in frame.groupby("source_branch_type", dropna=False):
            ttft = pd.to_numeric(group["ttft_ms"], errors="coerce").dropna()
            e2e = pd.to_numeric(group["e2e_ms"], errors="coerce").dropna()
            itl = pd.to_numeric(group["itl_ms"], errors="coerce")
            output = pd.to_numeric(group["output_tokens"], errors="coerce")
            valid = (itl > 0) & (output > 1)
            transitions = float((output.loc[valid] - 1).sum())
            weighted_itl = (
                float((itl.loc[valid] * (output.loc[valid] - 1)).sum() / transitions)
                if transitions > 0
                else None
            )
            inflight = pd.to_numeric(group["system_inflight_at_start"], errors="coerce").dropna()
            rows.append(
                {
                    "scope": scope,
                    "source_branch_type": branch,
                    "request_count": int(len(group)),
                    "ttft_median_ms": _quantile(ttft, 0.5),
                    "ttft_p90_ms": _quantile(ttft, 0.9),
                    "e2e_median_ms": _quantile(e2e, 0.5),
                    "e2e_p90_ms": _quantile(e2e, 0.9),
                    "weighted_itl_ms": weighted_itl,
                    "weighted_decode_tps": 1000.0 / weighted_itl if weighted_itl else None,
                    "system_inflight_at_start_median": _quantile(inflight, 0.5),
                    "system_inflight_at_start_p90": _quantile(inflight, 0.9),
                    "metric_scope": "source branch origin; not backend worker/GPU affinity",
                }
            )
    return pd.DataFrame(rows)


def _parse_frontend_log_archive(path: Path) -> dict[str, pd.DataFrame]:
    completions: list[dict[str, object]] = []
    checkpoints: list[dict[str, object]] = []
    candidates: list[dict[str, object]] = []
    with tarfile.open(path, mode="r:gz") as archive:
        for member in archive:
            if not member.isfile() or not member.name.endswith((".out", ".log")):
                continue
            stream = archive.extractfile(member)
            if stream is None:
                continue
            is_frontend = bool(FRONTEND_MEMBER.search(member.name))
            for line_number, raw in enumerate(stream, start=1):
                line = ANSI_ESCAPE.sub("", raw.decode("utf-8", errors="replace")).strip()
                timestamp = _timestamp_from_line(line)
                if is_frontend:
                    completion = COMPLETION_PATTERN.search(line)
                    if completion:
                        completions.append(
                            {
                                "x_request_id": completion.group("x_request_id"),
                                "router_request_id": completion.group("router_request_id"),
                                "prefill_worker_id": completion.group("prefill_worker_id"),
                                "decode_worker_id": completion.group("decode_worker_id"),
                                "routing_source_file": member.name,
                                "routing_source_line": line_number,
                                "routing_log_timestamp": timestamp,
                            }
                        )
                    checkpoint = QUEUE_CHECKPOINT_PATTERN.search(line)
                    if checkpoint:
                        checkpoints.append(
                            {
                                "router_request_id": checkpoint.group("router_request_id"),
                                "router_queue_wait_checkpoint_ms": float(checkpoint.group("wait_ms")),
                                "queue_checkpoint_source_file": member.name,
                                "queue_checkpoint_source_line": line_number,
                                "queue_checkpoint_timestamp": timestamp,
                            }
                        )
                for match in ARCHIVE_COUNTER_PATTERN.finditer(line):
                    name = match.group("name").lower().replace(" ", "_").replace("-", "_")
                    candidates.append(
                        {
                            "component": "frontend_log",
                            "worker": member.name,
                            "rank": None,
                            "source_file": f"tar:{member.name}",
                            "line_number": line_number,
                            "raw_log_line_pattern": name,
                            "candidate_metric_name": _archive_candidate_name(name),
                            "value": float(match.group("value")),
                            "timestamp": timestamp,
                            "metric_scope_interpretation": _archive_candidate_scope(name),
                            "classification": "Evidence",
                            "source_kind": "server_log_archive",
                        }
                    )
    completion_frame = pd.DataFrame(completions)
    if completion_frame.empty:
        raise SystemExit("no public frontend completion routing rows found in c8 server logs")
    if completion_frame["x_request_id"].duplicated().any():
        raise SystemExit("frontend completion x_request_id is not unique")
    checkpoint_frame = pd.DataFrame(checkpoints)
    if checkpoint_frame.empty:
        checkpoint_summary = pd.DataFrame(
            columns=["router_request_id", "router_queue_wait_checkpoint_ms"]
        )
    else:
        checkpoint_summary = (
            checkpoint_frame.groupby("router_request_id", as_index=False)
            .agg(
                router_queue_wait_checkpoint_count=("router_queue_wait_checkpoint_ms", "size"),
                router_queue_wait_checkpoint_max_ms=("router_queue_wait_checkpoint_ms", "max"),
                router_queue_wait_checkpoint_min_ms=("router_queue_wait_checkpoint_ms", "min"),
                queue_checkpoint_source_file=("queue_checkpoint_source_file", "first"),
                queue_checkpoint_source_line=("queue_checkpoint_source_line", "first"),
            )
            .copy()
        )
    completion_frame = completion_frame.merge(
        checkpoint_summary, on="router_request_id", how="left", validate="one_to_one"
    )
    return {
        "completions": completion_frame,
        "checkpoints": checkpoint_summary,
        "scheduler_candidates": _deduplicate_archive_candidates(candidates),
    }


def _attach_frontend_routing(profile: pd.DataFrame, completion: pd.DataFrame) -> pd.DataFrame:
    result = profile.merge(completion, on="x_request_id", how="left", validate="one_to_one")
    result["routing_match_status"] = np.where(
        result["prefill_worker_id"].notna() & result["decode_worker_id"].notna(), "exact", "unmatched"
    )
    if not result["routing_match_status"].eq("exact").all():
        raise SystemExit("not every profile row has a unique public frontend routing join")
    # Checkpoint rows use the Dynamo router's request ID rather than x_request_id.
    # Completion records bridge the two identities without inventing a queue time.
    return result


def _routing_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for component, field in (("prefill", "prefill_worker_id"), ("decode", "decode_worker_id")):
        for worker, group in frame.groupby(field, dropna=False):
            recon = reconstruct_http_inflight(group)
            summary = summarize_http_inflight(recon)
            rows.append(
                {
                    "component": component,
                    "worker_id": worker,
                    "request_count": int(len(group)),
                    "percentage_of_profiled_requests": float(len(group) / len(frame)),
                    "root_id_count": int(group["root_trace_id"].nunique()),
                    "max_selected_http_interval_overlap": summary.get("max_inflight"),
                    "time_weighted_mean_selected_http_interval_overlap": summary.get(
                        "time_weighted_mean_inflight"
                    ),
                    "routing_join_status": "exact x_request_id -> frontend completion",
                    "scope_note": "Dynamo selected-worker routing. Interval overlap is not backend scheduler running or GPU affinity.",
                    "classification": "Evidence",
                }
            )
    return pd.DataFrame(rows)


def _router_checkpoint_summary(frame: pd.DataFrame) -> pd.DataFrame:
    checkpoints = frame.loc[frame.get("router_queue_wait_checkpoint_max_ms", pd.Series(index=frame.index, dtype=float)).notna()].copy()
    if checkpoints.empty:
        return pd.DataFrame(
            [
                {
                    "profile_request_count_with_checkpoint": 0,
                    "classification": "Unknown",
                    "scope_note": "No exact profile-to-router queue checkpoint join found; not zero queue time.",
                }
            ]
        )
    values = pd.to_numeric(checkpoints["router_queue_wait_checkpoint_max_ms"], errors="coerce")
    return pd.DataFrame(
        [
            {
                "profile_request_count_with_checkpoint": int(len(checkpoints)),
                "checkpoint_event_count": int(
                    pd.to_numeric(checkpoints["router_queue_wait_checkpoint_count"], errors="coerce").sum()
                ),
                "checkpoint_wait_ms_median": _quantile(values, 0.5),
                "checkpoint_wait_ms_p90": _quantile(values, 0.9),
                "checkpoint_wait_ms_max": _quantile(values, 1.0),
                "classification": "Evidence",
                "scope_note": "Dynamo KV-router long-wait refresh checkpoint; not final end-to-end H200 scheduler queue time.",
            }
        ]
    )


def _id03_backend_pressure(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "exact_source_key",
        "source_request_index",
        "source_branch_type",
        "request_start_ns",
        "request_end_ns",
        "ttft_ms",
        "itl_ms",
        "e2e_ms",
        "output_tokens",
        "x_request_id",
        "router_request_id",
        "prefill_worker_id",
        "decode_worker_id",
        "routing_match_status",
        "router_queue_wait_checkpoint_count",
        "router_queue_wait_checkpoint_max_ms",
        "queue_checkpoint_source_file",
        "queue_checkpoint_source_line",
        "system_inflight_at_start",
    ]
    result = _available_columns(frame.sort_values("request_start_ns"), columns)
    result["backend_pressure_scope"] = (
        "Dynamo routing plus HTTP overlap; not request-level SGLang running/waiting or GPU affinity"
    )
    return result


def _metrics_csv_inventory(path: Path) -> pd.DataFrame:
    frame = _read_server_metrics_csv(path)
    selected = frame.loc[frame["Metric"].astype(str).isin(SUMMARY_METRICS)].copy()
    rows: list[dict[str, object]] = []
    for _, item in selected.iterrows():
        metric = str(item["Metric"])
        # Histogram rows use a distinct leading statistical schema while the
        # compact export retains the generic gauge header. Their label fields
        # are shifted in CSV, so JSON is the canonical source for their
        # component/rank and percentile estimates.
        histogram_layout = str(item.get("Type") or "").lower() == "histogram"
        component = "csv_histogram_labels_unparsed" if histogram_layout else _component_from_metric_row(item)
        numeric = None if histogram_layout else _numeric_or_none(item.get("max"))
        rows.append(
            {
                "component": component,
                "worker": None
                if histogram_layout
                else _text_or_none(item.get("worker_id")) or _text_or_none(item.get("Endpoint")),
                "rank": None if histogram_layout else _rank_label(item),
                "source_file": "data/raw/h200_gpu_resident_mtp/conc8/result/9017979109/conc_8/aiperf_artifacts/server_metrics_export.csv",
                "line_number": int(item["_source_line_number"]),
                "raw_log_line_pattern": f"Metric={metric}; Description={_text_or_none(item.get('Description'))}",
                "candidate_metric_name": metric,
                "value": numeric,
                "timestamp": None,
                "metric_scope_interpretation": (
                    "AIPerf histogram row with shifted compact-CSV label schema; use JSON export "
                    "for component/rank and histogram estimates."
                    if histogram_layout
                    else _metric_scope(metric, item)
                ),
                "classification": "Evidence",
                "source_kind": "aiperf_server_metrics_csv_aggregate",
                "unit": _text_or_none(item.get("Unit")),
                "avg": None if histogram_layout else _numeric_or_none(item.get("avg")),
                "min": None if histogram_layout else _numeric_or_none(item.get("min")),
                "max": numeric,
                "p50": None if histogram_layout else _numeric_or_none(item.get("p50")),
                "p90": None if histogram_layout else _numeric_or_none(item.get("p90")),
                "p95": None if histogram_layout else _numeric_or_none(item.get("p95")),
            }
        )
    return pd.DataFrame(rows)


def _extract_scheduler_metrics(path: Path, downsample_seconds: int) -> dict[str, Any]:
    phase_start, phase_end = _profiling_window(path)
    stats_rows: list[dict[str, object]] = []
    timeline_rows: list[dict[str, object]] = []
    errors: list[str] = []
    for metric, payload in _iter_metric_payloads(path, set(JSON_TARGET_METRICS)):
        try:
            series_stats, series_timeline = _payload_rows(metric, payload, phase_start, phase_end)
        except (KeyError, TypeError, ValueError) as error:
            errors.append(f"{metric}: {error}")
            continue
        stats_rows.extend(series_stats)
        if metric in TIMELINE_METRICS:
            timeline_rows.extend(series_timeline)
    return {
        "phase_start_ns": phase_start,
        "phase_end_ns": phase_end,
        "stats_rows": pd.DataFrame(stats_rows),
        "timeline_rows": pd.DataFrame(timeline_rows),
        "errors": errors,
        "downsample_seconds": downsample_seconds,
    }


def _profiling_window(path: Path) -> tuple[int, int]:
    # The summary object is compact and precedes the 3+ GB ``metrics`` map.
    marker = b'\n  "metrics_phase":'
    chunks: list[bytes] = []
    with path.open("rb") as handle:
        while True:
            block = handle.read(64 * 1024)
            if not block:
                raise ValueError("metrics JSON missing metrics_phase marker")
            chunks.append(block)
            joined = b"".join(chunks)
            marker_position = joined.find(marker)
            if marker_position >= 0:
                prefix = joined[:marker_position].rstrip(b",\r\n ") + b"\n}"
                document = json.loads(prefix)
                profiling = document["summary"]["phase_time_ranges"]["profiling"]
                return int(profiling["start_ns"]), int(profiling["end_ns"])


def _iter_metric_payloads(path: Path, targets: set[str]) -> Iterator[tuple[str, dict[str, Any]]]:
    """Stream named top-level metric objects from pretty-printed export JSON.

    AIPerf writes one top-level JSON object per metric inside the ``metrics``
    map.  We inspect only selected objects and parse at most one object at a
    time; this avoids loading the multi-gigabyte export as a Python object.
    """

    prefixes = {f'    "{name}": {{'.encode(): name for name in targets}
    active_name: str | None = None
    active_parts: list[bytes] = []
    brace_depth = 0
    found: set[str] = set()
    with path.open("rb") as handle:
        for line in handle:
            if active_name is None:
                name = prefixes.get(line.rstrip(b"\r\n"))
                if name is None:
                    continue
                active_name = name
                active_parts = [line]
                brace_depth = _brace_delta(line)
                continue
            active_parts.append(line)
            brace_depth += _brace_delta(line)
            if brace_depth != 0:
                continue
            payload_bytes = b"".join(active_parts)
            open_brace = payload_bytes.find(b"{")
            close_brace = payload_bytes.rfind(b"}")
            if open_brace < 0 or close_brace < open_brace:
                raise ValueError(f"unable to isolate JSON object for {active_name}")
            payload = json.loads(payload_bytes[open_brace : close_brace + 1])
            found.add(active_name)
            yield active_name, payload
            active_name = None
            active_parts = []
            brace_depth = 0
            if found == targets:
                return
    missing = sorted(targets - found)
    if missing:
        raise ValueError(f"metrics JSON missing selected keys: {', '.join(missing)}")


def _brace_delta(line: bytes) -> int:
    """Count structural braces in a UTF-8 JSON line without parsing the document."""

    delta = 0
    in_string = False
    escaped = False
    for value in line:
        if in_string:
            if escaped:
                escaped = False
            elif value == 92:  # backslash
                escaped = True
            elif value == 34:  # quote
                in_string = False
            continue
        if value == 34:
            in_string = True
        elif value == 123:
            delta += 1
        elif value == 125:
            delta -= 1
    return delta


def _payload_rows(
    metric: str,
    payload: dict[str, Any],
    profile_start_ns: int,
    profile_end_ns: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    stats_rows: list[dict[str, object]] = []
    timeline_rows: list[dict[str, object]] = []
    description = str(payload.get("description") or "")
    for series_index, series in enumerate(payload.get("series") or []):
        labels = series.get("labels") or {}
        endpoint = str(series.get("endpoint_url") or "")
        component = _scheduler_component(labels)
        base = {
            "metric": metric,
            "description": description,
            "component": component,
            "endpoint_url": endpoint,
            "worker_id": labels.get("worker_id"),
            "dp_rank": labels.get("dp_rank"),
            "tp_rank": labels.get("tp_rank"),
            "series_index": series_index,
            "series_scope": _scheduler_series_scope(component, metric),
            "classification": "Evidence",
        }
        stats = series.get("stats") or {}
        stats_rows.append(
            {
                **base,
                "sample_count": _numeric_or_none(stats.get("count")),
                "avg": _numeric_or_none(stats.get("avg")),
                "min": _numeric_or_none(stats.get("min")),
                "max": _numeric_or_none(stats.get("max")),
                # Gauge series use p* while histogram series use p*_estimate.
                # A missing key remains null; it is never interpreted as zero.
                "p50": _first_numeric(stats, ("p50", "p50_estimate")),
                "p90": _first_numeric(stats, ("p90", "p90_estimate")),
                "p95": _first_numeric(stats, ("p95", "p95_estimate")),
                "p99": _first_numeric(stats, ("p99", "p99_estimate")),
                "source_file": "data/raw/h200_gpu_resident_mtp/conc8/result/9017979109/conc_8/aiperf_artifacts/server_metrics_export.json",
                "profile_window_start_ns": profile_start_ns,
                "profile_window_end_ns": profile_end_ns,
            }
        )
        for timeslice in series.get("timeslices") or []:
            start = _numeric_or_none(timeslice.get("start_ns"))
            end = _numeric_or_none(timeslice.get("end_ns"))
            if start is None or end is None or end <= profile_start_ns or start >= profile_end_ns:
                continue
            value = _first_numeric(timeslice, ("avg", "value", "last", "max"))
            if value is None:
                continue
            timeline_rows.append(
                {
                    **base,
                    "timeslice_start_ns": max(int(start), profile_start_ns),
                    "timeslice_end_ns": min(int(end), profile_end_ns),
                    "timeslice_value": value,
                    "timeslice_min": _numeric_or_none(timeslice.get("min")),
                    "timeslice_max": _numeric_or_none(timeslice.get("max")),
                }
            )
    return stats_rows, timeline_rows


def _write_scheduler_outputs(processed: Path, scheduler: dict[str, Any]) -> None:
    stats = scheduler["stats_rows"].copy()
    timeline = scheduler["timeline_rows"].copy()
    if stats.empty:
        return
    for component, prefix in (("prefill", "c8_prefill_scheduler"), ("decode", "c8_decode_scheduler")):
        component_stats = stats.loc[stats["component"] == component].copy()
        if component_stats.empty:
            continue
        component_timeline = timeline.loc[timeline["component"] == component].copy()
        _scheduler_summary(component_stats, component_timeline).to_csv(
            processed / f"{prefix}_summary.csv", index=False
        )
        if component_timeline.empty:
            continue
        # Full per-rank timeslices remain local (Parquet is ignored); Git gets
        # a 10-second reviewable range across rank-export series.
        component_timeline.to_parquet(processed / f"{prefix}_timeline_full.parquet", index=False)
        _downsample_scheduler_timeline(
            component_timeline,
            int(scheduler["phase_start_ns"]),
            int(scheduler["downsample_seconds"]),
        ).to_csv(processed / f"{prefix}_timeline.csv", index=False)


def _scheduler_summary(stats: pd.DataFrame, timeline: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    keys = ["component", "endpoint_url", "worker_id", "metric"]
    for values, group in stats.groupby(keys, dropna=False):
        component, endpoint, worker, metric = values
        samples = timeline.loc[
            (timeline["component"] == component)
            & (timeline["endpoint_url"] == endpoint)
            & (timeline["worker_id"] == worker)
            & (timeline["metric"] == metric)
        ].copy()
        if not samples.empty:
            per_rank = (
                samples.groupby("series_index", dropna=False)["timeslice_value"]
                .agg(
                    timeslice_sample_count="size",
                    min="min",
                    max="max",
                    avg="mean",
                    p50=lambda value: value.quantile(0.50),
                    p90=lambda value: value.quantile(0.90),
                    p95=lambda value: value.quantile(0.95),
                )
                .reset_index(drop=True)
            )
            summary_source = (
                "profiling-window 1-second AIPerf timeslice samples; per-rank series "
                "are summarized but never summed"
            )
        else:
            per_rank = group[["min", "max", "avg", "p50", "p90", "p95"]].copy()
            per_rank["timeslice_sample_count"] = pd.NA
            summary_source = (
                "aggregate AIPerf histogram/export statistics; no usable gauge timeslice value "
                "for this metric"
            )
        rows.append(
            {
                "component": component,
                "endpoint_url": endpoint,
                "worker_id": worker,
                "metric": metric,
                "rank_series_count": int(len(per_rank)),
                "timeslice_sample_count_total": _series_aggregate(
                    per_rank["timeslice_sample_count"], "sum"
                ),
                "observed_min_across_rank_series": _series_aggregate(per_rank["min"], "min"),
                "observed_max_across_rank_series": _series_aggregate(per_rank["max"], "max"),
                "rank_series_median_avg": _series_aggregate(per_rank["avg"], "median"),
                "rank_series_median_p50": _series_aggregate(per_rank["p50"], "median"),
                "rank_series_median_p90": _series_aggregate(per_rank["p90"], "median"),
                "rank_series_median_p95": _series_aggregate(per_rank["p95"], "median"),
                "rank_series_min_of_max": _series_aggregate(per_rank["max"], "min"),
                "rank_series_max_of_max": _series_aggregate(per_rank["max"], "max"),
                "description": _first_text(group, "description"),
                "scope_note": _scheduler_series_scope(str(component), str(metric)),
                "summary_sampling": summary_source,
                "classification": "Evidence",
            }
        )
    return pd.DataFrame(rows).sort_values(["metric", "endpoint_url"]).reset_index(drop=True)


def _downsample_scheduler_timeline(
    timeline: pd.DataFrame, profile_start_ns: int, downsample_seconds: int
) -> pd.DataFrame:
    work = timeline.copy()
    bucket_ns = downsample_seconds * 1_000_000_000
    work["bucket_start_ns"] = (
        ((pd.to_numeric(work["timeslice_start_ns"], errors="coerce") - profile_start_ns) // bucket_ns)
        * bucket_ns
        + profile_start_ns
    ).astype("int64")
    work["bucket_end_ns"] = work["bucket_start_ns"] + bucket_ns
    keys = ["component", "endpoint_url", "worker_id", "metric", "bucket_start_ns", "bucket_end_ns"]
    rows: list[dict[str, object]] = []
    for values, group in work.groupby(keys, dropna=False):
        component, endpoint, worker, metric, start, end = values
        values_numeric = pd.to_numeric(group["timeslice_value"], errors="coerce").dropna()
        rows.append(
            {
                "component": component,
                "endpoint_url": endpoint,
                "worker_id": worker,
                "metric": metric,
                "bucket_start_ns": int(start),
                "bucket_end_ns": int(end),
                "timeslice_row_count": int(len(group)),
                "rank_series_count": int(group["series_index"].nunique()),
                "rank_series_value_min": _quantile(values_numeric, 0.0),
                "rank_series_value_median": _quantile(values_numeric, 0.5),
                "rank_series_value_max": _quantile(values_numeric, 1.0),
                "scope_note": "10-second downsample across public rank-export series; values are not summed into a worker/global count.",
                "classification": "Evidence",
            }
        )
    return pd.DataFrame(rows).sort_values(["metric", "endpoint_url", "bucket_start_ns"])


def _empty_scheduler_result() -> dict[str, Any]:
    return {
        "phase_start_ns": None,
        "phase_end_ns": None,
        "stats_rows": pd.DataFrame(),
        "timeline_rows": pd.DataFrame(),
        "errors": ["server_metrics_export.json not parsed"],
        "downsample_seconds": None,
    }


def _concurrency_reconstruction_rows(
    *,
    http_summary: dict[str, Any],
    scheduler: dict[str, Any],
    routed_profile: pd.DataFrame,
    frontend: dict[str, pd.DataFrame],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    def add(metric: str, value: object, status: str, scope: str, notes: str) -> None:
        rows.append(
            {
                "metric": metric,
                "value": value,
                "status": status,
                "evidence_scope": scope,
                "notes": notes,
            }
        )

    add(
        "agentx_root_concurrency_configured",
        8,
        "Evidence",
        "AIPerf c8 command / trajectory lanes",
        "Configured root-trajectory lane count; not HTTP or scheduler running count.",
    )
    for field in (
        "max_inflight",
        "time_weighted_mean_inflight",
        "time_weighted_p50_inflight",
        "time_weighted_p75_inflight",
        "time_weighted_p90_inflight",
        "time_weighted_p95_inflight",
        "time_weighted_p99_inflight",
        "max_root_inflight",
        "max_subagent_inflight",
        "time_weighted_mean_root_inflight",
        "time_weighted_mean_subagent_inflight",
        "fraction_time_inflight_ge_8",
        "fraction_time_inflight_ge_12",
        "fraction_time_inflight_ge_16",
        "fraction_time_inflight_ge_24",
        "fraction_time_inflight_ge_32",
    ):
        add(
            f"http_{field}",
            http_summary.get(field),
            "Evidence",
            "957 successful profiling request [start,end) intervals",
            "HTTP/client-observed overlap; never interpreted as scheduler running or GPU concurrency.",
        )
    add(
        "prefill_configured_max_running",
        32,
        "Evidence",
        "public startup ServerArgs / runtime evidence",
        "Configured capacity, not observed runtime running-request count.",
    )
    add(
        "decode_configured_max_running",
        200,
        "Evidence",
        "public startup ServerArgs / runtime evidence",
        "Configured capacity, not observed runtime running-request count.",
    )
    stats = scheduler["stats_rows"]
    timeslices = scheduler["timeline_rows"]
    for component in ("prefill", "decode"):
        component_stats = stats.loc[stats.get("component", pd.Series(dtype="string")) == component]
        for metric, label in (
            ("sglang:num_running_reqs", "running"),
            ("sglang:num_queue_reqs", "waiting"),
        ):
            selected = component_stats.loc[
                component_stats.get("metric", pd.Series(dtype="string")) == metric
            ]
            selected_timeslices = timeslices.loc[
                (timeslices.get("component", pd.Series(dtype="string")) == component)
                & (timeslices.get("metric", pd.Series(dtype="string")) == metric)
            ]
            if selected.empty or selected_timeslices.empty:
                add(
                    f"{component}_observed_max_{label}",
                    "Unknown",
                    "Unknown",
                    "profiling-window public metrics timeslice unavailable or metric absent",
                    "Missing profiling-window evidence is not zero; configured limit remains separate.",
                )
            else:
                value = _series_aggregate(selected_timeslices["timeslice_value"], "max")
                add(
                    f"{component}_observed_max_{label}",
                    value,
                    "Evidence",
                    "AIPerf profiling-window 1-second server-metrics timeslices; maximum across endpoint/rank-export series",
                    "Rank-export series are not summed to a worker or cluster total; this is not a global scheduler total.",
                )
    checkpoints = _router_checkpoint_summary(routed_profile)
    checkpoint_row = checkpoints.iloc[0].to_dict()
    add(
        "router_queue_wait_checkpoint_profile_request_count",
        checkpoint_row.get("profile_request_count_with_checkpoint"),
        checkpoint_row.get("classification", "Unknown"),
        "exact frontend router request ID -> x_request_id -> profiling row join",
        "Long-wait refresh checkpoints are not final scheduler queue time.",
    )
    add(
        "router_queue_wait_checkpoint_max_ms",
        checkpoint_row.get("checkpoint_wait_ms_max"),
        checkpoint_row.get("classification", "Unknown"),
        "exact frontend router request ID -> x_request_id -> profiling row join",
        "Long-wait refresh checkpoint, not full per-request queue decomposition.",
    )
    add(
        "h200_explicit_queue_time",
        "aggregate_scheduler_histogram_and_router_checkpoints_available",
        "Evidence",
        "SGLang queue_time_seconds rank-series histogram plus exact long-wait router checkpoint events",
        "No complete request-level scheduler lifecycle join exists; TTFT cannot be decomposed into queue versus execution.",
    )
    add(
        "routing_exact_profile_join_count",
        int(routed_profile["routing_match_status"].eq("exact").sum()),
        "Evidence",
        "raw profile x_request_id -> frontend request-completed log",
        "Dynamo worker routing only, not GPU affinity.",
    )
    return rows


def _build_figures(
    figures: Path,
    timeline: pd.DataFrame,
    id03: pd.DataFrame,
    scheduler: dict[str, Any],
) -> None:
    _http_timeline_plot(timeline, figures / "c8_http_inflight_timeline.png")
    _id03_scatter_plot(id03, figures / "id03_ttft_vs_system_inflight.png")
    if not scheduler["timeline_rows"].empty:
        _scheduler_timeline_plot(
            scheduler["timeline_rows"], figures / "c8_scheduler_running_waiting.png"
        )


def _http_timeline_plot(timeline: pd.DataFrame, path: Path) -> None:
    fig, axis = plt.subplots(figsize=(10, 4.8))
    if not timeline.empty:
        data = timeline.sort_values(["timestamp_ns", "event_order_at_timestamp"]).copy()
        origin = int(data["timestamp_ns"].min())
        x = (pd.to_numeric(data["timestamp_ns"], errors="coerce") - origin) / 1e9
        axis.step(x, data["inflight_after_event"], where="post", label="HTTP in-flight")
        axis.step(x, data["root_inflight"], where="post", label="root-origin")
        axis.step(x, data["subagent_inflight"], where="post", label="subagent-origin")
        axis.legend()
    else:
        axis.text(0.5, 0.5, "No valid HTTP intervals", ha="center", va="center")
    axis.set_xlabel("Seconds from first profiling request interval event")
    axis.set_ylabel("Concurrent HTTP request intervals")
    axis.set_title("Public H200 c8: client-observed HTTP overlap (not scheduler running)")
    axis.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _id03_scatter_plot(frame: pd.DataFrame, path: Path) -> None:
    fig, axis = plt.subplots(figsize=(7.5, 4.8))
    if not frame.empty:
        data = frame[["system_inflight_at_start", "ttft_ms", "source_branch_type"]].dropna()
        for branch, group in data.groupby("source_branch_type", dropna=False):
            axis.scatter(
                group["system_inflight_at_start"],
                group["ttft_ms"],
                s=25,
                alpha=0.8,
                label=f"{branch} (n={len(group)})",
            )
        axis.legend(title="source branch origin")
    else:
        axis.text(0.5, 0.5, "No ID03 rows", ha="center", va="center")
    axis.set_xlabel("System HTTP in-flight at request start (includes request)")
    axis.set_ylabel("Observed H200 replay TTFT (ms)")
    axis.set_title("ID03 c8: TTFT vs client-observed offered load")
    axis.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _scheduler_timeline_plot(frame: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    data = frame.loc[frame["metric"].isin(["sglang:num_running_reqs", "sglang:num_queue_reqs"])]
    if data.empty:
        for axis in axes:
            axis.text(0.5, 0.5, "No observed scheduler timeslices", ha="center", va="center")
    else:
        origin = int(data["timeslice_start_ns"].min())
        for axis, component in zip(axes, ("prefill", "decode"), strict=True):
            subset = data.loc[data["component"] == component]
            for (endpoint, metric), group in subset.groupby(["endpoint_url", "metric"], dropna=False):
                grouped = group.groupby("timeslice_start_ns", as_index=False)["timeslice_value"].median()
                x = (grouped["timeslice_start_ns"] - origin) / 1e9
                metric_label = "running" if metric.endswith("running_reqs") else "queue"
                axis.plot(x, grouped["timeslice_value"], label=f"{component} {endpoint} {metric_label}")
            if not subset.empty:
                axis.legend(fontsize=7, ncol=2)
            axis.set_ylabel("Rank-series median gauge")
            axis.set_title(f"{component.title()} SGLang gauge export (not summed across ranks)")
            axis.grid(alpha=0.25)
    axes[-1].set_xlabel("Seconds from first selected scheduler timeslice")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _write_run_metadata(
    processed: Path,
    all_c8: pd.DataFrame,
    profile: pd.DataFrame,
    frontend: dict[str, pd.DataFrame],
    scheduler: dict[str, Any],
) -> None:
    pd.DataFrame(
        [
            {
                "all_c8_raw_profile_rows": int(len(all_c8)),
                "successful_profiling_rows": int(len(profile)),
                "frontend_completion_rows": int(len(frontend["completions"])),
                "scheduler_json_metrics_parsed": int(
                    scheduler["stats_rows"].get("metric", pd.Series(dtype="string")).nunique()
                ),
                "scheduler_json_parse_errors": "; ".join(scheduler["errors"]),
                "classification": "Evidence" if scheduler["stats_rows"].shape[0] else "Unknown",
            }
        ]
    ).to_csv(processed / "c8_concurrency_reconstruction_run_metadata.csv", index=False)


def _available_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = frame.copy()
    for column in columns:
        if column not in result:
            result[column] = pd.NA
    return result[columns].copy()


def _quantile(values: pd.Series, quantile: float) -> float | None:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    return float(numeric.quantile(quantile)) if not numeric.empty else None


def _numeric_or_none(value: object) -> float | int | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return int(number) if number.is_integer() else number


def _first_numeric(mapping: dict[str, Any], fields: Iterable[str]) -> float | int | None:
    for field in fields:
        value = _numeric_or_none(mapping.get(field))
        if value is not None:
            return value
    return None


def _text_or_none(value: object) -> str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value)
    return text if text and text.lower() != "nan" else None


def _first_text(frame: pd.DataFrame, column: str) -> str | None:
    if column not in frame:
        return None
    values = frame[column].dropna().astype(str)
    return values.iloc[0] if not values.empty else None


def _series_aggregate(values: pd.Series, method: str) -> float | None:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return None
    if method == "min":
        return float(numeric.min())
    if method == "max":
        return float(numeric.max())
    if method == "median":
        return float(numeric.median())
    if method == "sum":
        return float(numeric.sum())
    raise ValueError(f"unsupported aggregate: {method}")


def _timestamp_from_line(line: str) -> str | None:
    match = TIMESTAMP_PATTERN.search(line)
    return match.group("timestamp") if match else None


def _archive_candidate_name(name: str) -> str:
    if name.startswith("max_"):
        return "configured_max_running_requests" if "running" in name else "configured_max_waiting_requests"
    return "running_requests" if "running" in name else "waiting_or_queue_requests"


def _archive_candidate_scope(name: str) -> str:
    if name.startswith("max_"):
        return "configured capacity from log; not observed runtime scheduler count"
    return "explicit runtime log counter candidate; component/scheduler scope requires its source line"


def _deduplicate_archive_candidates(rows: list[dict[str, object]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(
            columns=[
                "component",
                "worker",
                "rank",
                "source_file",
                "line_number",
                "raw_log_line_pattern",
                "candidate_metric_name",
                "value",
                "timestamp",
                "metric_scope_interpretation",
                "classification",
                "source_kind",
            ]
        )
    frame = pd.DataFrame(rows)
    return frame.drop_duplicates(
        subset=["source_file", "candidate_metric_name", "value", "raw_log_line_pattern"]
    ).reset_index(drop=True)


def _read_server_metrics_csv(path: Path) -> pd.DataFrame:
    """Read AIPerf CSV while preserving histogram descriptions with commas.

    Histogram bucket text is appended after the final Description field without
    CSV quoting.  ``pandas.read_csv`` therefore infers a shifted index for the
    entire file.  This small reader joins surplus trailing cells back into the
    description and retains the physical source line for the inventory.
    """

    with path.open(encoding="utf-8", newline="") as handle:
        header: list[str] | None = None
        header_line: int | None = None
        for line_number, line in enumerate(handle, start=1):
            if line.startswith("Endpoint,"):
                header = next(csv.reader([line]))
                header_line = line_number
                break
        if header is None or header_line is None:
            raise ValueError("server metrics CSV header not found")
        rows: list[dict[str, object]] = []
        for line_number, row in enumerate(csv.reader(handle), start=header_line + 1):
            if not row:
                continue
            if len(row) < len(header):
                row = [*row, *([""] * (len(header) - len(row)))]
            elif len(row) > len(header):
                row = [*row[: len(header) - 1], ",".join(row[len(header) - 1 :])]
            item = dict(zip(header, row, strict=True))
            item["_source_line_number"] = line_number
            rows.append(item)
    return pd.DataFrame(rows)


def _component_from_metric_row(item: pd.Series) -> str:
    direct = _text_or_none(item.get("dynamo_component"))
    if direct:
        return "decode" if direct == "backend" else direct
    worker_type = _text_or_none(item.get("worker_type"))
    if worker_type:
        return worker_type
    metric = str(item.get("Metric") or "")
    if metric.startswith("dynamo_frontend") or metric.startswith("dynamo_request_plane"):
        return "frontend"
    return "unlabeled"


def _rank_label(item: pd.Series) -> str | None:
    values = []
    for name in ("dp_rank", "tp_rank", "pp_rank"):
        value = _text_or_none(item.get(name))
        if value is not None:
            values.append(f"{name}={value}")
    return ";".join(values) if values else None


def _metric_scope(metric: str, item: pd.Series) -> str:
    description = _text_or_none(item.get("Description")) or ""
    if metric == "sglang:num_running_reqs":
        return "explicit SGLang running-request gauge; rank-export scope, not summed"
    if metric == "sglang:num_queue_reqs":
        return "explicit SGLang queue/waiting-request gauge; rank-export scope, not summed"
    if metric == "sglang:queue_time_seconds":
        return "explicit SGLang aggregate queue-time histogram; not request-correlated to profile TTFT"
    if metric.startswith("dynamo_frontend") or metric.startswith("dynamo_request_plane"):
        return "Dynamo frontend/request-plane metric; separate from profile interval overlap and SGLang running"
    if "capacity" in description.lower() or "max_num" in metric:
        return "configured capacity metric; not observed scheduler running"
    return description or "public AIPerf server-metrics aggregate; retain component/rank scope"


def _scheduler_component(labels: dict[str, Any]) -> str:
    component = str(labels.get("dynamo_component") or "")
    if component == "backend":
        return "decode"
    if component == "prefill":
        return "prefill"
    return component or "unlabeled"


def _scheduler_series_scope(component: str, metric: str) -> str:
    base = "AIPerf public server-metrics profiling export; explicit SGLang metric"
    if component in {"prefill", "decode"}:
        return (
            f"{base}; {component} endpoint/rank-series scope. Values across rank exports are not summed "
            "into a worker or cluster count."
        )
    return f"{base}; component scope unavailable."


if __name__ == "__main__":
    raise SystemExit(main())
