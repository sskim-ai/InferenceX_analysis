from __future__ import annotations

import json

import pandas as pd

from h200_agentx_analysis.reporting import generate_reports


def _write_csv(tmp_path, name: str, rows: list[dict]) -> None:
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(processed / f"{name}.csv", index=False)


def test_completed_h200_report_keeps_metadata_and_pairing_scopes_distinct(tmp_path) -> None:
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    (processed / "h200_build_status.json").write_text(
        json.dumps({"status": "completed", "h200_available": True}), encoding="utf-8"
    )
    (processed / "coverage_status.json").write_text(
        json.dumps({"status": "completed"}), encoding="utf-8"
    )
    _write_csv(
        tmp_path,
        "source_trace_summary",
        [{"root_trace_id": "root-a"}, {"root_trace_id": "root-b"}],
    )
    _write_csv(
        tmp_path,
        "h200_requests_profiled",
        [
            {
                "root_trace_id": "root-a",
                "root_trace_id_provenance": "metadata.source_trace_id",
                "source_id_matched": True,
                "loader_metadata_turn_match": True,
                "match_class": "exact_turn_match",
            },
            {
                "root_trace_id": "root-a",
                "root_trace_id_provenance": "metadata.source_trace_id",
                "source_id_matched": True,
                "loader_metadata_turn_match": True,
                "match_class": "loader_metadata_turn_match",
            },
        ],
    )
    _write_csv(
        tmp_path,
        "concurrency_coverage_summary",
        [
            {
                "concurrency": 1,
                "profiled_request_count": 2,
                "distinct_root_ids": 1,
                "matched_root_ids": 1,
                "root_match_rate": 1.0,
                "replay_root_request_count": 1,
                "replay_nonroot_branch_request_count": 1,
                "source_origin_root_request_count": 2,
                "source_origin_subagent_request_count": 0,
            }
        ],
    )
    _write_csv(
        tmp_path,
        "id_concurrency_ratios",
        [
            {
                "root_trace_id": "root-a",
                "concurrency": 1,
                "baseline_concurrency": 1,
                "coverage_comparable": True,
            },
            {
                "root_trace_id": "root-a",
                "concurrency": 2,
                "baseline_concurrency": 1,
                "coverage_comparable": True,
                "ttft_ratio": 1.2,
            },
            {
                "root_trace_id": "root-b",
                "concurrency": 2,
                "baseline_concurrency": 1,
                "coverage_comparable": False,
                "ttft_ratio": 9.0,
            },
        ],
    )
    _write_csv(
        tmp_path,
        "paired_turn_comparisons",
        [
            {
                "root_trace_id": "root-a",
                "concurrency": 2,
                "baseline_concurrency": 1,
                "baseline_available_at_conc1": True,
                "matched_sample_count": 1,
                "baseline_matched_sample_count": 1,
                "output_tokens": 12,
                "baseline_output_tokens": 12,
                "output_token_delta": 0,
                "ttft_ratio": 1.1,
            }
        ],
    )
    _write_csv(
        tmp_path,
        "aggregate_validation",
        [
            {
                "concurrency": 1,
                "metric": "mean_ttft_ms",
                "published": 10.0,
                "recomputed": 10.0,
                "absolute_delta": 0.0,
                "relative_delta": 0.0,
                "status": "pass",
                "validation_status": "pass",
            }
        ],
    )
    _write_csv(
        tmp_path,
        "replay_branch_type_summary",
        [{"concurrency": 1, "branch_type": "fanout", "profiled_request_count": 1}],
    )
    _write_csv(
        tmp_path,
        "source_origin_branch_summary",
        [{"concurrency": 1, "source_branch_type": "root", "profiled_request_count": 2}],
    )
    _write_csv(
        tmp_path,
        "session_num_grouping_diagnostics",
        [
            {
                "concurrency": 1,
                "profiled_request_count": 2,
                "distinct_session_num": 2,
                "session_num_unique_row_rate": 1.0,
                "root_trace_id_cluster_count": 1,
            }
        ],
    )

    generate_reports(tmp_path)

    mapping = (tmp_path / "reports" / "03_id_mapping.md").read_text(encoding="utf-8")
    cross_concurrency = (tmp_path / "reports" / "06_cross_concurrency.md").read_text(
        encoding="utf-8"
    )
    id_level = (tmp_path / "reports" / "05_id_level_results.md").read_text(encoding="utf-8")
    korean = (tmp_path / "reports" / "results_summary_ko.md").read_text(encoding="utf-8")
    validation = (tmp_path / "reports" / "07_validation.md").read_text(encoding="utf-8")

    assert "metadata.source_trace_id" in mapping
    assert "loader metadata association" in mapping
    assert "strict exact-turn" in mapping
    assert "coverage-confounded row는 `1`개" in cross_concurrency
    assert "source output length로 대체하지 않는다" in cross_concurrency
    assert "Source-origin branch summary" in id_level
    assert "semantic identity is not validated" in id_level
    assert "source-origin과 replay structure" in korean
    assert "coverage-confounded `1`개" in korean
    assert "`pass` 또는 `pass_alias_equivalent` row는 `1/1`개" in validation
