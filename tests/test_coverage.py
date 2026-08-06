import importlib.util
import json
from pathlib import Path

import pandas as pd

from h200_agentx_analysis.coverage import build_coverage_summary, build_id_coverage_matrix
from h200_agentx_analysis.paired_analysis import build_paired_turn_comparisons
from h200_agentx_analysis.per_id_analysis import (
    summarize_id_concurrency,
    summarize_session_num_grouping,
    summarize_source_branch_origins,
)


def test_coverage_matrix_keeps_unobserved_source_ids_and_replay_rows() -> None:
    profiled = pd.DataFrame(
        [
            {"root_trace_id": "a", "concurrency": 1},
            {"root_trace_id": "a", "concurrency": 1},
            {"root_trace_id": "b", "concurrency": 2},
            {"root_trace_id": "unmatched", "concurrency": 2},
        ]
    )
    matrix = build_id_coverage_matrix(profiled, source_ids={"a", "b", "c"}, concurrencies=[1, 2])
    matrix = matrix.set_index("root_trace_id")
    assert matrix.loc["a", "conc1"] == 2
    assert matrix.loc["b", "conc2"] == 1
    assert matrix.loc["c", ["conc1", "conc2"]].sum() == 0
    assert "unmatched" in matrix.index


def test_coverage_summary_counts_root_subagent_and_unmatched_ids() -> None:
    all_rows = pd.DataFrame(
        [
            {
                "concurrency": 1,
                "root_trace_id": "a",
                "conversation_id": "a",
                "session_num": 1,
                "branch_type": "root",
                "benchmark_phase": "profiling",
                "error_present": False,
                "was_cancelled": False,
                "input_tokens": 1,
                "output_tokens": 2,
            },
            {
                "concurrency": 1,
                "root_trace_id": "x",
                "conversation_id": "x::sa:s",
                "session_num": 1,
                "branch_type": "subagent_main",
                "benchmark_phase": "warmup",
                "error_present": True,
                "was_cancelled": True,
                "input_tokens": 1,
                "output_tokens": 2,
            },
        ]
    )
    profiled = all_rows.iloc[[0]].copy()
    summary = build_coverage_summary(all_rows, profiled, source_ids={"a", "b"}, concurrencies=[1])
    row = summary.iloc[0]
    assert row["distinct_root_ids"] == 1
    assert row["matched_root_ids"] == 1
    assert row["root_request_count"] == 1
    assert row["error_count"] == 1
    assert row["cancellation_count"] == 1


def test_unknown_branch_type_is_not_folded_into_subagent_counts() -> None:
    profiled = pd.DataFrame(
        [
            {
                "concurrency": 1,
                "root_trace_id": "a",
                "conversation_id": "a::unexpected",
                "session_num": 1,
                "branch_type": "unknown",
                "input_tokens": 1,
                "output_tokens": 2,
            }
        ]
    )
    summary = build_coverage_summary(profiled, profiled, source_ids={"a"}, concurrencies=[1])
    row = summary.iloc[0]
    assert row["root_request_count"] == 0
    assert row["subagent_request_count"] == 0
    assert row["unknown_branch_request_count"] == 1


def test_replay_suffix_taxonomy_is_separate_from_source_agent_origin() -> None:
    profiled = pd.DataFrame(
        [
            {
                "concurrency": 1,
                "root_trace_id": "a",
                "conversation_id": "a::fa:000",
                "session_num": 1,
                "branch_type": "fanout",
                "source_branch_type": "root",
                "input_tokens": 1,
                "output_tokens": 2,
            },
            {
                "concurrency": 1,
                "root_trace_id": "a",
                "conversation_id": "a::sa:agent::aux:000",
                "session_num": 2,
                "branch_type": "auxiliary",
                "source_branch_type": "subagent",
                "input_tokens": 1,
                "output_tokens": 2,
            },
        ]
    )
    coverage = build_coverage_summary(profiled, profiled, source_ids={"a"}, concurrencies=[1])
    row = coverage.iloc[0]
    assert row["replay_nonroot_branch_request_count"] == 2
    assert row["source_origin_root_request_count"] == 1
    assert row["source_origin_subagent_request_count"] == 1
    # Compatibility count is explicitly replay-suffix based, not source origin.
    assert row["subagent_request_count"] == 2

    source_origin = summarize_source_branch_origins(profiled, all_frame=profiled)
    assert set(source_origin["source_origin_branch_type"]) == {"root", "subagent"}
    id_summary = summarize_id_concurrency(profiled, all_frame=profiled)
    assert id_summary.loc[0, "source_origin_root_request_count"] == 1
    assert id_summary.loc[0, "source_origin_subagent_request_count"] == 1


