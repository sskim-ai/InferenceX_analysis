from __future__ import annotations

import importlib.util
import tarfile
from io import BytesIO
from pathlib import Path

import pandas as pd

from h200_agentx_analysis.concurrency_reconstruction import (
    observed_scheduler_counter_summary,
    parse_scheduler_counter_line,
    reconstruct_http_inflight,
    summarize_http_inflight,
    time_weighted_quantile,
)


def _reconstruction_script_module() -> object:
    path = Path(__file__).resolve().parents[1] / "scripts/h200_gpu_resident_mtp/reconstruct_c8_concurrency.py"
    spec = importlib.util.spec_from_file_location("reconstruct_c8_concurrency_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _request(
    start: int,
    end: int,
    branch: str = "root",
    *,
    label: str = "request",
) -> dict[str, object]:
    return {
        "label": label,
        "request_start_ns": start,
        "request_end_ns": end,
        "source_branch_type": branch,
    }


def test_interval_sweep_uses_start_inclusive_end_exclusive_semantics() -> None:
    frame = pd.DataFrame(
        [
            _request(0, 10, "root", label="first"),
            _request(10, 20, "subagent main", label="second"),
        ]
    )

    result = reconstruct_http_inflight(frame)
    at_ten = result.timeline.loc[result.timeline["timestamp_ns"] == 10]

    assert at_ten["event_type"].tolist() == ["end", "start"]
    assert at_ten["inflight_after_event"].tolist() == [0, 1]
    second = result.requests.loc[result.requests["label"] == "second"].iloc[0]
    assert second["system_inflight_before_start"] == 0
    assert second["system_inflight_at_start"] == 1
    assert second["root_inflight_at_start"] == 0
    assert second["subagent_inflight_at_start"] == 1


def test_same_timestamp_starts_receive_one_non_arbitrary_context() -> None:
    frame = pd.DataFrame(
        [
            _request(0, 20, "root", label="existing"),
            _request(10, 30, "root", label="a"),
            _request(10, 40, "subagent main", label="b"),
        ]
    )

    result = reconstruct_http_inflight(frame)
    simultaneous = result.requests.loc[result.requests["label"].isin(["a", "b"])]

    # Both requests include themselves and the other simultaneous start.
    assert simultaneous["system_inflight_before_start"].tolist() == [1, 1]
    assert simultaneous["system_inflight_at_start"].tolist() == [3, 3]
    assert simultaneous["root_inflight_at_start"].tolist() == [2, 2]
    assert simultaneous["subagent_inflight_at_start"].tolist() == [1, 1]


def test_time_weighted_summary_is_not_request_start_sampled() -> None:
    frame = pd.DataFrame(
        [
            _request(0, 100, "root", label="long"),
            _request(0, 10, "subagent main", label="short"),
        ]
    )

    summary = summarize_http_inflight(reconstruct_http_inflight(frame))

    # Two requests are active for 10 ns, then only one for 90 ns.
    assert summary["max_inflight"] == 2
    assert summary["time_weighted_mean_inflight"] == 1.1
    assert summary["time_weighted_p50_inflight"] == 1.0
    assert summary["time_weighted_p90_inflight"] == 1.0
    assert summary["request_start_sampled_mean_inflight"] == 2.0


def test_root_and_subagent_overlap_are_separate_from_total_http_overlap() -> None:
    frame = pd.DataFrame(
        [
            _request(0, 30, "root", label="root"),
            _request(5, 20, "subagent main", label="subagent"),
            _request(10, 15, "fan-out agent", label="fanout"),
        ]
    )

    summary = summarize_http_inflight(reconstruct_http_inflight(frame))

    assert summary["max_inflight"] == 3
    assert summary["max_root_inflight"] == 1
    assert summary["max_subagent_inflight"] == 2


def test_id03_style_request_key_is_retained_with_start_load_context() -> None:
    frame = pd.DataFrame(
        [
            {
                **_request(0, 40, "root", label="first"),
                "exact_source_key": "07dd40536557a1d6440a923557c3129dc929|3|-1",
            },
            {
                **_request(10, 20, "subagent main", label="second"),
                "exact_source_key": "07dd40536557a1d6440a923557c3129dc929|4|0",
            },
        ]
    )

    enriched = reconstruct_http_inflight(frame).requests.set_index("exact_source_key")

    assert enriched.loc["07dd40536557a1d6440a923557c3129dc929|3|-1", "system_inflight_at_start"] == 1
    assert enriched.loc["07dd40536557a1d6440a923557c3129dc929|4|0", "system_inflight_at_start"] == 2


