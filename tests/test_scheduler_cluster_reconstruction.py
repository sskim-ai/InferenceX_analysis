from __future__ import annotations

import pandas as pd

from h200_agentx_analysis.scheduler_cluster_reconstruction import (
    aggregate_rank_shards,
    deduplicate_rank_gauges,
    dynamo_sglang_crosscheck,
    guarded_stage_sum,
    intersect_worker_intervals,
    prefill_duplicate_verdict,
    rank_envelope_timeseries,
    rank_series_validation,
)


def _rank_rows(
    *,
    component: str,
    worker: str,
    metric: str,
    rank_column: str,
    values: list[list[int]],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for timestamp, rank_values in enumerate(values):
        for rank, value in enumerate(rank_values):
            rows.append(
                {
                    "component": component,
                    "worker_id": worker,
                    "endpoint_url": f"http://{worker}/metrics",
                    "metric": metric,
                    rank_column: str(rank),
                    "timeslice_start_ns": timestamp * 10,
                    "timeslice_end_ns": (timestamp + 1) * 10,
                    "timeslice_value": value,
                }
            )
    return pd.DataFrame(rows)


def test_tp_rank_validation_requires_timestamp_level_exact_equality() -> None:
    frame = _rank_rows(
        component="prefill",
        worker="prefill-a",
        metric="sglang:num_running_reqs",
        rank_column="tp_rank",
        values=[[2] * 8, [2, 2, 2, 2, 3, 2, 2, 2]],
    )

    result = rank_series_validation(frame, rank_column="tp_rank").iloc[0]

    assert result["aligned_timeslice_count"] == 2
    assert result["all_8_ranks_exactly_equal_count"] == 1
    assert result["all_8_ranks_exactly_equal_ratio"] == 0.5
    assert result["overall_max_rank_difference"] == 1.0
    assert result["timestamp_alignment_status"] == "exact_all_rank_timestamp_alignment"


def test_prefill_envelope_does_not_turn_rank_values_into_a_worker_sum() -> None:
    frame = _rank_rows(
        component="prefill",
        worker="prefill-a",
        metric="sglang:num_running_reqs",
        rank_column="tp_rank",
        values=[[2] * 8],
    )

    envelope = rank_envelope_timeseries(
        frame,
        rank_column="tp_rank",
        metric_to_column={"sglang:num_running_reqs": "running_requests"},
        expected_rank_count=8,
    )

    assert envelope.iloc[0]["running_requests_rank_min"] == 2.0
    assert envelope.iloc[0]["running_requests_rank_median"] == 2.0
    assert envelope.iloc[0]["running_requests_rank_max"] == 2.0
    assert "no rank sum" in envelope.iloc[0]["reconstruction_method"]
    assert envelope.iloc[0]["validation_status"] == "Strong inference"


def test_prefill_duplicate_guard_needs_source_semantics_and_exact_values() -> None:
    frame = _rank_rows(
        component="prefill",
        worker="prefill-a",
        metric="sglang:num_running_reqs",
        rank_column="tp_rank",
        values=[[1] * 8, [1, 1, 1, 2, 1, 1, 1, 1]],
    )
    validation = rank_series_validation(frame, rank_column="tp_rank")

    verdict = prefill_duplicate_verdict(
        validation,
        required_metrics=("sglang:num_running_reqs",),
        source_semantics_verified=False,
    ).iloc[0]

    assert verdict["verdict"] == "unresolved"
    assert verdict["status"] == "Unknown"


def test_strict_worker_gauge_dedup_drops_a_mismatched_rank_timeslice() -> None:
    frame = _rank_rows(
        component="prefill",
        worker="prefill-a",
        metric="sglang:num_running_reqs",
        rank_column="tp_rank",
        values=[[2] * 8, [2, 2, 2, 3, 2, 2, 2, 2]],
    )

    result = deduplicate_rank_gauges(
        frame,
        rank_column="tp_rank",
        metric_to_column={"sglang:num_running_reqs": "running_requests"},
        expected_rank_count=8,
        accepted_workers=("prefill-a",),
    ).sort_values("timeslice_start_ns")

    assert result.iloc[0]["running_requests"] == 2.0
    assert pd.isna(result.iloc[1]["running_requests"])


def test_decode_dp_sum_requires_complete_rank_grid() -> None:
    complete = _rank_rows(
        component="decode",
        worker="decode-a",
        metric="sglang:num_running_reqs",
        rank_column="dp_rank",
        values=[[1] * 8],
    )
    missing = complete.loc[complete["dp_rank"] != "7"].copy()
    frame = pd.concat([complete, missing.assign(timeslice_start_ns=10, timeslice_end_ns=20)])

    result = aggregate_rank_shards(
        frame,
        rank_column="dp_rank",
        metric_to_column={"sglang:num_running_reqs": "running_requests"},
        expected_rank_count=8,
        accepted_workers=("decode-a",),
    ).sort_values("timeslice_start_ns")

    assert result.iloc[0]["running_requests"] == 8.0
    assert pd.isna(result.iloc[1]["running_requests"])


def test_rank_shard_sum_requires_a_semantically_approved_worker() -> None:
    frame = _rank_rows(
        component="decode",
        worker="decode-a",
        metric="sglang:num_running_reqs",
        rank_column="dp_rank",
        values=[[1] * 8],
    )

    result = aggregate_rank_shards(
        frame,
        rank_column="dp_rank",
        metric_to_column={"sglang:num_running_reqs": "running_requests"},
        expected_rank_count=8,
        accepted_workers=(),
    )

    assert result.empty


def test_rank_validation_keeps_missing_rank_samples_visible() -> None:
    frame = _rank_rows(
        component="decode",
        worker="decode-a",
        metric="sglang:num_running_reqs",
        rank_column="dp_rank",
        values=[[1] * 8],
    )
    frame = frame.loc[frame["dp_rank"] != "7"].copy()

    result = rank_series_validation(frame, rank_column="dp_rank").iloc[0]

    assert result["observed_rank_count"] == 7
    assert result["complete_expected_rank_timeslice_count"] == 0
    assert result["timestamp_alignment_status"] == "rank_count_mismatch"


def test_exact_endpoint_interval_intersection_has_no_nearest_neighbor_fill() -> None:
    rows = pd.DataFrame(
        [
            {
                "component": "decode",
                "worker_id": "a",
                "timeslice_start_ns": 0,
                "timeslice_end_ns": 10,
                "running_requests": 2,
                "waiting_requests": 0,
            },
            {
                "component": "decode",
                "worker_id": "a",
                "timeslice_start_ns": 10,
                "timeslice_end_ns": 20,
                "running_requests": 4,
                "waiting_requests": 0,
            },
            {
                "component": "decode",
                "worker_id": "b",
                "timeslice_start_ns": 5,
                "timeslice_end_ns": 15,
                "running_requests": 3,
                "waiting_requests": 0,
            },
        ]
    )

    timeline, summary = intersect_worker_intervals(
        rows,
        component="decode",
        worker_ids=("a", "b"),
        value_columns=("running_requests", "waiting_requests"),
        profile_duration_ns=20,
    )

    assert timeline["overlap_duration_ns"].tolist() == [5, 5]
    assert timeline["running_requests_cluster"].tolist() == [5.0, 7.0]
    running = summary.loc[summary["metric"] == "running_requests"].iloc[0]
    assert running["max"] == 7.0
    assert running["common_worker_overlap_fraction_of_profile"] == 0.5


def test_guarded_prefill_decode_sum_leaves_unknown_as_unknown() -> None:
    result = guarded_stage_sum(pd.DataFrame(), pd.DataFrame(), allow_sum=False).iloc[0]

    assert pd.isna(result["backend_stage_active_count"])
    assert result["status"] == "Unknown"


def test_dynamo_sglang_crosscheck_aligns_only_same_worker_phase_bins() -> None:
    dynamo = pd.DataFrame(
        [
            {
                "worker_id": "decode-a",
                "timeslice_start_ns": 0,
                "timeslice_end_ns": 1_000_000_000,
                "timeslice_value": 1,
            },
            {
                "worker_id": "decode-a",
                "timeslice_start_ns": 1_000_000_000,
                "timeslice_end_ns": 2_000_000_000,
                "timeslice_value": 2,
            },
            {
                "worker_id": "other-worker",
                "timeslice_start_ns": 0,
                "timeslice_end_ns": 1_000_000_000,
                "timeslice_value": 99,
            },
        ]
    )
    sglang = pd.DataFrame(
        [
            {
                "component": "decode",
                "worker_id": "decode-a",
                "timeslice_start_ns": 0,
                "timeslice_end_ns": 1_000_000_000,
                "running_requests": 1,
            },
            {
                "component": "decode",
                "worker_id": "decode-a",
                "timeslice_start_ns": 1_000_000_000,
                "timeslice_end_ns": 2_000_000_000,
                "running_requests": 2,
            },
        ]
    )

    result = dynamo_sglang_crosscheck(dynamo, sglang, phase_start_ns=0).iloc[0]

    assert result["worker_id"] == "decode-a"
    assert result["common_phase_second_bins"] == 2
    assert result["dynamo_max"] == 2.0
