import json

import pandas as pd

from h200_agentx_analysis.metrics import filter_profile_records


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "benchmark_phase": "profiling",
        "error_present": False,
        "was_cancelled": False,
        "input_tokens": 10,
        "output_tokens": 2,
        "ttft_ms": 10.0,
        "e2e_ms": 20.0,
        "itl_ms": 5.0,
    }
    row.update(overrides)
    return row


def test_profile_filter_retains_only_successful_profiling_records() -> None:
    frame = pd.DataFrame(
        [
            _row(),
            _row(benchmark_phase="warmup"),
            _row(error_present=True),
            _row(was_cancelled=True),
            _row(input_tokens=-1),
        ]
    )
    included, excluded = filter_profile_records(frame)
    assert len(included) == 1
    assert set(excluded["exclusion_reason"]) == {
        "not_profiling_phase",
        "error_present",
        "was_cancelled",
        "negative_token_count",
    }


def test_missing_phase_defaults_to_source_compatible_legacy_profiling() -> None:
    frame = pd.DataFrame([_row(benchmark_phase=None)])
    included, excluded = filter_profile_records(frame)
    assert len(included) == 1
    assert excluded.empty
    strict_included, strict_excluded = filter_profile_records(
        frame, missing_phase_is_profiling=False
    )
    assert strict_included.empty
    assert strict_excluded.iloc[0]["exclusion_reason"] == "missing_benchmark_phase"


def test_h200_builder_parses_pinned_aiperf_shape_and_writes_filter_outputs(tmp_path) -> None:
    from h200_agentx_analysis.h200_io import build_h200_request_tables

    profile = tmp_path / "raw" / "conc1" / "raw_agentic" / "profile_export.jsonl"
    profile.parent.mkdir(parents=True)

    def record(phase="profiling", error=None, cancelled=False):
        metadata = {
            "session_num": 0,
            "conversation_id": "trace-a::sa:agent:fa:000",
            "turn_index": 2,
            "request_start_ns": 1_000_000_000,
            "request_ack_ns": 1_100_000_000,
            "request_end_ns": 2_000_000_000,
            "worker_id": "worker-1",
            "was_cancelled": cancelled,
        }
        if phase is not None:
            metadata["benchmark_phase"] = phase
        return {
            "metadata": metadata,
            "metrics": {
                "input_sequence_length": {"value": 100, "unit": "tokens"},
                "output_sequence_length": {"value": 10, "unit": "tokens"},
                "time_to_first_token": {"value": 20.0, "unit": "ms"},
                "request_latency": {"value": 200.0, "unit": "ms"},
                "inter_token_latency": {"value": 10.0, "unit": "ms"},
            },
            "error": error,
        }

    profile.write_text(
        "\n".join(
            json.dumps(item)
            for item in [
                record(),
                record(phase="warmup"),
                record(error={"type": "server_error"}),
                record(cancelled=True),
                record(phase=None),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "processed"
    result = build_h200_request_tables(
        profile.parents[2],
        output,
        github_run_id=29820102138,
        expected_environment={"target_model": "GLM-5.2 FP8", "hardware": "H200", "total_gpus": 16},
    )
    all_rows = pd.read_parquet(output / "h200_requests_all.parquet")
    profiled = pd.read_parquet(output / "h200_requests_profiled.parquet")
    assert result.all_record_count == 5
    assert result.profiled_record_count == 2
    assert len(all_rows) == 5
    assert len(profiled) == 2
    assert set(all_rows.loc[~all_rows["is_profiled_valid"], "exclusion_reason"]) == {
        "not_profiling_phase",
        "error_present",
        "was_cancelled",
    }
    assert set(profiled["root_trace_id"]) == {"trace-a"}
    assert set(profiled["branch_type"]) == {"fanout"}
    assert profiled.loc[0, "ttft_ms"] == 20.0


def test_nested_metric_unit_is_used_before_field_name_default() -> None:
    from h200_agentx_analysis.artifact_parser import normalize_profile_record

    row = normalize_profile_record(
        {
            "metadata": {"benchmark_phase": "profiling"},
            "metrics": {
                "time_to_first_token": {"value": 1.25, "unit": "s"},
                "request_latency": {"value": 750_000, "unit": "us"},
                "inter_token_latency": {"value": 10_000_000, "unit": "ns"},
            },
        }
    )
    assert row["ttft_ms"] == 1250.0
    assert row["e2e_ms"] == 750.0
    assert row["itl_ms"] == 10.0


def test_parser_preserves_integer_nanosecond_timestamp_and_source_metadata() -> None:
    from h200_agentx_analysis.artifact_parser import normalize_profile_record

    timestamp_ns = 1_784_630_947_472_644_248
    row = normalize_profile_record(
        {
            "metadata": {
                "source_trace_id": "source-root",
                "source_outer_idx": 17,
                "source_inner_idx": 3,
                "request_start_ns": timestamp_ns,
            }
        }
    )
    assert row["request_start_ns"] == timestamp_ns
    assert row["source_trace_id"] == "source-root"
    assert row["source_outer_idx"] == 17
    assert row["source_inner_idx"] == 3


def test_schema_inventory_observes_sibling_metric_units(tmp_path) -> None:
    from h200_agentx_analysis.artifact_parser import profile_schema_inventory

    profile = tmp_path / "profile_export.jsonl"
    profile.write_text(
        json.dumps(
            {
                "metrics": {
                    "input_sequence_length": {"value": 10, "unit": "tokens"},
                    "output_sequence_length": {"value": 2, "unit": "tokens"},
                    "time_to_first_token": {"value": 12.5, "unit": "ms"},
                    "request_latency": {"value": 20.0, "unit": "ms"},
                    "inter_token_latency": {"value": 3.0, "unit": "ms"},
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )
    rows, metrics, issues = profile_schema_inventory([profile])
    assert not issues
    by_field = {row["field_name"]: row for row in rows}
    assert by_field["metrics.time_to_first_token.value"]["observed_unit"] == "ms"
    assert by_field["metrics.time_to_first_token.value"]["inferred_unit"] == "ms"
    assert by_field["metrics.input_sequence_length.value"]["observed_unit"] == "tokens"
    assert by_field["metrics.output_sequence_length.value"]["unit_value_present_count"] == 1
    metric_by_field = {row["field_name"]: row for row in metrics}
    assert metric_by_field["metrics.inter_token_latency.value"]["observed_unit_values"] == "ms"