def test_invalid_or_missing_intervals_are_excluded_not_assumed_zero() -> None:
    frame = pd.DataFrame(
        [
            _request(0, 10, "root", label="valid"),
            _request(10, 10, "root", label="zero"),
            _request(20, 15, "root", label="negative"),
            _request(30, None, "root", label="missing"),
        ]
    )

    result = reconstruct_http_inflight(frame)
    summary = summarize_http_inflight(result)

    assert summary["valid_interval_request_count"] == 1
    assert summary["invalid_interval_request_count"] == 3
    assert result.invalid_requests["interval_invalid_reason"].tolist() == [
        "nonpositive_request_interval",
        "nonpositive_request_interval",
        "missing_request_end_ns",
    ]


def test_time_weighted_quantile_uses_duration_not_row_count() -> None:
    assert time_weighted_quantile([1, 9], [99, 1], 0.95) == 1.0
    assert time_weighted_quantile([1, 9], [99, 1], 0.99) == 1.0
    assert time_weighted_quantile([1, 9], [99, 1], 0.995) == 9.0


def test_scheduler_parser_distinguishes_configured_limit_from_observed_counter() -> None:
    configured = parse_scheduler_counter_line("max_running_requests=200")
    configured_spaced = parse_scheduler_counter_line("max running requests: 32")
    observed = parse_scheduler_counter_line("scheduler running_requests=7 waiting_reqs: 2")

    assert configured == [
        {
            "candidate_metric_name": "configured_max_running_requests",
            "value": 200.0,
            "metric_scope_interpretation": "configured capacity; not an observed runtime scheduler count",
            "is_observed_runtime_counter": False,
            "classification": "Evidence",
        }
    ]
    assert [candidate["candidate_metric_name"] for candidate in observed] == [
        "running_requests",
        "waiting_requests",
    ]
    assert all(candidate["is_observed_runtime_counter"] for candidate in observed)
    assert [candidate["candidate_metric_name"] for candidate in configured_spaced] == [
        "configured_max_running_requests"
    ]


def test_missing_scheduler_counter_is_unknown_not_zero() -> None:
    configured_only = parse_scheduler_counter_line("max_running_requests=32")

    summary = observed_scheduler_counter_summary(configured_only)

    assert summary["observed_running_metric_available"] == "no"
    assert summary["max_observed_running"] is None
    assert summary["observed_running_status"] == "Unknown"
    assert summary["observed_waiting_metric_available"] == "no"
    assert summary["max_observed_waiting"] is None
    assert summary["observed_waiting_status"] == "Unknown"


def test_frontend_log_fixture_preserves_routing_and_long_wait_checkpoint(tmp_path: Path) -> None:
    module = _reconstruction_script_module()
    archive_path = tmp_path / "server_logs.tar.gz"
    log = (
        b"2026-08-08T04:51:24.454472Z request completed request_id=a1b2-c3 "
        b'x_request_id="d4e5-f6" prefill_worker_id=2787 decode_worker_id=2792\n'
        b"2026-08-08T04:51:25.454472Z dynamo_kv_router::scheduling::queue: "
        b'refreshed overlap scores after long queue wait request_id="a1b2-c3" wait_ms=13932\n'
    )
    with tarfile.open(archive_path, "w:gz") as archive:
        member = tarfile.TarInfo("./worker-8_frontend_0.out")
        member.size = len(log)
        archive.addfile(member, BytesIO(log))

    parsed = module._parse_frontend_log_archive(archive_path)

    completion = parsed["completions"].iloc[0]
    assert completion["x_request_id"] == "d4e5-f6"
    assert completion["prefill_worker_id"] == "2787"
    assert completion["decode_worker_id"] == "2792"
    assert completion["router_queue_wait_checkpoint_max_ms"] == 13932.0


def test_histogram_percentile_estimates_are_not_misread_as_gauge_columns() -> None:
    module = _reconstruction_script_module()
    payload = {
        "description": "Histogram of queueing time in seconds.",
        "series": [
            {
                "endpoint_url": "http://prefill.example/metrics",
                "labels": {"dynamo_component": "prefill", "worker_id": "worker-a"},
                "stats": {
                    "count": 3,
                    "avg": 1.5,
                    "p50_estimate": 0.01,
                    "p90_estimate": 2.0,
                    "p95_estimate": 4.0,
                    "p99_estimate": 8.0,
                },
                "timeslices": [],
            }
        ],
    }

    rows, timeline = module._payload_rows(
        "sglang:queue_time_seconds", payload, profile_start_ns=0, profile_end_ns=100
    )

    assert timeline == []
    assert rows[0]["p50"] == 0.01
    assert rows[0]["p90"] == 2.0
    assert rows[0]["p95"] == 4.0
    assert rows[0]["p99"] == 8.0
