"""Scope-safe helpers for SGLang worker/cluster scheduler reconstruction.

The public AIPerf export presents metrics at individual SGLang rank labels.
This module deliberately separates three operations which are easy to conflate:

* testing whether rank-labelled series are duplicates of one worker gauge;
* summing a DP-sharded counter only after caller-supplied semantic validation;
* aligning independent workers in coarse phase-second bins without interpolation.

No function here converts a missing/unsupported metric to zero, or calls a
prefill+decode sum a unique system-wide request count.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping, Sequence
from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def select_numeric_timeslice_field(
    mapping: Mapping[str, object],
    fields: Sequence[str],
) -> tuple[float | None, str | None]:
    """Return the first finite numeric raw timeslice field and its name.

    Exported AIPerf timeslices can expose multiple summaries such as ``avg``,
    ``last``, and ``max``.  Callers must retain the selected field alongside
    its value so a scheduler-occupancy bin is not silently relabelled as an
    instantaneous scrape.  Missing fields remain ``None`` rather than zero.
    """

    for field in fields:
        value = _finite_float(mapping.get(field))
        if value is not None:
            return value, field
    return None, None


def occupancy_bin_scope_note(selected_field: str | None) -> str:
    """Describe an exported scheduler-bin statistic without inventing scope.

    The helper deliberately does not call a bin statistic an instantaneous
    request count.  It is reused in derived CSVs and tests so the high-water
    mark of an occupancy reconstruction cannot silently become a unique
    request-concurrency claim.
    """

    if selected_field == "avg":
        statistic = "selected raw avg field from exported one-second scheduler occupancy bins"
    elif selected_field == "last":
        statistic = "selected raw last field from exported scheduler occupancy bins"
    elif selected_field == "max":
        statistic = "selected raw max field from exported scheduler occupancy bins"
    elif selected_field == "value":
        statistic = "selected raw value field from exported scheduler occupancy bins"
    else:
        statistic = "exported scheduler occupancy-bin field with unresolved selected statistic"
    return f"{statistic}; not an instantaneous unique-request maximum."


def rank_series_validation(
    timeline: pd.DataFrame,
    *,
    rank_column: str,
    expected_rank_count: int = 8,
) -> pd.DataFrame:
    """Validate rank equality at exactly aligned raw timeslices.

    ``timeline`` must retain the raw exporter ``timeslice_start_ns`` and
    ``timeslice_end_ns``.  Equality is never inferred from aggregate maxima:
    every comparison uses the complete same-start/same-end rank set.
    """

    required = {
        "component",
        "worker_id",
        "metric",
        "timeslice_start_ns",
        "timeslice_end_ns",
        "timeslice_value",
        rank_column,
    }
    missing = sorted(required - set(timeline.columns))
    if missing:
        raise ValueError(f"rank series validation missing columns: {', '.join(missing)}")

    rows: list[dict[str, object]] = []
    groups = timeline.groupby(["component", "worker_id", "metric"], dropna=False, sort=True)
    for (component, worker_id, metric), group in groups:
        work = group.copy()
        work[rank_column] = work[rank_column].astype("string")
        work["timeslice_value"] = pd.to_numeric(work["timeslice_value"], errors="coerce")
        work = work.dropna(subset=[rank_column, "timeslice_value"])
        rank_labels = sorted(work[rank_column].unique().tolist(), key=_rank_sort_key)
        pivot = work.pivot_table(
            index=["timeslice_start_ns", "timeslice_end_ns"],
            columns=rank_column,
            values="timeslice_value",
            aggfunc="first",
            observed=False,
        ).reindex(columns=rank_labels)
        # A populated pivot of only seven labels is not a complete expected
        # DP8/TP8 grid.  Preserve it for diagnostics, but do not let it pass
        # a completeness check merely because the observed labels agree.
        complete = (
            pivot.notna().all(axis=1) & (len(rank_labels) == expected_rank_count)
            if len(rank_labels)
            else pd.Series(dtype=bool)
        )
        complete_pivot = pivot.loc[complete]
        if complete_pivot.empty:
            all_equal_count = 0
            max_difference = None
        else:
            rank_difference = complete_pivot.max(axis=1) - complete_pivot.min(axis=1)
            all_equal_count = int((rank_difference == 0).sum())
            max_difference = _finite_float(rank_difference.max())
        aligned_count = int(len(pivot))
        complete_count = int(complete.sum()) if len(complete) else 0
        sample_count_by_rank = {
            str(rank): int(pivot[str(rank)].notna().sum()) for rank in rank_labels
        }
        missing_by_rank = {
            str(rank): int(aligned_count - pivot[str(rank)].notna().sum()) for rank in rank_labels
        }
        rows.append(
            {
                "component": component,
                "worker_id": worker_id,
                "metric": metric,
                "rank_dimension": rank_column,
                "expected_rank_count": expected_rank_count,
                "observed_rank_count": int(len(rank_labels)),
                "rank_labels": json.dumps(rank_labels),
                "raw_row_count": int(len(work)),
                "aligned_timeslice_count": aligned_count,
                "complete_expected_rank_timeslice_count": complete_count,
                "complete_expected_rank_ratio": _safe_ratio(complete_count, aligned_count),
                "all_8_ranks_exactly_equal_count": all_equal_count,
                "all_8_ranks_exactly_equal_ratio": _safe_ratio(all_equal_count, complete_count),
                "max_rank_difference_per_timeslice": max_difference,
                "overall_max_rank_difference": max_difference,
                "pairwise_correlation": json.dumps(_pairwise_correlations(pivot), sort_keys=True),
                "rank0_vs_other_exact_match_percent": json.dumps(
                    _rank_zero_exact_match_percent(pivot), sort_keys=True
                ),
                "pairwise_exact_match_percent": json.dumps(
                    _pairwise_exact_match_percent(pivot), sort_keys=True
                ),
                "missing_sample_count_by_rank": json.dumps(missing_by_rank, sort_keys=True),
                "sample_count_by_rank": json.dumps(sample_count_by_rank, sort_keys=True),
                "timestamp_alignment_status": _alignment_status(
                    observed_rank_count=len(rank_labels),
                    expected_rank_count=expected_rank_count,
                    complete_count=complete_count,
                    aligned_count=aligned_count,
                ),
                "classification": "Evidence",
                "method": "same raw timeslice_start_ns + timeslice_end_ns; no interpolation",
            }
        )
    return pd.DataFrame(rows)


def prefill_duplicate_verdict(
    validation: pd.DataFrame,
    *,
    required_metrics: Sequence[str],
    source_semantics_verified: bool,
) -> pd.DataFrame:
    """Produce a worker-level prefill deduplication verdict.

    Caller must independently establish the runtime/source semantics.  Exact
    value equality by itself is not enough to label rank series duplicates.
    """

    required = {
        "component",
        "worker_id",
        "metric",
        "observed_rank_count",
        "expected_rank_count",
        "complete_expected_rank_ratio",
        "all_8_ranks_exactly_equal_ratio",
    }
    missing = sorted(required - set(validation.columns))
    if missing:
        raise ValueError(f"prefill verdict missing columns: {', '.join(missing)}")

    rows: list[dict[str, object]] = []
    prefill = validation.loc[validation["component"].astype("string") == "prefill"].copy()
    for worker_id, group in prefill.groupby("worker_id", dropna=False, sort=True):
        metric_rows = group.set_index("metric")
        evidence: list[str] = []
        metric_pass = True
        for metric in required_metrics:
            if metric not in metric_rows.index:
                metric_pass = False
                evidence.append(f"missing:{metric}")
                continue
            item = metric_rows.loc[metric]
            if isinstance(item, pd.DataFrame):
                item = item.iloc[0]
            rank_ok = int(item["observed_rank_count"]) == int(item["expected_rank_count"])
            complete_ok = _is_one(item["complete_expected_rank_ratio"])
            equal_ok = _is_one(item["all_8_ranks_exactly_equal_ratio"])
            if not (rank_ok and complete_ok and equal_ok):
                metric_pass = False
            evidence.append(
                f"{metric}: ranks={item['observed_rank_count']}/{item['expected_rank_count']}; "
                f"complete={item['complete_expected_rank_ratio']}; exact={item['all_8_ranks_exactly_equal_ratio']}"
            )
        if source_semantics_verified and metric_pass:
            verdict = "validated_duplicate_worker_gauge"
            status = "Validated reconstruction"
        elif metric_pass:
            verdict = "likely_duplicate_worker_gauge"
            status = "Strong inference"
        else:
            verdict = "unresolved"
            status = "Unknown"
        rows.append(
            {
                "component": "prefill",
                "worker_id": worker_id,
                "required_metrics": ";".join(required_metrics),
                "source_semantics_verified": bool(source_semantics_verified),
                "rank_equality_validated": bool(metric_pass),
                "verdict": verdict,
                "status": status,
                "evidence": " | ".join(evidence),
            }
        )
    return pd.DataFrame(rows)


def deduplicate_rank_gauges(
    timeline: pd.DataFrame,
    *,
    rank_column: str,
    metric_to_column: Mapping[str, str],
    expected_rank_count: int,
    accepted_workers: Iterable[str],
) -> pd.DataFrame:
    """Deduplicate equal rank gauges into one strict worker timeseries.

    A value appears only when every expected rank exists at that raw timeslice
    and all values exactly agree.  Thus a missing/inconsistent rank becomes a
    missing worker sample, never a zero or a median substitute.
    """

    accepted = {str(worker) for worker in accepted_workers}
    rows: list[dict[str, object]] = []
    relevant = timeline.loc[
        timeline["worker_id"].astype("string").isin(accepted)
        & timeline["metric"].astype("string").isin(metric_to_column)
    ].copy()
    keys = ["component", "worker_id", "endpoint_url", "timeslice_start_ns", "timeslice_end_ns", "metric"]
    for values, group in relevant.groupby(keys, dropna=False, sort=True):
        component, worker_id, endpoint_url, start, end, metric = values
        values_numeric = pd.to_numeric(group["timeslice_value"], errors="coerce").dropna()
        ranks = group[rank_column].astype("string").dropna().unique()
        complete = len(ranks) == expected_rank_count and len(values_numeric) == expected_rank_count
        exactly_equal = complete and values_numeric.nunique(dropna=True) == 1
        rows.append(
            {
                "component": component,
                "worker_id": worker_id,
                "endpoint_url": endpoint_url,
                "timeslice_start_ns": int(start),
                "timeslice_end_ns": int(end),
                "metric": metric,
                "worker_value": _finite_float(values_numeric.iloc[0]) if exactly_equal else None,
                "rank_sample_count": int(len(values_numeric)),
                "rank_samples_complete": bool(complete),
                "all_rank_values_exactly_equal": bool(exactly_equal),
                "reconstruction_method": "deduplicated exactly-equal rank gauge",
                "validation_status": "Validated reconstruction" if exactly_equal else "Unknown",
            }
        )
    long = pd.DataFrame(rows)
    if long.empty:
        return _empty_worker_timeseries()
    index_columns = ["component", "worker_id", "endpoint_url", "timeslice_start_ns", "timeslice_end_ns"]
    # ``pivot_table`` silently drops a key whose only value is null.  Keep the
    # incomplete timeslice visible so callers can distinguish missing evidence
    # from a zero worker count.
    wide = (
        long.set_index([*index_columns, "metric"])["worker_value"]
        .unstack("metric")
        .rename(columns=metric_to_column)
    )
    wide.columns.name = None
    result = wide.reset_index()
    expected = list(metric_to_column.values())
    for column in expected:
        if column not in result:
            result[column] = np.nan
    result["reconstruction_method"] = "deduplicated exactly-equal rank gauge"
    result["validation_status"] = "Validated reconstruction"
    return result.sort_values(["worker_id", "timeslice_start_ns"]).reset_index(drop=True)


def rank_envelope_timeseries(
    timeline: pd.DataFrame,
    *,
    rank_column: str,
    metric_to_column: Mapping[str, str],
    expected_rank_count: int,
) -> pd.DataFrame:
    """Preserve a rank-local counter as a min/median/max envelope.

    This is useful for CP-prefill evidence where every physical rank exports a
    local scheduler view but logical-request union is not observable.  It is
    explicitly *not* a worker-level unique request reconstruction.
    """

    rows: list[dict[str, object]] = []
    relevant = timeline.loc[timeline["metric"].astype("string").isin(metric_to_column)].copy()
    keys = ["component", "worker_id", "endpoint_url", "timeslice_start_ns", "timeslice_end_ns", "metric"]
    for values, group in relevant.groupby(keys, dropna=False, sort=True):
        component, worker_id, endpoint_url, start, end, metric = values
        numeric = pd.to_numeric(group["timeslice_value"], errors="coerce").dropna()
        ranks = group[rank_column].astype("string").dropna().unique()
        complete = len(ranks) == expected_rank_count and len(numeric) == expected_rank_count
        base = metric_to_column[str(metric)]
        rows.append(
            {
                "component": component,
                "worker_id": worker_id,
                "endpoint_url": endpoint_url,
                "timeslice_start_ns": int(start),
                "timeslice_end_ns": int(end),
                "metric": metric,
                f"{base}_rank_min": _finite_float(numeric.min()) if not numeric.empty else None,
                f"{base}_rank_median": _quantile(numeric, 0.50),
                f"{base}_rank_max": _finite_float(numeric.max()) if not numeric.empty else None,
                "rank_sample_count": int(len(numeric)),
                "rank_samples_complete": bool(complete),
                "all_rank_values_exactly_equal": bool(
                    complete and numeric.nunique(dropna=True) == 1
                ),
            }
        )
    long = pd.DataFrame(rows)
    if long.empty:
        return _empty_worker_timeseries()
    key_columns = ["component", "worker_id", "endpoint_url", "timeslice_start_ns", "timeslice_end_ns"]
    value_columns = [column for column in long if column.endswith(("_rank_min", "_rank_median", "_rank_max"))]
    result = long.groupby(key_columns, dropna=False, sort=True)[value_columns].first().reset_index()
    result["reconstruction_method"] = "rank-local envelope; no rank sum and no unique-worker union"
    result["validation_status"] = "Strong inference"
    return result.sort_values(["worker_id", "timeslice_start_ns"]).reset_index(drop=True)


def aggregate_rank_shards(
    timeline: pd.DataFrame,
    *,
    rank_column: str,
    metric_to_column: Mapping[str, str],
    expected_rank_count: int,
    accepted_workers: Iterable[str],
) -> pd.DataFrame:
    """Sum complete rank-local scheduler shards into worker timeseries.

    This mechanical sum is intentionally gated by ``accepted_workers``.  The
    caller must add workers only after independently establishing that ranks
    own distinct logical requests and the metric is rank-local.
    """

    accepted = {str(worker) for worker in accepted_workers}
    rows: list[dict[str, object]] = []
    relevant = timeline.loc[
        timeline["worker_id"].astype("string").isin(accepted)
        & timeline["metric"].astype("string").isin(metric_to_column)
    ].copy()
    keys = ["component", "worker_id", "endpoint_url", "timeslice_start_ns", "timeslice_end_ns", "metric"]
    for values, group in relevant.groupby(keys, dropna=False, sort=True):
        component, worker_id, endpoint_url, start, end, metric = values
        values_numeric = pd.to_numeric(group["timeslice_value"], errors="coerce").dropna()
        ranks = group[rank_column].astype("string").dropna().unique()
        complete = len(ranks) == expected_rank_count and len(values_numeric) == expected_rank_count
        rows.append(
            {
                "component": component,
                "worker_id": worker_id,
                "endpoint_url": endpoint_url,
                "timeslice_start_ns": int(start),
                "timeslice_end_ns": int(end),
                "metric": metric,
                "worker_value": _finite_float(values_numeric.sum()) if complete else None,
                "rank_sample_count": int(len(values_numeric)),
                "rank_samples_complete": bool(complete),
                "reconstruction_method": "sum of validated independent rank-local scheduler shards",
                "validation_status": "Validated reconstruction" if complete else "Unknown",
            }
        )
    long = pd.DataFrame(rows)
    if long.empty:
        return _empty_worker_timeseries()
    index_columns = ["component", "worker_id", "endpoint_url", "timeslice_start_ns", "timeslice_end_ns"]
    wide = (
        long.set_index([*index_columns, "metric"])["worker_value"]
        .unstack("metric")
        .rename(columns=metric_to_column)
    )
    wide.columns.name = None
    result = wide.reset_index()
    for column in metric_to_column.values():
        if column not in result:
            result[column] = np.nan
    result["reconstruction_method"] = "sum of validated independent rank-local scheduler shards"
    result["validation_status"] = "Validated reconstruction"
    return result.sort_values(["worker_id", "timeslice_start_ns"]).reset_index(drop=True)


def phase_bin_worker_timeseries(
    worker_series: pd.DataFrame,
    *,
    phase_start_ns: int,
    bin_ns: int = 1_000_000_000,
) -> pd.DataFrame:
    """Map raw exporter samples to phase-anchored bins without filling values."""

    if worker_series.empty:
        return worker_series.copy()
    result = worker_series.copy()
    starts = pd.to_numeric(result["timeslice_start_ns"], errors="coerce")
    result = result.loc[starts.notna()].copy()
    result["phase_second_bin"] = ((starts.loc[result.index] - phase_start_ns) // bin_ns).astype(int)
    result["phase_bin_start_ns"] = phase_start_ns + result["phase_second_bin"] * bin_ns
    result["phase_bin_end_ns"] = result["phase_bin_start_ns"] + bin_ns
    value_columns = _numeric_measurement_columns(result)
    group_keys = ["component", "worker_id", "phase_second_bin", "phase_bin_start_ns", "phase_bin_end_ns"]
    aggregations: dict[str, str] = {column: "mean" for column in value_columns}
    for column in ("endpoint_url", "reconstruction_method", "validation_status"):
        if column in result:
            aggregations[column] = "first"
    grouped = result.groupby(group_keys, dropna=False, sort=True).agg(aggregations).reset_index()
    grouped["raw_timeslice_samples_in_bin"] = (
        result.groupby(group_keys, dropna=False, sort=True).size().to_numpy()
    )
    grouped["alignment_method"] = (
        "phase-anchored 1-second bins from raw timeslice start; no nearest-neighbor, interpolation, or forward-fill"
    )
    return grouped.sort_values(["worker_id", "phase_second_bin"]).reset_index(drop=True)


def reconstruct_cluster_from_workers(
    binned_worker_series: pd.DataFrame,
    *,
    component: str,
    worker_ids: Sequence[str],
    value_columns: Sequence[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Sum independent worker gauges only at bins containing all workers.

    This returns the coarse aligned timeseries and a compact alignment summary.
    Missing a worker in a bin leaves the corresponding cluster value null.
    """

    if len(worker_ids) != 2:
        raise ValueError("this public c8 reconstruction expects exactly two independent workers")
    worker_a, worker_b = [str(worker) for worker in worker_ids]
    work = binned_worker_series.loc[
        (binned_worker_series["component"].astype("string") == component)
        & binned_worker_series["worker_id"].astype("string").isin([worker_a, worker_b])
    ].copy()
    index = ["phase_second_bin", "phase_bin_start_ns", "phase_bin_end_ns"]
    if work.empty:
        return pd.DataFrame(columns=index), pd.DataFrame()
    result = work[index].drop_duplicates().sort_values(index).reset_index(drop=True)
    for column in value_columns:
        pivot = work.pivot_table(
            index=index,
            columns="worker_id",
            values=column,
            aggfunc="first",
            observed=False,
        ).reindex(columns=[worker_a, worker_b])
        pivot.columns = [f"{column}_{worker_a}", f"{column}_{worker_b}"]
        result = result.merge(pivot.reset_index(), on=index, how="left", validate="one_to_one")
        left = pd.to_numeric(result[f"{column}_{worker_a}"], errors="coerce")
        right = pd.to_numeric(result[f"{column}_{worker_b}"], errors="coerce")
        complete = left.notna() & right.notna()
        result[f"{column}_cluster"] = np.where(complete, left + right, np.nan)
        result[f"{column}_workers_aligned"] = complete
    result["component"] = component
    result["cluster_reconstruction_method"] = (
        "sum two independent workers only in common phase-second bins; no fill/interpolation"
    )
    result["validation_status"] = "Validated reconstruction"

    summary_rows: list[dict[str, object]] = []
    for column in value_columns:
        values = pd.to_numeric(result[f"{column}_cluster"], errors="coerce").dropna()
        aligned = result[f"{column}_workers_aligned"].fillna(False)
        summary_rows.append(
            {
                "component": component,
                "metric": column,
                "worker_a": worker_a,
                "worker_b": worker_b,
                "phase_bin_count": int(len(result)),
                "common_worker_bin_count": int(aligned.sum()),
                "common_worker_bin_ratio": _safe_ratio(int(aligned.sum()), int(len(result))),
                "max": _finite_float(values.max()) if not values.empty else None,
                "p50": _quantile(values, 0.50),
                "p90": _quantile(values, 0.90),
                "p95": _quantile(values, 0.95),
                "positive_fraction": _safe_ratio(int((values > 0).sum()), int(len(values))),
                "status": "Validated reconstruction" if not values.empty else "Unknown",
                "reconstruction_method": result["cluster_reconstruction_method"].iloc[0],
            }
        )
    return result, pd.DataFrame(summary_rows)


