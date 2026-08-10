from __future__ import annotations

import pandas as pd

from h200_agentx_analysis.id03_deep_dive import (
    CONTEXT_202752_UNAVAILABLE,
    ID03_CANONICAL_ID,
    build_reference_table,
    collapse_source_key_profiles,
    context_202752_status,
    cross_concurrency_summary,
    exact_pair_table,
    id03_rows,
    source_coverage_by_concurrency,
)
from h200_agentx_analysis.mtp_study import (
    MIN_COMPARATIVE_ITL_SAMPLES,
    decode_tps_comparison_status,
    summarize_requests,
)


def _raw_row(
    *,
    concurrency: int = 8,
    start_ns: int = 100,
    record_ordinal: int = 0,
    phase: str = "profiling",
    outer: int = 0,
    inner: int = -1,
    path: str = "root",
    root: str = ID03_CANONICAL_ID,
    turn_index: int = 0,
) -> dict[str, object]:
    return {
        "concurrency": concurrency,
        "root_trace_id": root,
        "source_trace_id": root,
        "source_outer_idx": outer,
        "source_inner_idx": inner,
        "source_request_index": outer,
        "source_conversation_path": path,
        "source_branch_type": "root" if path == "root" else "subagent main",
        "source_branch_request_index": outer,
        "conversation_id": f"{root}::{path}",
        "session_num": record_ordinal,
        "turn_index": turn_index,
        "benchmark_phase": phase,
        "request_start_ns": start_ns,
        "request_ack_ns": start_ns + 1,
        "request_end_ns": start_ns + 10,
        "source_file_path": "fixture/profile_export.jsonl",
        "record_ordinal": record_ordinal,
        "worker_id": "worker-0",
        "input_sequence_length": 100 + outer,
        "usage_prompt_tokens": 100 + outer,
        "source_input_tokens": 1_000 + outer,
        "logical_prompt_tokens": pd.NA,
        "cache_read_tokens": pd.NA,
        "output_tokens": 4,
        "ttft_ms": 10.0 + outer,
        "itl_ms": 2.0,
        "e2e_ms": 20.0 + outer,
        "exact_source_key": f"{root}|{outer}|{inner}",
        "error_present": False,
        "was_cancelled": False,
    }


def _collapsed_row(
    *,
    concurrency: int,
    key: str,
    path: str = "root",
    turn_index: int = 0,
    output_tokens: int = 4,
    ttft_ms: float = 10.0,
    itl_ms: float = 2.0,
    e2e_ms: float = 20.0,
) -> dict[str, object]:
    outer = int(key.split("|")[-2])
    inner = int(key.split("|")[-1])
    return {
        "concurrency": concurrency,
        "exact_source_key": key,
        "record_count": 1,
        "root_trace_id": ID03_CANONICAL_ID,
        "source_trace_id": ID03_CANONICAL_ID,
        "source_conversation_path": path,
        "source_branch_type": "root",
        "benchmark_phase": "profiling",
        "source_outer_idx": outer,
        "source_inner_idx": inner,
        "source_request_index": outer,
        "source_branch_request_index": outer,
        "turn_index": turn_index,
        "input_sequence_length": 100,
        "usage_prompt_tokens": 100,
        "source_input_tokens": 1_000,
        "output_tokens": output_tokens,
        "ttft_ms": ttft_ms,
        "itl_ms": itl_ms,
        "decode_tps": 1_000.0 / itl_ms,
        "e2e_ms": e2e_ms,
    }


def test_id03_selection_requires_the_canonical_full_id() -> None:
    canonical = _raw_row()
    prefix_collision = _raw_row(root="07dd405another-root", record_ordinal=1)
    frame = pd.DataFrame([canonical, prefix_collision])

    selected = id03_rows(frame)

    assert selected["root_trace_id"].tolist() == [ID03_CANONICAL_ID]


def test_execution_ordinals_are_chronological_and_profile_filter_aware() -> None:
    # Deliberately write raw records in a non-chronological order.  The public
    # reference must expose raw order separately and sort human-facing replay
    # ordinals by start time.
    frame = pd.DataFrame(
        [
            _raw_row(start_ns=300, record_ordinal=90, outer=2, path="root"),
            _raw_row(start_ns=100, record_ordinal=10, phase="warmup", outer=0, path="root"),
            _raw_row(start_ns=200, record_ordinal=20, outer=1, path="sa:one"),
        ]
    )

    reference = build_reference_table(frame)

    assert reference["request_start_ns"].tolist() == [100, 200, 300]
    assert reference["raw_record_ordinal"].tolist() == [10, 20, 90]
    assert reference["execution_ordinal_all_0_based"].tolist() == [0, 1, 2]
    assert reference["execution_ordinal_all_1_based"].tolist() == [1, 2, 3]
    assert pd.isna(reference.loc[0, "execution_ordinal_profile_0_based"])
    assert reference.loc[1, "execution_ordinal_profile_0_based"] == 0
    assert reference.loc[2, "execution_ordinal_profile_0_based"] == 1
    assert reference["execution_ordinal_within_root_0_based"].tolist() == [0, 1, 2]
    assert reference["execution_ordinal_within_branch_0_based"].tolist() == [0, 0, 1]