def test_session_num_grouping_does_not_claim_independent_replays() -> None:
    profiled = pd.DataFrame(
        [
            {"concurrency": 1, "root_trace_id": "a", "session_num": 10},
            {"concurrency": 1, "root_trace_id": "a", "session_num": 11},
        ]
    )
    diagnostics = summarize_session_num_grouping(profiled)
    all_rows = diagnostics.loc[diagnostics["scope"] == "all_profiled_rows"].iloc[0]
    assert all_rows["session_num_unique_row_rate"] == 1.0
    assert all_rows["replay_instance_identity_status"] == "unvalidated_session_num_group"
    assert all_rows["cross_concurrency_cluster_unit"] == "root_trace_id"


def test_paired_subset_requires_explicit_exact_source_classification() -> None:
    rows = pd.DataFrame(
        [
            {
                "root_trace_id": "a",
                "conversation_id": "a",
                "turn_index": 0,
                "input_tokens": 10,
                "output_tokens": 2,
                "concurrency": conc,
                "ttft_ms": 10.0,
                "itl_ms": 2.0,
                "e2e_ms": 15.0,
                "request_start_ns": 1,
            }
            for conc in (1, 2)
        ]
    )
    assert build_paired_turn_comparisons(rows).empty
    rows["match_class"] = "exact_turn_match"
    paired = build_paired_turn_comparisons(rows)
    assert len(paired) == 1
    assert paired.loc[0, "concurrency"] == 2
    assert paired.loc[0, "baseline_concurrency"] == 1


def test_id_status_counts_come_from_all_rows_not_profiled_rows() -> None:
    profiled = pd.DataFrame(
        [
            {
                "concurrency": 1,
                "root_trace_id": "a",
                "session_num": 0,
                "conversation_id": "a",
                "branch_type": "root",
                "input_tokens": 10,
                "output_tokens": 2,
                "ttft_ms": 10.0,
                "itl_ms": 2.0,
                "e2e_ms": 15.0,
                "request_start_ns": 0,
                "request_end_ns": 15_000_000,
                "error_present": False,
                "was_cancelled": False,
            }
        ]
    )
    all_rows = pd.concat(
        [
            profiled,
            pd.DataFrame(
                [
                    {
                        **profiled.iloc[0].to_dict(),
                        "error_present": True,
                        "was_cancelled": True,
                        "benchmark_phase": "warmup",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    summary = summarize_id_concurrency(profiled, all_frame=all_rows)
    assert summary.loc[0, "error_count"] == 1
    assert summary.loc[0, "cancellation_count"] == 1


def test_blocked_h200_coverage_never_emits_zero_observation_claims(tmp_path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_analysis.py"
    spec = importlib.util.spec_from_file_location("run_analysis_for_test", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    source = pd.DataFrame([{"root_trace_id": "a"}, {"root_trace_id": "b"}])
    result = module._coverage_stage(
        tmp_path,
        pd.DataFrame(),
        pd.DataFrame(),
        source,
        {"a", "b"},
        [1, 2],
        h200_available=False,
    )
    matrix = pd.read_csv(tmp_path / "id_coverage_matrix.csv")
    status = json.loads((tmp_path / "coverage_status.json").read_text(encoding="utf-8"))
    assert result["status"] == "blocked_no_profile_export"
    assert matrix.empty
    assert status["status"] == "blocked_no_profile_export"
    assert "zero coverage must not be inferred" in status["interpretation"]
