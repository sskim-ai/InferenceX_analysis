#!/usr/bin/env python3
# ruff: noqa: I001
"""Reconstruct scope-safe public c8 SGLang worker/cluster scheduler evidence.

This script streams only selected metric objects from the multi-gigabyte
public AIPerf JSON export.  It does not add TP/DP rank values unless both the
raw time-series behaviour and the SGLang runtime topology support the exact
operation.  In particular, CP8 prefill remains a rank-envelope observation,
not an asserted unique-worker request count.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))
if str(REPOSITORY_ROOT / "scripts/h200_gpu_resident_mtp") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "scripts/h200_gpu_resident_mtp"))

from reconstruct_c8_concurrency import (  # noqa: E402
    _iter_metric_payloads,
    _profiling_window,
)

from h200_agentx_analysis.scheduler_cluster_reconstruction import (  # noqa: E402
    aggregate_rank_shards,
    dynamo_sglang_crosscheck,
    intersect_worker_intervals,
    occupancy_bin_scope_note,
    prefill_duplicate_verdict,
    rank_envelope_timeseries,
    rank_series_validation,
    select_numeric_timeslice_field,
    summarize_worker_timeseries,
)


STUDY_ROOT_DEFAULT = REPOSITORY_ROOT / "studies/h200_gpu_resident_mtp"
RAW_ROOT_DEFAULT = REPOSITORY_ROOT / "data/raw/h200_gpu_resident_mtp"

PREFILL_WORKERS = ("694d9fdfb4d8ee15", "694d9fdfb4d8ee13")
DECODE_WORKERS = ("694d9fdfb4d8ee1b", "694d9fdfb4d8ee18")
CURRENT_TIMESLICE_FIELD_PRIORITY = ("avg", "value", "last", "max")
DECODE_OCCUPANCY_SENSITIVITY_FIELDS = ("avg", "last", "max")

SGLANG_METRICS = (
    "sglang:num_running_reqs",
    "sglang:num_queue_reqs",
    "sglang:num_prefill_bootstrap_queue_reqs",
    "sglang:num_prefill_inflight_queue_reqs",
    "sglang:num_decode_prealloc_queue_reqs",
    "sglang:num_decode_transfer_queue_reqs",
    "sglang:token_usage",
    "sglang:full_token_usage",
)
DYNAMO_METRICS = (
    "dynamo_component_inflight_requests",
    "dynamo_request_plane_inflight_requests",
    "dynamo_frontend_inflight_requests",
    "dynamo_frontend_queued_requests",
    "dynamo_frontend_router_queue_pending_requests",
    "dynamo_frontend_router_queue_pending_isl_tokens",
)
PREFILL_METRIC_COLUMNS = {
    "sglang:num_running_reqs": "running_requests",
    "sglang:num_queue_reqs": "waiting_requests",
    "sglang:num_prefill_bootstrap_queue_reqs": "prefill_bootstrap_queue",
    "sglang:num_prefill_inflight_queue_reqs": "prefill_inflight_queue",
}
DECODE_METRIC_COLUMNS = {
    "sglang:num_running_reqs": "running_requests",
    "sglang:num_queue_reqs": "waiting_requests",
    "sglang:num_decode_prealloc_queue_reqs": "decode_prealloc_queue_requests",
    "sglang:num_decode_transfer_queue_reqs": "decode_transfer_queue_requests",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-root", type=Path, default=STUDY_ROOT_DEFAULT)
    parser.add_argument("--raw-root", type=Path, default=RAW_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    processed = args.study_root / "processed"
    figures = args.study_root / "figures"
    manifests = args.study_root / "manifests"
    processed.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    manifests.mkdir(parents=True, exist_ok=True)
    metrics_json = _metrics_json_path(args.raw_root)
    phase_start_ns, phase_end_ns = _profiling_window(metrics_json)
    raw = _extract_selected_timeseries(metrics_json, phase_start_ns, phase_end_ns)
    sglang = raw.loc[raw["metric"].astype("string").isin(SGLANG_METRICS)].copy()
    dynamo = raw.loc[raw["metric"].astype("string").isin(DYNAMO_METRICS)].copy()
    if sglang.empty or dynamo.empty:
        raise SystemExit("selected public c8 server-metric timeseries are missing")

    source_semantics = _source_semantics_rows()
    source_semantics.to_csv(processed / "c8_scheduler_source_semantics.csv", index=False)
    (manifests / "sglang_v0516_scheduler_metric_semantics.json").write_text(
        json.dumps(source_semantics.to_dict(orient="records"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    prefill = sglang.loc[sglang["component"] == "prefill"].copy()
    decode = sglang.loc[sglang["component"] == "decode"].copy()
    decode_running = _decode_running_timeslices(raw)
    field_semantics = _decode_timeslice_field_semantics(decode_running)
    field_semantics.to_csv(processed / "c8_decode_timeslice_field_semantics.csv", index=False)
    current_timeslice_field = _selected_field_label(field_semantics)
    prefill_validation = rank_series_validation(
        prefill.loc[prefill["metric"].astype("string").isin(PREFILL_METRIC_COLUMNS)],
        rank_column="tp_rank",
    )
    decode_validation = rank_series_validation(
        decode.loc[decode["metric"].astype("string").isin(DECODE_METRIC_COLUMNS)],
        rank_column="dp_rank",
    )
    rank_validation = pd.concat([prefill_validation, decode_validation], ignore_index=True)
    rank_validation = _attach_rank_semantic_verdicts(rank_validation)
    rank_validation.to_csv(processed / "c8_scheduler_rank_semantics_validation.csv", index=False)
    rank_validation.loc[
        rank_validation["component"].astype("string") == "decode"
    ].to_csv(processed / "c8_decode_rank_scheduler_summary.csv", index=False)

    # CP8 prefill ranks report local scheduler/batch views.  Their nearly equal
    # values refute 8x summation, but source code and raw metrics do not prove
    # the unique logical request union required for a worker total.
    prefill_verdict = prefill_duplicate_verdict(
        prefill_validation,
        required_metrics=(
            "sglang:num_running_reqs",
            "sglang:num_queue_reqs",
            "sglang:num_prefill_bootstrap_queue_reqs",
            "sglang:num_prefill_inflight_queue_reqs",
        ),
        source_semantics_verified=False,
    )
    prefill_envelope = rank_envelope_timeseries(
        prefill,
        rank_column="tp_rank",
        metric_to_column=PREFILL_METRIC_COLUMNS,
        expected_rank_count=8,
    )
    prefill_summary = _prefill_envelope_summary(prefill_envelope, prefill_verdict)
    prefill_summary.to_csv(processed / "c8_prefill_worker_scheduler_summary.csv", index=False)
    _reviewable_prefill_timeseries(prefill_envelope).to_csv(
        processed / "c8_prefill_worker_scheduler_timeseries.csv", index=False
    )
    _unknown_prefill_cluster_summary(prefill_verdict).to_csv(
        processed / "c8_prefill_cluster_scheduler_summary.csv", index=False
    )

    # Decode DP attention has one attention-TP rank per DP shard for TP8/DP8.
    # SGLang's DP controller tracks scheduler load per DP rank and dispatches a
    # request to one selected rank.  Complete raw rank grids can therefore be
    # summed into a decode-worker scheduler count.
    decode_workers = aggregate_rank_shards(
        decode,
        rank_column="dp_rank",
        metric_to_column=DECODE_METRIC_COLUMNS,
        expected_rank_count=8,
        accepted_workers=DECODE_WORKERS,
    )
    decode_summary = summarize_worker_timeseries(
        decode_workers,
        value_columns=(
            "running_requests",
            "waiting_requests",
            "decode_prealloc_queue_requests",
            "decode_transfer_queue_requests",
        ),
    )
    decode_waiting_all_zero = bool(
        not decode.empty
        and (
            pd.to_numeric(
                decode.loc[
                    decode["metric"].astype("string") == "sglang:num_queue_reqs", "timeslice_value"
                ],
                errors="coerce",
            ).fillna(np.nan)
            == 0
        ).all()
    )
    decode_summary = _decorate_decode_summary(decode_summary, decode_waiting_all_zero)
    decode_summary.to_csv(processed / "c8_decode_worker_scheduler_summary.csv", index=False)
    decode_cluster, decode_cluster_summary = intersect_worker_intervals(
        decode_workers,
        component="decode",
        worker_ids=DECODE_WORKERS,
        value_columns=(
            "running_requests",
            "waiting_requests",
            "decode_prealloc_queue_requests",
            "decode_transfer_queue_requests",
        ),
        profile_duration_ns=phase_end_ns - phase_start_ns,
    )
    decode_cluster_summary = _decorate_decode_cluster_summary(
        decode_cluster_summary,
        decode_waiting_all_zero,
        current_timeslice_field=current_timeslice_field,
    )
    decode_cluster_summary.to_csv(processed / "c8_decode_cluster_scheduler_summary.csv", index=False)
    alignment_summary = _decode_timeslice_alignment_summary(decode_cluster)
    alignment_summary.to_csv(processed / "c8_decode_timeslice_alignment_summary.csv", index=False)
    field_sensitivity = _decode_cluster_field_sensitivity(
        decode_running, profile_duration_ns=phase_end_ns - phase_start_ns
    )
    field_sensitivity.to_csv(processed / "c8_decode_cluster_field_sensitivity.csv", index=False)
    _reviewable_decode_timeseries(decode_workers, decode_cluster, phase_start_ns).to_csv(
        processed / "c8_decode_worker_scheduler_timeseries.csv", index=False
    )
    _reviewable_cluster_timeseries(decode_cluster).to_csv(
        processed / "c8_cluster_scheduler_timeseries.csv", index=False
    )

    crosscheck = _dynamo_crosschecks(
        dynamo=dynamo,
        decode_workers=decode_workers,
        prefill=prefill,
        phase_start_ns=phase_start_ns,
    )
    crosscheck.to_csv(processed / "c8_dynamo_sglang_concurrency_crosscheck.csv", index=False)

    http = _read_single_row(processed / "c8_http_concurrency_summary.csv")
    cluster_summary = _primary_cluster_summary(
        http=http,
        prefill_summary=prefill_summary,
        decode_summary=decode_summary,
        decode_cluster_summary=decode_cluster_summary,
        prefill_verdict=prefill_verdict,
        decode_waiting_all_zero=decode_waiting_all_zero,
        current_timeslice_field=current_timeslice_field,
    )
    cluster_summary.to_csv(processed / "c8_cluster_scheduler_reconstruction.csv", index=False)
    _build_figures(
        figures=figures,
        prefill_envelope=prefill_envelope,
        decode_cluster=decode_cluster,
        dynamo=dynamo,
        phase_start_ns=phase_start_ns,
    )
    print(
        json.dumps(
            {
                "status": "completed",
                "profiling_window_start_ns": phase_start_ns,
                "profiling_window_end_ns": phase_end_ns,
                "prefill_verdicts": prefill_verdict.to_dict(orient="records"),
                "decode_cluster_rows": int(len(decode_cluster)),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _metrics_json_path(raw_root: Path) -> Path:
    path = raw_root / "conc8/result/9017979109/conc_8/aiperf_artifacts/server_metrics_export.json"
    if not path.exists():
        raise SystemExit(f"missing public c8 metrics export: {path}")
    return path


def _extract_selected_timeseries(
    path: Path, profile_start_ns: int, profile_end_ns: int
) -> pd.DataFrame:
    """Stream selected raw metric objects and retain profiling-window 1-s bins."""

    rows: list[dict[str, object]] = []
    targets = set(SGLANG_METRICS) | set(DYNAMO_METRICS)
    for metric, payload in _iter_metric_payloads(path, targets):
        description = str(payload.get("description") or "")
        for series_index, series in enumerate(payload.get("series") or []):
            labels = series.get("labels") or {}
            component = _component(metric, labels)
            for timeslice in series.get("timeslices") or []:
                start = _integer_or_none(timeslice.get("start_ns"))
                end = _integer_or_none(timeslice.get("end_ns"))
                if start is None or end is None or end <= profile_start_ns or start >= profile_end_ns:
                    continue
                value, selected_field = select_numeric_timeslice_field(
                    timeslice, CURRENT_TIMESLICE_FIELD_PRIORITY
                )
                rows.append(
                    {
                        "metric": metric,
                        "description": description,
                        "component": component,
                        "endpoint_url": str(series.get("endpoint_url") or ""),
                        "worker_id": labels.get("worker_id"),
                        "dynamo_component": labels.get("dynamo_component"),
                        "dynamo_endpoint": labels.get("dynamo_endpoint"),
                        "worker_type": labels.get("worker_type"),
                        "engine_type": labels.get("engine_type"),
                        "dp_rank": labels.get("dp_rank"),
                        "tp_rank": labels.get("tp_rank"),
                        "series_index": series_index,
                        "timeslice_start_ns": max(start, profile_start_ns),
                        "timeslice_end_ns": min(end, profile_end_ns),
                        "timeslice_value": value,
                        "timeslice_selected_field": selected_field,
                        "timeslice_avg": _raw_numeric_field(timeslice, "avg"),
                        "timeslice_last": _raw_numeric_field(timeslice, "last"),
                        "timeslice_max": _raw_numeric_field(timeslice, "max"),
                        "timeslice_min": _raw_numeric_field(timeslice, "min"),
                        "timeslice_explicit_value": _raw_numeric_field(timeslice, "value"),
                        "timeslice_field_keys": json.dumps(sorted(timeslice.keys())),
                    }
                )
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    result["worker_id"] = result["worker_id"].astype("string")
    result["dp_rank"] = result["dp_rank"].astype("string")
    result["tp_rank"] = result["tp_rank"].astype("string")
    return result


def _component(metric: str, labels: dict[str, Any]) -> str:
    dynamo_component = str(labels.get("dynamo_component") or "")
    if dynamo_component == "backend":
        return "decode"
    if dynamo_component == "prefill":
        return "prefill"
    worker_type = str(labels.get("worker_type") or "")
    if worker_type:
        return worker_type
    if metric.startswith("dynamo_frontend") or metric.startswith("dynamo_request_plane"):
        return "frontend"
    return "unlabeled"


def _integer_or_none(value: object) -> int | None:
    try:
        numeric = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return numeric


def _raw_numeric_field(mapping: dict[str, Any], field: str) -> float | None:
    """Read one raw field without falling back to a different statistic."""

    value, selected = select_numeric_timeslice_field(mapping, (field,))
    return value if selected is not None else None


def _decode_running_timeslices(raw: pd.DataFrame) -> pd.DataFrame:
    """Select the raw decode running-gauge rows used for occupancy analysis."""

    return raw.loc[
        (raw["component"].astype("string") == "decode")
        & (raw["metric"].astype("string") == "sglang:num_running_reqs")
        & raw["worker_id"].astype("string").isin(DECODE_WORKERS)
    ].copy()


def _decode_timeslice_field_semantics(decode_running: pd.DataFrame) -> pd.DataFrame:
    """Inventory raw gauge fields by worker and DP rank without inventing fields."""

    rows: list[dict[str, object]] = []
    field_columns = {
        "avg": "timeslice_avg",
        "last": "timeslice_last",
        "max": "timeslice_max",
        "value": "timeslice_explicit_value",
        "min": "timeslice_min",
    }
    for (worker_id, dp_rank), group in decode_running.groupby(
        ["worker_id", "dp_rank"], dropna=False, sort=True
    ):
        count = int(len(group))
        selected = group["timeslice_selected_field"].dropna().astype(str)
        selected_counts = selected.value_counts().sort_index().to_dict()
        selected_label = (
            next(iter(selected_counts))
            if len(selected_counts) == 1
            else "mixed:" + ",".join(f"{key}={value}" for key, value in selected_counts.items())
        )
        schema_keys: set[str] = set()
        for value in group["timeslice_field_keys"].dropna():
            try:
                schema_keys.update(json.loads(str(value)))
            except json.JSONDecodeError:
                continue
        row: dict[str, object] = {
            "metric": "sglang:num_running_reqs",
            "worker_id": worker_id,
            "rank": dp_rank,
            "timeslice_count": count,
            "selected_field_under_current_parser": selected_label or "Unknown",
            "selected_field_counts": json.dumps(selected_counts, sort_keys=True),
            "raw_timeslice_schema_keys": json.dumps(sorted(schema_keys)),
            "timeslice_start_ns_min": _integer_min_or_none(group["timeslice_start_ns"]),
            "timeslice_end_ns_max": _integer_max_or_none(group["timeslice_end_ns"]),
            "classification": "Evidence",
            "notes": (
                "Presence is measured from raw public JSON timeslices. Current parser priority is "
                "avg, value, last, max; a missing statistic is not substituted in this inventory."
            ),
        }
        for field, column in field_columns.items():
            values = pd.to_numeric(group.get(column), errors="coerce")
            row[f"{field}_present_fraction"] = _fraction_true(values.notna())
        avg_values = pd.to_numeric(group["timeslice_avg"], errors="coerce")
        paired_avg_max = pd.DataFrame(
            {
                "avg": avg_values,
                "max": pd.to_numeric(group["timeslice_max"], errors="coerce"),
            }
        ).dropna()
        row["avg_fractional_value_count"] = int(
            (avg_values.notna() & ~np.isclose(avg_values.fillna(0.0), np.round(avg_values.fillna(0.0)))).sum()
        )
        row["avg_differs_from_max_count"] = int(
            (~np.isclose(paired_avg_max["avg"], paired_avg_max["max"])).sum()
        )
        rows.append(row)
    return pd.DataFrame(rows)


def _selected_field_label(field_semantics: pd.DataFrame) -> str:
    if field_semantics.empty or "selected_field_under_current_parser" not in field_semantics:
        return "Unknown"
    labels = field_semantics["selected_field_under_current_parser"].dropna().astype(str).unique().tolist()
    if not labels:
        return "Unknown"
    return labels[0] if len(labels) == 1 else "mixed"


def _decode_cluster_field_sensitivity(
    decode_running: pd.DataFrame,
    *,
    profile_duration_ns: int,
) -> pd.DataFrame:
    """Reconstruct named raw-field variants without filling unavailable samples."""

    field_columns = {
        "avg": "timeslice_avg",
        "last": "timeslice_last",
        "max": "timeslice_max",
    }
    rows: list[dict[str, object]] = []
    for field in DECODE_OCCUPANCY_SENSITIVITY_FIELDS:
        column = field_columns[field]
        variant = decode_running.copy()
        variant["timeslice_value"] = pd.to_numeric(variant.get(column), errors="coerce")
        raw_count = int(len(variant))
        present_fraction = _fraction_true(variant["timeslice_value"].notna())
        if not variant["timeslice_value"].notna().any():
            rows.append(
                {
                    "timeslice_field": field,
                    "availability_status": "Unavailable",
                    "raw_rank_timeslice_count": raw_count,
                    "raw_field_present_fraction": present_fraction,
                    "mean": "Unknown",
                    "p50": "Unknown",
                    "p90": "Unknown",
                    "p95": "Unknown",
                    "p99": "Unknown",
                    "highest_reconstructed_1s_bin_sum": "Unknown",
                    "notes": "The raw field was absent; no fallback value was invented.",
                }
            )
            continue
        workers = aggregate_rank_shards(
            variant,
            rank_column="dp_rank",
            metric_to_column={"sglang:num_running_reqs": "running_requests"},
            expected_rank_count=8,
            accepted_workers=DECODE_WORKERS,
        )
        cluster, summary = intersect_worker_intervals(
            workers,
            component="decode",
            worker_ids=DECODE_WORKERS,
            value_columns=("running_requests",),
            profile_duration_ns=profile_duration_ns,
        )
        metric = _lookup_cluster(summary, "running_requests")
        rows.append(
            {
                "timeslice_field": field,
                "availability_status": "Evidence" if metric else "Unavailable",
                "raw_rank_timeslice_count": raw_count,
                "raw_field_present_fraction": present_fraction,
                "cluster_overlap_segment_count": metric.get("overlap_segment_count", "Unknown"),
                "cluster_overlap_s": metric.get("common_worker_overlap_s", "Unknown"),
                "mean": metric.get("time_weighted_mean", "Unknown"),
                "p50": metric.get("p50", "Unknown"),
                "p90": metric.get("p90", "Unknown"),
                "p95": metric.get("p95", "Unknown"),
                "p99": metric.get("p99", "Unknown"),
                "highest_reconstructed_1s_bin_sum": metric.get("max", "Unknown"),
                "notes": (
                    "Exact endpoint-interval intersection after validated DP-shard sums. Values are "
                    "exported one-second occupancy-bin statistics, not instantaneous unique requests."
                ),
            }
        )
    return pd.DataFrame(rows)


def _decode_timeslice_alignment_summary(cluster: pd.DataFrame) -> pd.DataFrame:
    """Describe real endpoint-bin intersections and their start offsets."""

    if cluster.empty:
        return pd.DataFrame(
            [
                {
                    "availability_status": "Unavailable",
                    "notes": "No common decode endpoint intervals were reconstructed.",
                }
            ]
        )
    durations = pd.to_numeric(cluster["overlap_duration_ns"], errors="coerce").dropna()
    offsets = (
        pd.to_numeric(cluster["worker_b_sample_start_ns"], errors="coerce")
        - pd.to_numeric(cluster["worker_a_sample_start_ns"], errors="coerce")
    ).dropna()
    absolute_offsets = offsets.abs()
    return pd.DataFrame(
        [
            {
                "worker_a": cluster.iloc[0].get("worker_a", "Unknown"),
                "worker_b": cluster.iloc[0].get("worker_b", "Unknown"),
                "intersection_segment_count": int(len(cluster)),
                "intersection_duration_min_ns": _min_or_none(durations),
                "intersection_duration_p50_ns": _quantile(durations, 0.50),
                "intersection_duration_p90_ns": _quantile(durations, 0.90),
                "intersection_duration_p95_ns": _quantile(durations, 0.95),
                "intersection_duration_max_ns": _max_or_none(durations),
                "worker_b_minus_a_start_offset_p50_ns": _quantile(offsets, 0.50),
                "worker_b_minus_a_start_offset_p90_ns": _quantile(offsets, 0.90),
                "worker_b_minus_a_start_offset_p95_ns": _quantile(offsets, 0.95),
                "absolute_start_offset_p50_ns": _quantile(absolute_offsets, 0.50),
                "absolute_start_offset_p90_ns": _quantile(absolute_offsets, 0.90),
                "absolute_start_offset_p95_ns": _quantile(absolute_offsets, 0.95),
                "availability_status": "Evidence",
                "method": "actual [start_ns,end_ns) endpoint-interval intersection; no nearest-neighbor, fill, or interpolation",
                "notes": "Offsets compare the two exported backend timeslice grids, not request timestamps.",
            }
        ]
    )


def _fraction_true(values: pd.Series) -> float | None:
    return float(values.mean()) if len(values) else None


def _min_or_none(values: pd.Series) -> float | None:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    return float(numeric.min()) if not numeric.empty else None


def _integer_min_or_none(values: pd.Series) -> int | None:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    return int(numeric.min()) if not numeric.empty else None


def _integer_max_or_none(values: pd.Series) -> int | None:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    return int(numeric.max()) if not numeric.empty else None


def _source_semantics_rows() -> pd.DataFrame:
    """Record source mapping separately from execution-image proof."""

    base = {
        "runtime_container_tag": "lmsysorg/sglang:v0.5.16-cu130",
        "source_tag": "v0.5.16",
        "source_commit": "fdebc938f7f4d16fe6b9f55dcd9a767cf0899ea1",
        "source_url": "https://github.com/sgl-project/sglang/tree/fdebc938f7f4d16fe6b9f55dcd9a767cf0899ea1",
        "runtime_log_reference": (
            "multinode_server_logs.tar.gz:fingerprint_prefill_w0.json:91; "
            "fingerprint_prefill_w1.json:91; fingerprint_decode_w0.json:91; fingerprint_decode_w1.json:91"
        ),
        "mapping_status": "Evidence",
        "mapping_caveat": (
            "Public decode startup logs record SGLANG_BUILD_COMMIT=fdebc938f7f4d16fe6b9f55dcd9a767cf0899ea1; the container digest itself remains unrecorded."
        ),
    }
    rows = [
        {
            **base,
            "topic": "prefill_tp_cp_metrics",
            "source_reference": "python/sglang/srt/observability/metrics_collector.py:1048-1070; python/sglang/srt/layers/dp_attention.py:293-307; python/sglang/srt/managers/scheduler_components/metrics_reporter.py:641-650",
            "source_finding": (
                "Metric labels are emitted by attention-TP logging ranks; with TP8, DP1, ATTN_CP8, attention-TP size is one so all CP ranks are logging ranks. Running derives from local batch.reqs and queue from local waiting_queue."
            ),
            "reconstruction_implication": (
                "Do not sum TP/CP rank counters. Near-equality is supporting pressure evidence but does not establish a unique logical-request union."
            ),
            "status": "Evidence + Strong inference",
        },
        {
            **base,
            "topic": "decode_dp_attention_metrics",
            "source_reference": "python/sglang/srt/layers/dp_attention.py:293-307; python/sglang/srt/managers/scheduler_components/dp_attn.py:218-360; python/sglang/srt/managers/scheduler_components/metrics_reporter.py:845-906; python/sglang/srt/managers/data_parallel_controller.py:350-425,734-805; python/sglang/srt/observability/metrics_collector.py:1048-1088",
            "source_finding": (
                "With TP8/DP8/CP1, attention-TP size is one and each physical rank is a DP shard. The data-parallel controller tracks num_running_reqs + num_waiting_reqs per dp_rank, dispatches to a selected DP rank, and reports PD preallocation/transfer queues separately."
            ),
            "reconstruction_implication": (
                "Complete same-timeslice DP rank counters can be summed by their named decode-worker scope; generic waiting, PD preallocation, and PD transfer queues remain separate counters."
            ),
            "status": "Validated reconstruction",
        },
    ]
    return pd.DataFrame(rows)


def _attach_rank_semantic_verdicts(validation: pd.DataFrame) -> pd.DataFrame:
    result = validation.copy()
    result["semantic_verdict"] = np.where(
        result["component"].astype("string") == "prefill",
        "CP-rank local scheduler views; rank sum invalid, unique worker union Unknown",
        "DP-rank independent scheduler shards; sum permitted only for complete DP grids",
    )
    result["semantic_status"] = np.where(
        result["component"].astype("string") == "prefill",
        "Strong inference",
        "Validated reconstruction",
    )
    return result


def _prefill_envelope_summary(
    envelope: pd.DataFrame, verdict: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    metric_names = {
        "running_requests": "rank-envelope running requests",
        "waiting_requests": "rank-envelope waiting/queue requests",
        "prefill_bootstrap_queue": "rank-envelope prefill bootstrap queue",
        "prefill_inflight_queue": "rank-envelope prefill inflight queue",
    }
    for worker_id, group in envelope.groupby("worker_id", dropna=False, sort=True):
        worker_verdict = verdict.loc[verdict["worker_id"].astype("string") == str(worker_id)]
        verdict_text = worker_verdict.iloc[0]["verdict"] if not worker_verdict.empty else "unresolved"
        for base, metric in metric_names.items():
            values = {
                suffix: pd.to_numeric(group.get(f"{base}_rank_{suffix}"), errors="coerce").dropna()
                for suffix in ("min", "median", "max")
            }
            rows.append(
                {
                    "component": "prefill",
                    "worker_id": worker_id,
                    "metric": metric,
                    "timeslice_sample_count": int(len(values["max"])),
                    "rank_envelope_max_of_min": _max_or_none(values["min"]),
                    "rank_envelope_p50_of_median": _quantile(values["median"], 0.50),
                    "rank_envelope_p90_of_median": _quantile(values["median"], 0.90),
                    "rank_envelope_p95_of_median": _quantile(values["median"], 0.95),
                    "rank_envelope_max": _max_or_none(values["max"]),
                    "unique_worker_value": "Unknown",
                    "status": "Strong inference",
                    "rank_semantics_verdict": verdict_text,
                    "reconstruction_method": "TP/CP rank envelope (min/median/max); no rank sum or worker unique union",
                    "notes": "Do not read rank_envelope_max as a validated logical worker request count.",
                }
            )
    return pd.DataFrame(rows)


def _reviewable_prefill_timeseries(envelope: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "component",
        "worker_id",
        "timeslice_start_ns",
        "timeslice_end_ns",
        "running_requests_rank_min",
        "running_requests_rank_median",
        "running_requests_rank_max",
        "waiting_requests_rank_min",
        "waiting_requests_rank_median",
        "waiting_requests_rank_max",
        "prefill_bootstrap_queue_rank_min",
        "prefill_bootstrap_queue_rank_median",
        "prefill_bootstrap_queue_rank_max",
        "prefill_inflight_queue_rank_min",
        "prefill_inflight_queue_rank_median",
        "prefill_inflight_queue_rank_max",
        "rank_samples_complete",
        "all_rank_values_exactly_equal",
        "reconstruction_method",
        "validation_status",
    ]
    return _with_columns(envelope, columns)


def _unknown_prefill_cluster_summary(verdict: pd.DataFrame) -> pd.DataFrame:
    workers = ", ".join(verdict["worker_id"].astype(str).tolist()) or "Unknown"
    return pd.DataFrame(
        [
            {
                "component": "prefill",
                "metric": metric,
                "max": "Unknown",
                "p50": "Unknown",
                "p90": "Unknown",
                "p95": "Unknown",
                "positive_fraction": "Unknown",
                "status": "Unknown",
                "reconstruction_method": "withheld: CP rank-local counters lack a validated per-worker unique logical-request union",
                "notes": f"Workers {workers}; summing rank envelopes or ranks is not valid.",
            }
            for metric in ("running_requests", "waiting_requests")
        ]
    )


def _decorate_decode_summary(summary: pd.DataFrame, decode_waiting_all_zero: bool) -> pd.DataFrame:
    result = summary.copy()
    result["dp_semantics"] = "validated independent scheduler shards (TP8/DP8/DP attention)"
    result["decode_waiting_all_zero_raw_rank_series"] = np.where(
        result["metric"].astype("string") == "waiting_requests", decode_waiting_all_zero, pd.NA
    )
    result["notes"] = result["notes"].astype("string") + " DP rank sum requires complete raw 8-rank grids."
    return result


def _decorate_decode_cluster_summary(
    summary: pd.DataFrame,
    decode_waiting_all_zero: bool,
    *,
    current_timeslice_field: str,
) -> pd.DataFrame:
    result = summary.copy()
    result["decode_waiting_all_zero_raw_rank_series"] = np.where(
        result["metric"].astype("string") == "waiting_requests", decode_waiting_all_zero, pd.NA
    )
    result["timeslice_selected_field"] = current_timeslice_field
    common_note = (
        result["reconstruction_method"].astype("string")
        + "; DP rank sums are valid only because source topology and complete grids are both verified."
    )
    result["notes"] = common_note + " Selected raw field: " + current_timeslice_field + "."
    running = result["metric"].astype("string") == "running_requests"
    result.loc[running, "notes"] = common_note.loc[running] + " " + occupancy_bin_scope_note(
        current_timeslice_field
    )
    return result


def _reviewable_decode_timeseries(
    workers: pd.DataFrame, cluster: pd.DataFrame, phase_start_ns: int
) -> pd.DataFrame:
    work = workers.copy()
    work["phase_second_bin"] = (
        (pd.to_numeric(work["timeslice_start_ns"], errors="coerce") - phase_start_ns) // 1_000_000_000
    ).astype("Int64")
    columns = [
        "component",
        "worker_id",
        "phase_second_bin",
        "timeslice_start_ns",
        "timeslice_end_ns",
        "running_requests",
        "waiting_requests",
        "decode_prealloc_queue_requests",
        "decode_transfer_queue_requests",
        "reconstruction_method",
        "validation_status",
    ]
    return _with_columns(work, columns)


def _reviewable_cluster_timeseries(cluster: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "component",
        "overlap_start_ns",
        "overlap_end_ns",
        "overlap_duration_ns",
        "running_requests_cluster",
        "waiting_requests_cluster",
        "decode_prealloc_queue_requests_cluster",
        "decode_transfer_queue_requests_cluster",
        "running_requests_workers_aligned",
        "waiting_requests_workers_aligned",
        "decode_prealloc_queue_requests_workers_aligned",
        "decode_transfer_queue_requests_workers_aligned",
        "cluster_reconstruction_method",
        "validation_status",
    ]
    return _with_columns(cluster, columns)


def _dynamo_crosschecks(
    *, dynamo: pd.DataFrame, decode_workers: pd.DataFrame, prefill: pd.DataFrame, phase_start_ns: int
) -> pd.DataFrame:
    backend = dynamo.loc[
        (dynamo["metric"].astype("string") == "dynamo_component_inflight_requests")
        & (dynamo["dynamo_endpoint"].astype("string") == "generate")
        & dynamo["worker_id"].notna()
    ].copy()
    # Decode uses a validated DP-shard sum; prefill remains a rank-0
    # observational cross-check so no source scope is silently upgraded.
    decode_crosscheck = dynamo_sglang_crosscheck(
        backend.loc[backend["component"] == "decode"],
        decode_workers,
        phase_start_ns=phase_start_ns,
    )
    if not decode_crosscheck.empty:
        decode_crosscheck["rank_or_reconstruction_method"] = "validated sum of complete DP-rank scheduler shards"
        decode_crosscheck["alignment_method"] = "same backend endpoint exact exported [start,end) 1-second bins"
        decode_crosscheck["classification"] = "Evidence + Validated reconstruction"

    rank0 = prefill.loc[
        (prefill["metric"].astype("string") == "sglang:num_running_reqs")
        & (prefill["tp_rank"].astype("string") == "0")
    ].copy()
    if not rank0.empty:
        rank0 = rank0.rename(columns={"timeslice_value": "running_requests"})
        rank0["phase_second_bin"] = (
            (pd.to_numeric(rank0["timeslice_start_ns"], errors="coerce") - phase_start_ns)
            // 1_000_000_000
        ).astype(int)
        rank0["reconstruction_method"] = "TP0 local CP-rank scheduler view only"
        rank0["validation_status"] = "Evidence"
    prefill_crosscheck = dynamo_sglang_crosscheck(
        backend.loc[backend["component"] == "prefill"], rank0, phase_start_ns=phase_start_ns
    )
    if not prefill_crosscheck.empty:
        prefill_crosscheck["rank_or_reconstruction_method"] = "TP0 local CP-rank scheduler view; not worker unique union"
        prefill_crosscheck["alignment_method"] = "same backend endpoint exact exported [start,end) 1-second bins"
        prefill_crosscheck["classification"] = "Evidence"

    layer_rows = _frontend_layer_rows(dynamo)
    result = pd.concat([prefill_crosscheck, decode_crosscheck, layer_rows], ignore_index=True, sort=False)
    if result.empty:
        return result
    result["scope_note"] = (
        "Dynamo component inflight is a work-handler lifecycle metric; it is not synonymous with SGLang scheduler running. "
        "Frontend/request-plane series are independent scrape/scope layers and are retained without direct equality claims."
    )
    return result


def _frontend_layer_rows(dynamo: pd.DataFrame) -> pd.DataFrame:
    metrics = (
        "dynamo_request_plane_inflight_requests",
        "dynamo_frontend_inflight_requests",
        "dynamo_frontend_queued_requests",
        "dynamo_frontend_router_queue_pending_requests",
        "dynamo_frontend_router_queue_pending_isl_tokens",
    )
    rows: list[dict[str, object]] = []
    for (metric, worker_type), group in dynamo.loc[
        dynamo["metric"].astype("string").isin(metrics)
    ].groupby(["metric", "worker_type"], dropna=False, sort=True):
        values = pd.to_numeric(group["timeslice_value"], errors="coerce").dropna()
        rows.append(
            {
                "worker_id": pd.NA,
                "component": "frontend_or_request_plane",
                "dynamo_metric": metric,
                "sglang_metric": pd.NA,
                "rank_or_reconstruction_method": "not directly joined to backend scheduler metrics",
                "alignment_method": "independent frontend/request-plane AIPerf 1-second export bins",
                "common_phase_second_bins": int(len(values)),
                "dynamo_max": _max_or_none(values),
                "dynamo_p50": _quantile(values, 0.50),
                "dynamo_p90": _quantile(values, 0.90),
                "dynamo_p95": _quantile(values, 0.95),
                "worker_type": worker_type,
                "status": "Evidence",
                "classification": "Evidence",
                "interpretation": "Frontend/request-plane layer retained separately from backend SGLang scheduler scope.",
            }
        )
    return pd.DataFrame(rows)


def _primary_cluster_summary(
    *,
    http: dict[str, object],
    prefill_summary: pd.DataFrame,
    decode_summary: pd.DataFrame,
    decode_cluster_summary: pd.DataFrame,
    prefill_verdict: pd.DataFrame,
    decode_waiting_all_zero: bool,
    current_timeslice_field: str,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    def add(
        metric: str,
        value: object,
        unit: str,
        scope: str,
        status: str,
        method: str,
        evidence: str,
        notes: str,
    ) -> None:
        rows.append(
            {
                "metric": metric,
                "value": value,
                "unit": unit,
                "scope": scope,
                "status": status,
                "reconstruction_method": method,
                "evidence": evidence,
                "notes": notes,
            }
        )

    for input_name, output_name in (
        ("max_inflight", "http_max_inflight"),
        ("time_weighted_mean_inflight", "http_time_weighted_mean"),
        ("time_weighted_p90_inflight", "http_p90"),
        ("time_weighted_p95_inflight", "http_p95"),
    ):
        add(
            output_name,
            http.get(input_name, "Unknown"),
            "requests",
            "HTTP/client [request_start_ns, request_end_ns) profile overlap",
            "Evidence",
            "interval sweep from successful profiling request timestamps",
            "public profile_export + canonical processed request table",
            "Not an SGLang scheduler running-request count.",
        )

    for position, worker_id in enumerate(PREFILL_WORKERS):
        prefix = f"prefill_worker_{position}"
        for kind, label in (("running", "rank-envelope running requests"), ("waiting", "rank-envelope queue requests")):
            summary = _lookup_prefill(prefill_summary, worker_id, kind)
            envelope_value = summary.get("rank_envelope_max", "Unknown") if summary else "Unknown"
            add(
                f"{prefix}_max_{kind}",
                "Unknown",
                "requests",
                "unique logical requests at one CP8 prefill worker",
                "Unknown",
                "withheld: TP/CP rank-local views lack request-ID union",
                "raw 1-second rank grids plus SGLang CP8 source topology",
                "The rank envelope is recorded separately; neither rank sum nor a unique worker count is proven.",
            )
            add(
                f"{prefix}_rank_envelope_max_{kind}",
                envelope_value,
                "rank-local counter",
                label,
                "Strong inference",
                "max over per-timeslice TP/CP rank envelope; no sum",
                "raw 1-second prefill rank series",
                "Pressure evidence only, not a unique logical worker request count.",
            )

    for kind in ("running", "waiting"):
        add(
            f"prefill_cluster_max_{kind}",
            "Unknown",
            "requests",
            "two prefill workers' unique logical request union",
            "Unknown",
            "withheld: each CP8 worker unique union is unknown",
            "prefill rank validation",
            "Do not sum TP ranks or strong-inference rank envelopes across workers.",
        )
        for percentile in ("p50", "p90", "p95"):
            add(
                f"prefill_cluster_{percentile}_{kind}",
                "Unknown",
                "requests",
                "two prefill workers' unique logical request union",
                "Unknown",
                "withheld: each CP8 worker unique union is unknown",
                "prefill rank validation",
                "Unknown is intentionally not converted to zero.",
            )
    add(
        "prefill_cluster_waiting_positive_fraction",
        "Unknown",
        "fraction",
        "two prefill workers' unique logical request union",
        "Unknown",
        "withheld: CP-rank queue counters cannot establish a unique worker union",
        "prefill rank validation",
        "Rank-local positive queue evidence exists but cluster positive fraction is not reconstructable.",
    )

    for position, worker_id in enumerate(DECODE_WORKERS):
        prefix = f"decode_worker_{position}"
        for kind in ("running", "waiting"):
            summary = _lookup_decode(decode_summary, worker_id, f"{kind}_requests")
            add(
                f"{prefix}_max_{kind}",
                summary.get("max", "Unknown") if summary else "Unknown",
                "requests",
                "one decode worker, sum of complete DP8 rank-local scheduler shards",
                summary.get("status", "Unknown") if summary else "Unknown",
                summary.get("reconstruction_method", "Unknown") if summary else "Unknown",
                "raw 1-second decode DP rank grids + SGLang DP attention source semantics",
                "A logical request is assigned to one DP shard under the validated source mapping.",
            )

    decode_bin_scope = (
        "two decode workers, exact intersections of exported one-second scheduler occupancy bins"
    )
    for kind in ("running", "waiting"):
        summary = _lookup_cluster(decode_cluster_summary, f"{kind}_requests")
        for field, suffix in (("max", "max"), ("p50", "p50"), ("p90", "p90"), ("p95", "p95")):
            if kind == "running" and suffix == "max":
                notes = (
                    "Highest reconstructed sum across exported one-second scheduler occupancy bins. "
                    "Not an instantaneous unique-request maximum."
                )
            elif kind == "running":
                notes = (
                    "Time-weighted distribution of reconstructed exported one-second scheduler "
                    "occupancy-bin sums; not instantaneous unique-request counts."
                )
            else:
                notes = (
                    "Generic SGLang decode waiting queue only; this does not assert that all "
                    "P/D-specific decode queues were zero."
                )
            add(
                f"decode_cluster_{suffix}_{kind}",
                summary.get(field, "Unknown") if summary else "Unknown",
                "requests",
                decode_bin_scope,
                summary.get("status", "Unknown") if summary else "Unknown",
                summary.get("reconstruction_method", "Unknown") if summary else "Unknown",
                "raw decode DP grids, validated worker sums, exact endpoint-interval intersection",
                notes,
            )
    queue_cluster = _lookup_cluster(decode_cluster_summary, "waiting_requests")
    add(
        "decode_cluster_waiting_positive_fraction",
        queue_cluster.get("positive_fraction", "Unknown") if queue_cluster else "Unknown",
        "fraction",
        decode_bin_scope,
        queue_cluster.get("status", "Unknown") if queue_cluster else "Unknown",
        queue_cluster.get("reconstruction_method", "Unknown") if queue_cluster else "Unknown",
        "raw decode queue rank series",
        "Entire observed decode raw rank-series window has generic queue=0; this is not a claim that all P/D-specific decode queues, Dynamo queues, or frontend queues are zero.",
    )
    add(
        "decode_waiting_all_zero",
        decode_waiting_all_zero,
        "boolean",
        "all observed profiling-window decode DP-rank sglang:num_queue_reqs samples",
        "Evidence",
        "raw rank-timeslice check",
        "server_metrics_export.json 1-second AIPerf bins",
        "The metric's zero scope is generic SGLang decode num_queue_reqs only; separate P/D preallocation and transfer queue metrics are retained below.",
    )
    for metric, prefix, label in (
        (
            "decode_prealloc_queue_requests",
            "decode_cluster_prealloc_queue",
            "P/D-specific decode preallocation queue",
        ),
        (
            "decode_transfer_queue_requests",
            "decode_cluster_transfer_queue",
            "P/D-specific decode transfer queue",
        ),
    ):
        summary = _lookup_cluster(decode_cluster_summary, metric)
        for field, suffix in (("max", "max"), ("p90", "p90")):
            add(
                f"{prefix}_{suffix}",
                summary.get(field, "Unknown") if summary else "Unknown",
                "requests",
                decode_bin_scope,
                summary.get("status", "Unknown") if summary else "Unknown",
                summary.get("reconstruction_method", "Unknown") if summary else "Unknown",
                "raw decode DP grids, validated worker sums, exact endpoint-interval intersection",
                f"{label}; it is deliberately not merged with generic num_queue_reqs or another P/D queue.",
            )
        add(
            f"{prefix}_positive_fraction",
            summary.get("positive_fraction", "Unknown") if summary else "Unknown",
            "fraction",
            decode_bin_scope,
            summary.get("status", "Unknown") if summary else "Unknown",
            summary.get("reconstruction_method", "Unknown") if summary else "Unknown",
            "raw decode DP grids, validated worker sums, exact endpoint-interval intersection",
            f"Fraction of common endpoint-interval duration with {label.lower()} > 0; not a unique request queue fraction.",
        )
    add(
        "decode_occupancy_timeslice_selected_field",
        current_timeslice_field,
        "raw timeslice field",
        "decode running-request reconstruction input",
        "Evidence",
        "raw timeslice field inventory",
        "c8_decode_timeslice_field_semantics.csv",
        occupancy_bin_scope_note(current_timeslice_field),
    )
    add(
        "backend_stage_active_max",
        "Unknown",
        "requests",
        "P/D combined backend stage occupancy",
        "Unknown",
        "withheld: prefill unique worker union is unknown and P/D handoff overlap is not request-correlated",
        "rank-validation plus absent lifecycle join",
        "Do not add prefill and decode maxima or unrelated-timestamp maxima.",
    )
    add(
        "backend_stage_active_p90",
        "Unknown",
        "requests",
        "P/D combined backend stage occupancy",
        "Unknown",
        "withheld: prefill unique worker union is unknown and P/D handoff overlap is not request-correlated",
        "rank-validation plus absent lifecycle join",
        "Unknown is intentionally not converted to zero.",
    )
    add(
        "unique_global_running_max",
        "Unknown",
        "requests",
        "unique logical requests across prefill and decode stages",
        "Unknown",
        "no request-correlated P/D lifecycle or stage deduplication evidence",
        "public profile/export/log scope",
        "P/D sums can double-count a handoff; HTTP overlap is a separate metric.",
    )
    add(
        "prefill_tp_rank_semantics",
        "cp_rank_local_views_no_unique_union",
        "classification",
        "prefill TP8/ATTN_CP8 rank metric semantics",
        "Strong inference",
        "raw rank equality plus source topology",
        "c8_scheduler_rank_semantics_validation.csv",
        "Neither multiply nor assert a worker logical union.",
    )
    add(
        "decode_dp_rank_semantics",
        "independent_scheduler_shards_validated",
        "classification",
        "decode TP8/DP8 metric semantics",
        "Validated reconstruction",
        "source controller semantics + raw complete DP grids",
        "c8_scheduler_source_semantics.csv + rank validation",
        "Sum is permitted within a decode worker only for complete raw DP grids.",
    )
    return pd.DataFrame(rows)


def _lookup_prefill(summary: pd.DataFrame, worker_id: str, kind: str) -> dict[str, object]:
    target = (
        "rank-envelope running requests"
        if kind == "running"
        else "rank-envelope waiting/queue requests"
    )
    subset = summary.loc[
        (summary["worker_id"].astype("string") == worker_id)
        & (summary["metric"].astype("string") == target)
    ]
    return subset.iloc[0].to_dict() if not subset.empty else {}


def _lookup_decode(summary: pd.DataFrame, worker_id: str, metric: str) -> dict[str, object]:
    subset = summary.loc[
        (summary["worker_id"].astype("string") == worker_id)
        & (summary["metric"].astype("string") == metric)
    ]
    return subset.iloc[0].to_dict() if not subset.empty else {}


def _lookup_cluster(summary: pd.DataFrame, metric: str) -> dict[str, object]:
    subset = summary.loc[summary["metric"].astype("string") == metric]
    return subset.iloc[0].to_dict() if not subset.empty else {}


def _read_single_row(path: Path) -> dict[str, object]:
    if not path.exists():
        raise SystemExit(f"missing prerequisite HTTP summary: {path}; run make mtp-c8-concurrency")
    frame = pd.read_csv(path)
    return frame.iloc[0].to_dict() if not frame.empty else {}


def _build_figures(
    *,
    figures: Path,
    prefill_envelope: pd.DataFrame,
    decode_cluster: pd.DataFrame,
    dynamo: pd.DataFrame,
    phase_start_ns: int,
) -> None:
    _plot_prefill_envelope(figures / "c8_prefill_worker_running_waiting.png", prefill_envelope, phase_start_ns)
    _plot_decode_cluster(figures / "c8_decode_worker_running_waiting.png", decode_cluster)
    _plot_frontend_backend_layers(
        figures / "c8_frontend_backend_concurrency_timeline.png", dynamo, decode_cluster, phase_start_ns
    )


def _plot_prefill_envelope(path: Path, frame: pd.DataFrame, phase_start_ns: int) -> None:
    figure, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    for worker_id, group in frame.groupby("worker_id", dropna=False, sort=True):
        x = (pd.to_numeric(group["timeslice_start_ns"], errors="coerce") - phase_start_ns) / 1e9
        for axis, base, title in (
            (axes[0], "running_requests", "Prefill TP/CP rank envelope — running"),
            (axes[1], "waiting_requests", "Prefill TP/CP rank envelope — waiting"),
        ):
            lower = pd.to_numeric(group.get(f"{base}_rank_min"), errors="coerce")
            upper = pd.to_numeric(group.get(f"{base}_rank_max"), errors="coerce")
            median = pd.to_numeric(group.get(f"{base}_rank_median"), errors="coerce")
            axis.fill_between(x, lower, upper, alpha=0.14)
            axis.plot(x, median, linewidth=0.8, label=f"{worker_id} rank median")
            axis.set_title(title)
            axis.set_ylabel("rank-local requests")
            axis.grid(alpha=0.25)
    axes[1].set_xlabel("seconds from profiling start")
    axes[0].legend(fontsize=7, ncol=2)
    figure.suptitle("Public H200 c8 prefill: rank-local envelope, not a unique worker union", y=1.01)
    figure.tight_layout()
    figure.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(figure)


def _plot_decode_cluster(path: Path, frame: pd.DataFrame) -> None:
    figure, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    starts = pd.to_numeric(frame.get("overlap_start_ns"), errors="coerce")
    x = (starts - starts.min()) / 1e9 if starts.notna().any() else starts
    for axis, column, title in (
        (
            axes[0],
            "running_requests_cluster",
            "Decode reconstructed occupancy (exported 1-s-bin DP-shard sum)",
        ),
        (axes[1], "waiting_requests_cluster", "Decode cluster waiting (validated DP-shard sum)"),
    ):
        axis.plot(x, pd.to_numeric(frame.get(column), errors="coerce"), linewidth=0.8)
        axis.set_title(title)
        axis.set_ylabel("requests")
        axis.grid(alpha=0.25)
    axes[1].set_xlabel("seconds from first common endpoint sample")
    figure.suptitle(
        "Public H200 c8: exported occupancy bins aligned without fill/interpolation", y=1.01
    )
    figure.tight_layout()
    figure.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(figure)


def _plot_frontend_backend_layers(
    path: Path, dynamo: pd.DataFrame, decode_cluster: pd.DataFrame, phase_start_ns: int
) -> None:
    figure, axis = plt.subplots(figsize=(10, 4))
    for metric, label in (
        ("dynamo_request_plane_inflight_requests", "Dynamo request-plane inflight"),
        ("dynamo_frontend_inflight_requests", "Dynamo frontend inflight"),
        ("dynamo_frontend_queued_requests", "Dynamo frontend queued"),
    ):
        subset = dynamo.loc[dynamo["metric"].astype("string") == metric]
        if subset.empty:
            continue
        x = (pd.to_numeric(subset["timeslice_start_ns"], errors="coerce") - phase_start_ns) / 1e9
        axis.plot(x, pd.to_numeric(subset["timeslice_value"], errors="coerce"), linewidth=0.7, label=label)
    if not decode_cluster.empty:
        starts = pd.to_numeric(decode_cluster["overlap_start_ns"], errors="coerce")
        axis.plot(
            (starts - starts.min()) / 1e9,
            pd.to_numeric(decode_cluster["running_requests_cluster"], errors="coerce"),
            linewidth=0.8,
            label="SGLang decode reconstructed occupancy (1-s-bin sum)",
        )
    axis.set_title("Public H200 c8 concurrency layers (different scopes; not equivalent)")
    axis.set_xlabel("seconds from profiling start / phase-second bin")
    axis.set_ylabel("requests")
    axis.grid(alpha=0.25)
    axis.legend(fontsize=7, ncol=2)
    figure.tight_layout()
    figure.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(figure)


def _with_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = frame.copy()
    for column in columns:
        if column not in result:
            result[column] = pd.NA
    return result.loc[:, columns].copy()


def _max_or_none(values: pd.Series) -> float | None:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    return float(numeric.max()) if not numeric.empty else None


def _quantile(values: pd.Series, quantile: float) -> float | None:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    return float(numeric.quantile(quantile)) if not numeric.empty else None


def _first_or_unknown(frame: pd.DataFrame, column: str) -> object:
    return frame.iloc[0][column] if not frame.empty and column in frame else "Unknown"


if __name__ == "__main__":
    raise SystemExit(main())