def test_source_coverage_reports_warmup_profile_and_chronological_bounds() -> None:
    reference = build_reference_table(
        pd.DataFrame(
            [
                _raw_row(start_ns=200, record_ordinal=2, phase="profiling", outer=2),
                _raw_row(start_ns=100, record_ordinal=1, phase="warmup", outer=0),
                _raw_row(start_ns=150, record_ordinal=3, phase="profiling", outer=1, path="sa:one"),
            ]
        )
    )

    coverage = source_coverage_by_concurrency(reference, source_request_count=4).set_index(
        "concurrency"
    )

    row = coverage.loc[8]
    assert row["all_request_count"] == 3
    assert row["warmup_count"] == 1
    assert row["successful_profiling_count"] == 2
    assert row["first_source_outer_idx"] == 0
    assert row["last_source_outer_idx"] == 2
    assert row["first_exact_source_key"].endswith("|0|-1")
    assert row["last_exact_source_key"].endswith("|2|-1")
    assert row["source_coverage_ratio_profile"] == 0.5
    assert row["wall_span_s"] == 110 / 1e9
    assert coverage.loc[12, "all_request_count"] == 0


def test_exact_matching_records_validation_conflicts_and_excludes_them_from_strict_subsets() -> None:
    key = f"{ID03_CANONICAL_ID}|7|-1"
    collapsed = pd.DataFrame(
        [
            _collapsed_row(concurrency=8, key=key, path="root", turn_index=7),
            _collapsed_row(concurrency=12, key=key, path="sa:unexpected", turn_index=8),
        ]
    )

    paired = exact_pair_table(collapsed, 8, 12)

    assert len(paired) == 1
    assert paired.loc[0, "source_path_validation"] == "conflict"
    assert paired.loc[0, "turn_index_validation"] == "conflict"
    # A source-key collision cannot be called a high-confidence exact request
    # pair when its independent path/turn validation contradicts the key.
    assert not bool(paired.loc[0, "strict_ttft_subset"])
    assert not bool(paired.loc[0, "strict_decode_subset"])


def test_exact_pairs_collapse_replayed_source_keys_to_per_concurrency_medians() -> None:
    first_c8 = _raw_row(concurrency=8, record_ordinal=1, outer=4, start_ns=100)
    second_c8 = _raw_row(concurrency=8, record_ordinal=2, outer=4, start_ns=200)
    c12 = _raw_row(concurrency=12, record_ordinal=3, outer=4, start_ns=300)
    first_c8["ttft_ms"] = 10.0
    second_c8["ttft_ms"] = 30.0
    c12["ttft_ms"] = 40.0
    reference = build_reference_table(pd.DataFrame([first_c8, second_c8, c12]))

    collapsed = collapse_source_key_profiles(reference)
    paired = exact_pair_table(collapsed, 8, 12)

    assert collapsed.loc[collapsed["concurrency"] == 8, "record_count"].iloc[0] == 2
    assert paired.loc[0, "left_ttft_ms"] == 20.0
    assert paired.loc[0, "ttft_ratio_right_over_left"] == 2.0


def test_cross_concurrency_summary_uses_key_jaccard_not_row_counts() -> None:
    key_a = f"{ID03_CANONICAL_ID}|1|-1"
    key_b = f"{ID03_CANONICAL_ID}|2|-1"
    key_c = f"{ID03_CANONICAL_ID}|3|-1"
    collapsed = pd.DataFrame(
        [
            _collapsed_row(concurrency=8, key=key_a, ttft_ms=10, itl_ms=2, e2e_ms=20),
            _collapsed_row(concurrency=8, key=key_b),
            _collapsed_row(concurrency=12, key=key_a, ttft_ms=20, itl_ms=4, e2e_ms=40),
            _collapsed_row(concurrency=12, key=key_c),
        ]
    )
    paired = exact_pair_table(collapsed, 8, 12)

    summary = cross_concurrency_summary(collapsed, {"c8_c12": paired}).iloc[0]

    assert summary["matched_source_key_count"] == 1
    assert summary["strict_ttft_count"] == 1
    assert summary["strict_decode_count"] == 1
    assert summary["coverage_overlap_ratio_jaccard"] == 1 / 3
    assert summary["median_ttft_ratio_right_over_left"] == 2.0
    assert summary["median_itl_ratio_right_over_left"] == 2.0


def test_context_202752_subset_stays_unavailable_without_target_tokenization() -> None:
    reference = build_reference_table(pd.DataFrame([_raw_row()]))

    compatible, status = context_202752_status(reference)

    assert compatible.empty
    row = status.iloc[0]
    assert row["context_202752_subset_status"] == CONTEXT_202752_UNAVAILABLE
    assert "input_sequence_length" in row["forbidden_proxies"]
    assert "source_input_tokens" in row["forbidden_proxies"]


def test_raw_profile_cache_counter_is_not_published_as_cache_load_tps() -> None:
    summary = summarize_requests(
        pd.DataFrame(
            {
                "cache_read_tokens": [100],
                "output_tokens": [4],
                "itl_ms": [2.0],
                "ttft_ms": [10.0],
                "e2e_ms": [20.0],
                "request_start_ns": [0],
                "request_end_ns": [1_000_000_000],
            }
        )
    )

    assert "cache_load_tps" not in summary
    assert summary["raw_profile_cache_counter_tps"] == 100.0
    assert summary["raw_profile_cache_counter_status"] == "profile_counter_scope_unvalidated"


def test_decode_tps_comparison_status_suppresses_sparse_itl_samples() -> None:
    for sample_count in (None, 0, 1, MIN_COMPARATIVE_ITL_SAMPLES - 1):
        assert decode_tps_comparison_status(sample_count).startswith("suppressed_n_lt_")
    assert decode_tps_comparison_status(MIN_COMPARATIVE_ITL_SAMPLES) == (
        "comparative_sample_size_available"
    )