def intersect_worker_intervals(
    worker_series: pd.DataFrame,
    *,
    component: str,
    worker_ids: Sequence[str],
    value_columns: Sequence[str],
    profile_duration_ns: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Align two endpoint gauges by actual interval intersection, with no fill.

    AIPerf's one-second exporter bins for separate endpoints can have different
    offsets.  Phase-second grouping is useful for review plots, but this
    two-pointer interval intersection is the canonical cluster calculation:
    every retained segment has explicit overlap of both raw endpoint samples.
    """

    if len(worker_ids) != 2:
        raise ValueError("this public c8 reconstruction expects exactly two independent workers")
    worker_a, worker_b = [str(worker) for worker in worker_ids]
    work = worker_series.loc[
        (worker_series["component"].astype("string") == component)
        & worker_series["worker_id"].astype("string").isin([worker_a, worker_b])
    ].copy()
    left = work.loc[work["worker_id"].astype("string") == worker_a].sort_values(
        ["timeslice_start_ns", "timeslice_end_ns"]
    )
    right = work.loc[work["worker_id"].astype("string") == worker_b].sort_values(
        ["timeslice_start_ns", "timeslice_end_ns"]
    )
    rows: list[dict[str, object]] = []
    i = 0
    j = 0
    left_records = left.to_dict(orient="records")
    right_records = right.to_dict(orient="records")
    while i < len(left_records) and j < len(right_records):
        left_row = left_records[i]
        right_row = right_records[j]
        left_start = int(left_row["timeslice_start_ns"])
        left_end = int(left_row["timeslice_end_ns"])
        right_start = int(right_row["timeslice_start_ns"])
        right_end = int(right_row["timeslice_end_ns"])
        start = max(left_start, right_start)
        end = min(left_end, right_end)
        if end > start:
            row: dict[str, object] = {
                "component": component,
                "overlap_start_ns": start,
                "overlap_end_ns": end,
                "overlap_duration_ns": end - start,
                "worker_a": worker_a,
                "worker_b": worker_b,
                "worker_a_sample_start_ns": left_start,
                "worker_a_sample_end_ns": left_end,
                "worker_b_sample_start_ns": right_start,
                "worker_b_sample_end_ns": right_end,
                "alignment_method": "exact raw endpoint timeslice interval intersection; no nearest-neighbor, interpolation, or fill",
                "validation_status": "Validated reconstruction",
            }
            for column in value_columns:
                left_value = _finite_float(left_row.get(column))
                right_value = _finite_float(right_row.get(column))
                row[f"{column}_{worker_a}"] = left_value
                row[f"{column}_{worker_b}"] = right_value
                row[f"{column}_cluster"] = (
                    left_value + right_value
                    if left_value is not None and right_value is not None
                    else None
                )
            rows.append(row)
        if left_end <= right_end:
            i += 1
        if right_end <= left_end:
            j += 1
    result = pd.DataFrame(rows)
    summary_rows: list[dict[str, object]] = []
    overlap_duration = int(result["overlap_duration_ns"].sum()) if not result.empty else 0
    for column in value_columns:
        values = pd.to_numeric(result.get(f"{column}_cluster"), errors="coerce")
        durations = pd.to_numeric(result.get("overlap_duration_ns"), errors="coerce")
        valid = values.notna() & durations.notna() & (durations > 0)
        series = values.loc[valid]
        weights = durations.loc[valid]
        summary_rows.append(
            {
                "component": component,
                "metric": column,
                "worker_a": worker_a,
                "worker_b": worker_b,
                "overlap_segment_count": int(valid.sum()),
                "common_worker_overlap_s": overlap_duration / 1e9,
                "common_worker_overlap_fraction_of_profile": _safe_ratio(
                    overlap_duration, profile_duration_ns
                ),
                "max": _finite_float(series.max()) if not series.empty else None,
                "time_weighted_mean": _weighted_mean(series, weights),
                "p50": _weighted_quantile(series, weights, 0.50),
                "p75": _weighted_quantile(series, weights, 0.75),
                "p90": _weighted_quantile(series, weights, 0.90),
                "p95": _weighted_quantile(series, weights, 0.95),
                "p99": _weighted_quantile(series, weights, 0.99),
                "positive_fraction": _weighted_fraction(series > 0, weights),
                "status": "Validated reconstruction" if not series.empty else "Unknown",
                "reconstruction_method": "sum of validated worker scheduler counts over exact endpoint interval intersections",
            }
        )
    return result, pd.DataFrame(summary_rows)


def summarize_worker_timeseries(
    worker_series: pd.DataFrame,
    *,
    value_columns: Sequence[str],
) -> pd.DataFrame:
    """Summarize reconstructed worker samples without treating null as zero."""

    rows: list[dict[str, object]] = []
    if worker_series.empty:
        return pd.DataFrame(rows)
    group_columns = ["component", "worker_id"]
    for values, group in worker_series.groupby(group_columns, dropna=False, sort=True):
        component, worker_id = values
        for column in value_columns:
            if column not in group:
                continue
            numeric = pd.to_numeric(group[column], errors="coerce").dropna()
            rows.append(
                {
                    "component": component,
                    "worker_id": worker_id,
                    "metric": column,
                    "timeslice_sample_count": int(len(numeric)),
                    "max": _finite_float(numeric.max()) if not numeric.empty else None,
                    "p50": _quantile(numeric, 0.50),
                    "p90": _quantile(numeric, 0.90),
                    "p95": _quantile(numeric, 0.95),
                    "positive_fraction": _safe_ratio(
                        int((numeric > 0).sum()), int(len(numeric))
                    ),
                    "status": "Validated reconstruction" if not numeric.empty else "Unknown",
                    "reconstruction_method": _first_non_null(group, "reconstruction_method"),
                    "notes": "Raw one-second exporter samples; no null-to-zero conversion.",
                }
            )
    return pd.DataFrame(rows)


def dynamo_sglang_crosscheck(
    dynamo: pd.DataFrame,
    sglang_workers: pd.DataFrame,
    *,
    phase_start_ns: int,
    dyn_value_column: str = "timeslice_value",
    sglang_value_column: str = "running_requests",
) -> pd.DataFrame:
    """Align Dynamo component inflight with reconstructed SGLang worker running.

    The output is descriptive: the metrics have different documented
    lifecycles.  Lag is a sampling diagnostic, not an inferred causal delay.
    """

    if dynamo.empty or sglang_workers.empty:
        return pd.DataFrame()
    dyn = dynamo.copy()
    starts = pd.to_numeric(dyn["timeslice_start_ns"], errors="coerce")
    dyn = dyn.loc[starts.notna()].copy()
    dyn["phase_second_bin"] = ((starts.loc[dyn.index] - phase_start_ns) // 1_000_000_000).astype(int)
    rows: list[dict[str, object]] = []
    for worker_id, sglang_group in sglang_workers.groupby("worker_id", dropna=False, sort=True):
        dyn_group = dyn.loc[dyn["worker_id"].astype("string") == str(worker_id)].copy()
        if dyn_group.empty:
            continue
        dyn_bin = (
            dyn_group.groupby("phase_second_bin", dropna=False)[dyn_value_column]
            .mean()
            .rename("dynamo_component_inflight")
        )
        sglang_group = sglang_group.copy()
        if "phase_second_bin" not in sglang_group:
            sglang_starts = pd.to_numeric(sglang_group["timeslice_start_ns"], errors="coerce")
            sglang_group = sglang_group.loc[sglang_starts.notna()].copy()
            sglang_group["phase_second_bin"] = (
                (sglang_starts.loc[sglang_group.index] - phase_start_ns) // 1_000_000_000
            ).astype(int)
        sg_bin = (
            sglang_group.groupby("phase_second_bin", dropna=False)[sglang_value_column]
            .mean()
            .rename("sglang_worker_running")
        )
        merged = pd.concat([dyn_bin, sg_bin], axis=1, join="inner").dropna()
        dyn_values = pd.to_numeric(merged["dynamo_component_inflight"], errors="coerce")
        sg_values = pd.to_numeric(merged["sglang_worker_running"], errors="coerce")
        rows.append(
            {
                "worker_id": worker_id,
                "component": _first_non_null(sglang_group, "component"),
                "common_phase_second_bins": int(len(merged)),
                "dynamo_metric": "dynamo_component_inflight_requests (generate endpoint)",
                "sglang_metric": "sglang:num_running_reqs supplied comparison series",
                "spearman_rho": _spearman(dyn_values, sg_values),
                "pearson_r": _pearson(dyn_values, sg_values),
                "best_lag_seconds": _best_lag(dyn_values, sg_values)[0],
                "best_lag_pearson_r": _best_lag(dyn_values, sg_values)[1],
                "dynamo_max": _finite_float(dyn_values.max()),
                "dynamo_p50": _quantile(dyn_values, 0.50),
                "dynamo_p90": _quantile(dyn_values, 0.90),
                "dynamo_p95": _quantile(dyn_values, 0.95),
                "sglang_max": _finite_float(sg_values.max()),
                "sglang_p50": _quantile(sg_values, 0.50),
                "sglang_p90": _quantile(sg_values, 0.90),
                "sglang_p95": _quantile(sg_values, 0.95),
                "same_value_fraction": float((dyn_values == sg_values).mean()) if len(merged) else None,
                "dynamo_positive_sglang_zero_count": int(
                    ((dyn_values > 0) & (sg_values == 0)).sum()
                ),
                "sglang_positive_dynamo_zero_count": int(
                    ((sg_values > 0) & (dyn_values == 0)).sum()
                ),
                "dynamo_positive_sglang_zero_fraction": float(
                    ((dyn_values > 0) & (sg_values == 0)).mean()
                )
                if len(merged)
                else None,
                "sglang_positive_dynamo_zero_fraction": float(
                    ((sg_values > 0) & (dyn_values == 0)).mean()
                )
                if len(merged)
                else None,
                "status": "Evidence",
                "interpretation": (
                    "Time-aligned descriptive cross-check only; Dynamo work-handler inflight and "
                    "SGLang scheduler running have distinct lifecycles and are not expected to equal."
                ),
            }
        )
    return pd.DataFrame(rows)


def guarded_stage_sum(
    prefill_cluster: pd.DataFrame,
    decode_cluster: pd.DataFrame,
    *,
    allow_sum: bool,
) -> pd.DataFrame:
    """Return a stage sum only if an external lifecycle guard explicitly allows it.

    The public run has no request-correlated P/D handoff chain, so callers use
    ``allow_sum=False``.  The returned Unknown is intentionally not zero.
    """

    columns = [
        "phase_second_bin",
        "phase_bin_start_ns",
        "phase_bin_end_ns",
        "prefill_cluster_running",
        "decode_cluster_running",
        "backend_stage_active_count",
        "status",
        "notes",
    ]
    if not allow_sum:
        return pd.DataFrame(
            [
                {
                    "phase_second_bin": pd.NA,
                    "phase_bin_start_ns": pd.NA,
                    "phase_bin_end_ns": pd.NA,
                    "prefill_cluster_running": pd.NA,
                    "decode_cluster_running": pd.NA,
                    "backend_stage_active_count": pd.NA,
                    "status": "Unknown",
                    "notes": (
                        "P/D handoff overlap and logical-request uniqueness are not established; "
                        "prefill + decode is withheld rather than treated as zero or unique global running."
                    ),
                }
            ],
            columns=columns,
        )
    keys = ["phase_second_bin", "phase_bin_start_ns", "phase_bin_end_ns"]
    pre = prefill_cluster.loc[:, [*keys, "running_requests_cluster"]].rename(
        columns={"running_requests_cluster": "prefill_cluster_running"}
    )
    dec = decode_cluster.loc[:, [*keys, "running_requests_cluster"]].rename(
        columns={"running_requests_cluster": "decode_cluster_running"}
    )
    result = pre.merge(dec, on=keys, how="inner", validate="one_to_one")
    result["backend_stage_active_count"] = (
        pd.to_numeric(result["prefill_cluster_running"], errors="coerce")
        + pd.to_numeric(result["decode_cluster_running"], errors="coerce")
    )
    result["status"] = "Strong inference"
    result["notes"] = "Stage-occupancy sum; not unique global running requests."
    return result[columns]


def _pairwise_correlations(pivot: pd.DataFrame) -> dict[str, float | None]:
    values: dict[str, float | None] = {}
    for left, right in combinations(pivot.columns.tolist(), 2):
        paired = pivot.loc[:, [left, right]].dropna()
        values[f"{left}~{right}"] = _pearson(paired[left], paired[right])
    return values


def _pairwise_exact_match_percent(pivot: pd.DataFrame) -> dict[str, float | None]:
    values: dict[str, float | None] = {}
    for left, right in combinations(pivot.columns.tolist(), 2):
        paired = pivot.loc[:, [left, right]].dropna()
        values[f"{left}~{right}"] = (
            float((paired[left] == paired[right]).mean() * 100.0) if not paired.empty else None
        )
    return values


def _rank_zero_exact_match_percent(pivot: pd.DataFrame) -> dict[str, float | None]:
    if "0" not in pivot.columns:
        return {}
    values: dict[str, float | None] = {}
    for rank in pivot.columns:
        if rank == "0":
            continue
        paired = pivot.loc[:, ["0", rank]].dropna()
        values[f"0~{rank}"] = (
            float((paired["0"] == paired[rank]).mean() * 100.0) if not paired.empty else None
        )
    return values


def _rank_sort_key(value: object) -> tuple[int, str]:
    text = str(value)
    try:
        return int(text), text
    except ValueError:
        return 10**9, text


def _alignment_status(
    *, observed_rank_count: int, expected_rank_count: int, complete_count: int, aligned_count: int
) -> str:
    if observed_rank_count != expected_rank_count:
        return "rank_count_mismatch"
    if aligned_count == 0:
        return "no_timeslices"
    if complete_count == aligned_count:
        return "exact_all_rank_timestamp_alignment"
    return "partial_rank_timestamp_alignment"


def _numeric_measurement_columns(frame: pd.DataFrame) -> list[str]:
    excluded = {
        "timeslice_start_ns",
        "timeslice_end_ns",
        "phase_second_bin",
        "phase_bin_start_ns",
        "phase_bin_end_ns",
    }
    return [
        column
        for column in frame.columns
        if column not in excluded
        and (pd.api.types.is_numeric_dtype(frame[column]) or column in {"running_requests", "waiting_requests"})
    ]


def _empty_worker_timeseries() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "component",
            "worker_id",
            "endpoint_url",
            "timeslice_start_ns",
            "timeslice_end_ns",
            "reconstruction_method",
            "validation_status",
        ]
    )


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    return float(numerator / denominator) if denominator else None


def _is_one(value: object) -> bool:
    number = _finite_float(value)
    return number is not None and math.isclose(number, 1.0, rel_tol=0.0, abs_tol=1e-12)


def _finite_float(value: object) -> float | None:
    try:
        numeric = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _quantile(values: pd.Series, quantile: float) -> float | None:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    return float(numeric.quantile(quantile)) if not numeric.empty else None


def _weighted_mean(values: pd.Series, weights: pd.Series) -> float | None:
    paired = pd.DataFrame({"value": values, "weight": weights}).dropna()
    paired = paired.loc[paired["weight"] > 0]
    total = float(paired["weight"].sum()) if not paired.empty else 0.0
    if total <= 0:
        return None
    return float((paired["value"] * paired["weight"]).sum() / total)


def _weighted_quantile(values: pd.Series, weights: pd.Series, quantile: float) -> float | None:
    paired = pd.DataFrame({"value": values, "weight": weights}).dropna()
    paired = paired.loc[paired["weight"] > 0].sort_values("value")
    if paired.empty:
        return None
    threshold = float(paired["weight"].sum()) * quantile
    cumulative = paired["weight"].cumsum()
    return _finite_float(paired.loc[cumulative >= threshold, "value"].iloc[0])


def _weighted_fraction(condition: pd.Series, weights: pd.Series) -> float | None:
    paired = pd.DataFrame({"condition": condition, "weight": weights}).dropna()
    paired = paired.loc[paired["weight"] > 0]
    total = float(paired["weight"].sum()) if not paired.empty else 0.0
    if total <= 0:
        return None
    return float(paired.loc[paired["condition"].astype(bool), "weight"].sum() / total)


def _first_non_null(frame: pd.DataFrame, column: str) -> str | None:
    if column not in frame:
        return None
    values = frame[column].dropna().astype(str)
    return values.iloc[0] if not values.empty else None


def _pearson(left: pd.Series, right: pd.Series) -> float | None:
    paired = pd.concat([left, right], axis=1).dropna()
    if len(paired) < 2 or paired.iloc[:, 0].nunique() < 2 or paired.iloc[:, 1].nunique() < 2:
        return None
    return _finite_float(paired.iloc[:, 0].corr(paired.iloc[:, 1], method="pearson"))


def _spearman(left: pd.Series, right: pd.Series) -> float | None:
    paired = pd.concat([left, right], axis=1).dropna()
    if len(paired) < 2 or paired.iloc[:, 0].nunique() < 2 or paired.iloc[:, 1].nunique() < 2:
        return None
    statistic = spearmanr(paired.iloc[:, 0], paired.iloc[:, 1]).statistic
    return _finite_float(statistic)


def _best_lag(left: pd.Series, right: pd.Series) -> tuple[int | None, float | None]:
    best_lag: int | None = None
    best_value: float | None = None
    for lag in range(-5, 6):
        # Positive lag shifts the right series later relative to the left.
        value = _pearson(left, right.shift(lag))
        if value is None:
            continue
        if best_value is None or abs(value) > abs(best_value):
            best_lag = lag
            best_value = value
    return best_lag, best_value
