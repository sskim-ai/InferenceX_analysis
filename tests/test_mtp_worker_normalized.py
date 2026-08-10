"""Tests for the intentionally limited worker-normalized public comparison."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


def _analyzer_module():
    path = Path(__file__).resolve().parents[1] / "scripts/h200_gpu_resident_mtp/analyze.py"
    spec = importlib.util.spec_from_file_location("mtp_analyze_for_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _row(*, concurrency: int, ttft_ms: float, itl_ms: float, e2e_ms: float) -> dict:
    return {
        "concurrency": concurrency,
        "root_trace_id": "trace-a",
        "source_outer_idx": 1,
        "source_inner_idx": None,
        "output_tokens": 5,
        "input_sequence_length": 10,
        "ttft_ms": ttft_ms,
        "itl_ms": itl_ms,
        "e2e_ms": e2e_ms,
        "request_start_ns": 0,
        "request_end_ns": 1_000_000_000,
    }


def test_worker_normalized_table_separates_run_and_exact_sample_counts() -> None:
    analyzer = _analyzer_module()
    hisparse = pd.DataFrame(
        [
            _row(concurrency=4, ttft_ms=100, itl_ms=20, e2e_ms=200),
            _row(concurrency=8, ttft_ms=200, itl_ms=30, e2e_ms=300),
        ]
    )
    gpu_resident = pd.DataFrame(
        [
            _row(concurrency=8, ttft_ms=50, itl_ms=10, e2e_ms=100),
            _row(concurrency=16, ttft_ms=100, itl_ms=15, e2e_ms=150),
        ]
    )

    result = analyzer._worker_normalized_comparisons(gpu_resident, hisparse)

    assert set(result["comparison_label"]) == {
        "approximate_worker_normalized_hisparse_c4_vs_gpu_resident_mtp_c8",
        "approximate_worker_normalized_hisparse_c8_vs_gpu_resident_mtp_c16",
    }
    paired = result.loc[
        (result["comparison_scope"] == "source_key_matched_median_observed_system_ratio")
        & (result["metric"] == "ttft_ratio_gpu_resident_over_hisparse")
    ].sort_values("hisparse_concurrency")
    assert paired["exact_matched_source_key_count"].tolist() == [1, 1]
    assert paired["strict_ttft_count"].tolist() == [1, 1]
    assert paired["strict_decode_count"].tolist() == [1, 1]
    assert paired["gpu_resident_over_hisparse_ratio"].tolist() == [0.5, 0.5]

    run_level = result.loc[
        (result["comparison_scope"] == "run_level_unpaired_observed_system_difference")
        & (result["metric"] == "weighted_decode_tps")
    ]
    assert run_level["exact_matched_source_key_count"].isna().all()
    assert run_level["hisparse_request_count"].tolist() == [1, 1]
    assert run_level["gpu_resident_request_count"].tolist() == [1, 1]
    assert result["caveat"].str.contains("worker_id is request metadata").all()
    assert (result["hisparse_decode_worker_count"] == 1).all()
    assert (result["gpu_resident_mtp_decode_worker_count"] == 2).all()
