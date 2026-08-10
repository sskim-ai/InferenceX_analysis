from __future__ import annotations

import pandas as pd

from h200_agentx_analysis.mtp_study import (
    add_requested_id_coverage,
    add_source_metadata_join,
    build_pair_table,
    extract_mtp_profile_record,
    requested_id_resolution,
    summarize_requests,
)


def _record(*, include_itl: bool = True) -> dict:
    metrics = {
        "input_sequence_length": {"value": 10, "unit": "tokens"},
        "usage_prompt_tokens": {"value": 10, "unit": "tokens"},
        "usage_prompt_cache_read_tokens": {"value": 8, "unit": "tokens"},
        "output_sequence_length": {"value": 5, "unit": "tokens"},
        "time_to_first_token": {"value": 100, "unit": "ms"},
        "request_latency": {"value": 140, "unit": "ms"},
        "decode_duration": {"value": 40, "unit": "ms"},
    }
    if include_itl:
        metrics["inter_token_latency"] = {"value": 10, "unit": "ms"}
    return {
        "metadata": {
            "conversation_id": "abc::sa:agent_1",
            "source_trace_id": "abc",
            "source_outer_idx": 4,
            "session_num": 1,
            "turn_index": 9,
            "request_start_ns": 10,
            "request_end_ns": 150,
            "benchmark_phase": "profiling",
            "was_cancelled": False,
        },
        "metrics": metrics,
    }


def test_usage_prompt_does_not_claim_logical_prompt_semantics() -> None:
    row = extract_mtp_profile_record(_record(), context={}, source_file="fixture", record_ordinal=1)
    assert row["input_sequence_length"] == 10
    assert row["usage_prompt_tokens"] == 10
    assert row["logical_prompt_tokens"] is None
    assert row["cache_read_tokens"] == 8
    assert row["new_prompt_tokens"] is None
    assert row["itl_ms"] == 10


def test_decode_duration_derives_itl_when_no_direct_metric_exists() -> None:
    row = extract_mtp_profile_record(
        _record(include_itl=False), context={}, source_file="fixture", record_ordinal=1
    )
    assert row["itl_ms"] == 10
    assert row["source_metric_name"] == "decode_duration"
    assert str(row["raw_itl_field"]).startswith("derived:")


def test_source_metadata_join_preserves_source_provenance_without_input_equivalence() -> None:
    h200 = pd.DataFrame(
        [
            {
                "root_trace_id": "abc",
                "source_trace_id": "abc",
                "source_outer_idx": 4,
                "source_inner_idx": None,
                "input_sequence_length": 1,
            }
        ]
    )
    source = pd.DataFrame(
        [
            {
                "root_trace_id": "abc",
                "source_outer_request_index": 4,
                "source_inner_request_index": None,
                "source_conversation_path": "abc",
                "source_branch_type": "root",
                "source_branch_request_index": 4,
                "source_input_tokens": 100,
            }
        ]
    )
    result = add_source_metadata_join(h200, source, {"abc"})
    assert result.loc[0, "match_class"] == "loader_metadata_turn_match"
    assert bool(result.loc[0, "loader_metadata_turn_match"])
    assert not bool(result.loc[0, "loader_metadata_input_tokens_match"])
    assert result.loc[0, "exact_source_key"] == "abc|4|-1"


def test_summary_uses_transition_weighted_itl_and_wall_rate() -> None:
    frame = pd.DataFrame(
        {
            "root_trace_id": ["a", "a"],
            "worker_id": ["w", "w"],
            "input_sequence_length": [10, 10],
            "usage_prompt_tokens": [10, 10],
            "output_tokens": [3, 5],
            "ttft_ms": [10, 20],
            "itl_ms": [10, 20],
            "e2e_ms": [30, 100],
            "request_start_ns": [0, 10],
            "request_end_ns": [30_000_000_000, 40_000_000_000],
        }
    )
    result = summarize_requests(frame)
    assert result["itl_weighted_ms"] == (10 * 2 + 20 * 4) / 6
    assert result["weighted_decode_tps"] == 1000 / result["itl_weighted_ms"]
    assert result["wall_output_tps"] == 8 / 40


def test_requested_prefix_resolution_and_pairing_are_conservative() -> None:
    profile = pd.DataFrame(
        {
            "concurrency": [8, 12],
            "root_trace_id": ["07dd405full", "07dd405full"],
            "exact_source_key": ["07dd405full|1|-1", "07dd405full|1|-1"],
            "ttft_ms": [10, 20],
            "itl_ms": [2, 4],
            "e2e_ms": [20, 40],
            "output_tokens": [3, 3],
            "input_sequence_length": [5, 5],
        }
    )
    resolution = requested_id_resolution(profile, source_ids={"07dd405full"})
    id03 = resolution.loc[resolution["id_label"] == "ID03"].iloc[0]
    assert id03["resolution_status"] == "unique"
    assert bool(id03["present_c8"])
    pairs = build_pair_table(profile)
    assert len(pairs) == 1
    assert pairs.loc[0, "ttft_ratio_right_over_left"] == 2
    assert bool(pairs.loc[0, "strict_decode_subset"])


def test_requested_id_coverage_distinguishes_warmup_from_successful_profile() -> None:
    raw = pd.DataFrame(
        {
            "concurrency": [8, 8],
            "root_trace_id": ["07dd405full", "07dd405full"],
            "benchmark_phase": ["warmup", "profiling"],
            "error_present": [False, False],
            "was_cancelled": [False, False],
        }
    )
    profiled = raw.iloc[[1]].copy()
    resolution = requested_id_resolution(profiled, source_ids={"07dd405full"})
    result = add_requested_id_coverage(resolution, raw_all=raw, profiled=profiled)
    row = result.loc[result["id_label"] == "ID03"].iloc[0]
    assert row["all_request_count_c8"] == 2
    assert row["warmup_request_count_c8"] == 1
    assert row["successful_profile_request_count_c8"] == 1
    assert bool(row["present_c8"])
