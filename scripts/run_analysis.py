#!/usr/bin/env python3
"""Run coverage, ID, concurrency, and aggregate-validation stages."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from h200_agentx_analysis.artifact_parser import load_artifact_inventory  # noqa: E402
from h200_agentx_analysis.config import configured_path, load_run_config  # noqa: E402
from h200_agentx_analysis.coverage import (  # noqa: E402
    build_coverage_bias_table,
    build_coverage_model_composition,
    build_coverage_summary,
    build_id_coverage_matrix,
    observation_probability_by_source_shape,
)
from h200_agentx_analysis.h200_io import read_processed_table, write_json  # noqa: E402
from h200_agentx_analysis.paired_analysis import (  # noqa: E402
    build_exact_turn_cache_shape_table,
    build_id_concurrency_ratios,
    build_paired_turn_comparisons,
    clustered_ratio_summary,
    summarize_cache_shape_relationship,
)
from h200_agentx_analysis.per_id_analysis import (  # noqa: E402
    summarize_branch_types,
    summarize_id_concurrency,
    summarize_replay_instances,
    summarize_session_num_grouping,
    summarize_source_branch_origins,
    summarize_weightings,
    top_ids_by_latency,
    top_ids_by_workload,
)
from h200_agentx_analysis.validation import (  # noqa: E402
    aggregate_artifact_context,
    find_aggregate_jsons,
    load_published_aggregates,
    recompute_raw_aggregates,
    validate_aggregates,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run H200 conversation-ID analysis stages.")
    parser.add_argument(
        "--config", type=Path, default=REPOSITORY_ROOT / "configs/run_29820102138.yaml"
    )
    parser.add_argument("--processed-dir", type=Path, help="override analysis.processed_dir")
    parser.add_argument("--raw-root", type=Path, help="override analysis.raw_github_dir")
    parser.add_argument(
        "--stage",
        choices=("coverage", "ids", "concurrency", "validate", "all"),
        required=True,
    )
    parser.add_argument("--bootstrap-replicates", type=int, default=1_000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.bootstrap_replicates < 1:
        print("--bootstrap-replicates must be positive", file=sys.stderr)
        return 2
    try:
        config = load_run_config(args.config)
        processed = args.processed_dir or configured_path(config, "processed_dir")
        raw_root = args.raw_root or configured_path(config, "raw_github_dir")
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"analysis blocked: {exc}", file=sys.stderr)
        return 2
    processed.mkdir(parents=True, exist_ok=True)
    concurrencies = list(config.get("expected_environment", {}).get("concurrency", range(1, 9)))
    h200_all = read_processed_table(processed / "h200_requests_all.parquet")
    h200_profiled = read_processed_table(processed / "h200_requests_profiled.parquet")
    h200_build_status = _load_json(processed / "h200_build_status.json")
    h200_available = bool(h200_build_status.get("h200_available", not h200_profiled.empty))
    source_summary = read_processed_table(processed / "source_trace_summary.parquet")
    source_ids = _source_ids(source_summary)
    stages = [args.stage] if args.stage != "all" else ["coverage", "ids", "concurrency", "validate"]
    completed: dict[str, dict] = {}
    for stage in stages:
        if stage == "coverage":
            completed[stage] = _coverage_stage(
                processed,
                h200_all,
                h200_profiled,
                source_summary,
                source_ids,
                concurrencies,
                h200_available=h200_available,
            )
        elif stage == "ids":
            completed[stage] = _id_stage(processed, h200_all, h200_profiled, source_summary)
        elif stage == "concurrency":
            completed[stage] = _concurrency_stage(
                processed, h200_profiled, source_summary, args.bootstrap_replicates
            )
        elif stage == "validate":
            completed[stage] = _validation_stage(processed, raw_root, h200_profiled)
    status = {
        "status": (
            "blocked_no_profile_export"
            if not h200_available
            else ("completed_with_zero_profiled_rows" if h200_profiled.empty else "completed")
        ),
        "h200_available": h200_available,
        "h200_profiled_rows": int(len(h200_profiled)),
        "source_trace_count": len(source_ids),
        "session_num_replay_semantics": (
            "Unknown: profile_export metadata does not establish session_num as an "
            "independent replay-instance identifier; root_trace_id is the "
            "cross-concurrency bootstrap cluster unit."
        ),
        "stages": completed,
    }
    write_json(processed / "analysis_status.json", status)
    print(json.dumps(status, ensure_ascii=False, sort_keys=True))
    return 0


def _coverage_stage(
    processed: Path,
    h200_all: pd.DataFrame,
    h200_profiled: pd.DataFrame,
    source_summary: pd.DataFrame,
    source_ids: set[str],
    concurrencies: list[int],
    *,
    h200_available: bool,
) -> dict:
    if not h200_available:
        _write_blocked_coverage_outputs(processed, concurrencies)
        return {
            "status": "blocked_no_profile_export",
            "id_coverage_matrix_rows": 0,
            "coverage_summary_rows": 0,
            "source_trace_count": len(source_ids),
            "source_model_composition_rows": 0,
        }
    matrix = build_id_coverage_matrix(
        h200_profiled, source_ids=source_ids, concurrencies=concurrencies
    )
    summary = build_coverage_summary(
        h200_all,
        h200_profiled,
        source_ids=source_ids,
        concurrencies=concurrencies,
    )
    # Compatibility aliases make report readers explicit while retaining the
    # more descriptive full column names.
    if "distinct_conversation_branches" in summary and "distinct_branches" not in summary:
        summary["distinct_branches"] = summary["distinct_conversation_branches"]
    bias = build_coverage_bias_table(source_summary, h200_profiled, concurrencies=concurrencies)
    model_composition = build_coverage_model_composition(
        source_summary, h200_profiled, concurrencies=concurrencies
    )
    observation = observation_probability_by_source_shape(
        source_summary, h200_profiled, concurrencies=concurrencies
    )
    matrix.to_csv(processed / "id_coverage_matrix.csv", index=False)
    summary.to_csv(processed / "concurrency_coverage_summary.csv", index=False)
    bias.to_csv(processed / "coverage_bias_summary.csv", index=False)
    model_composition.to_csv(processed / "coverage_bias_model_composition.csv", index=False)
    observation.to_parquet(processed / "source_observation_probability.parquet", index=False)
    write_json(
        processed / "coverage_status.json",
        {
            "status": "completed",
            "h200_profiled_rows": int(len(h200_profiled)),
            "source_trace_count": len(source_ids),
            "interpretation": "Coverage counts are based on acquired H200 profiling records.",
        },
    )
    return {
        "id_coverage_matrix_rows": int(len(matrix)),
        "coverage_summary_rows": int(len(summary)),
        "source_trace_count": len(source_ids),
        "source_model_composition_rows": int(len(model_composition)),
    }


def _id_stage(
    processed: Path,
    h200_all: pd.DataFrame,
    h200_profiled: pd.DataFrame,
    source_summary: pd.DataFrame,
) -> dict:
    replay = summarize_replay_instances(h200_profiled)
    summary = summarize_id_concurrency(
        h200_profiled, source_summary=source_summary, all_frame=h200_all
    )
    branch = summarize_branch_types(h200_profiled, all_frame=h200_all)
    source_origin = summarize_source_branch_origins(h200_profiled, all_frame=h200_all)
    session_diagnostics = summarize_session_num_grouping(h200_profiled)
    weighting = summarize_weightings(h200_profiled)
    workload = top_ids_by_workload(summary)
    latency = top_ids_by_latency(summary)
    replay.to_parquet(processed / "replay_instance_summary.parquet", index=False)
    summary.to_parquet(processed / "id_concurrency_summary.parquet", index=False)
    _human_id_summary(summary).to_csv(processed / "id_concurrency_summary.csv", index=False)
    branch.to_csv(processed / "root_subagent_summary.csv", index=False)
    # ``root_subagent_summary`` predates authoritative source-origin joins and
    # therefore contains H200 replay suffix categories. Keep it for backwards
    # compatibility and emit explicit names for both taxonomies.
    branch.to_csv(processed / "replay_branch_type_summary.csv", index=False)
    source_origin.to_csv(processed / "source_origin_branch_summary.csv", index=False)
    source_origin.to_csv(processed / "source_branch_origin_summary.csv", index=False)
    session_diagnostics.to_csv(processed / "session_num_grouping_diagnostics.csv", index=False)
    weighting.to_csv(processed / "weighting_summary.csv", index=False)
    workload.to_csv(processed / "top_ids_by_workload.csv", index=False)
    latency.to_csv(processed / "top_ids_by_latency.csv", index=False)
    return {
        "replay_instance_rows": int(len(replay)),
        "id_concurrency_rows": int(len(summary)),
        "branch_summary_rows": int(len(branch)),
        "source_origin_branch_summary_rows": int(len(source_origin)),
        "session_num_grouping_rows": int(len(session_diagnostics)),
        "cross_concurrency_cluster_unit": "root_trace_id",
        "session_num_replay_semantics": "unvalidated_session_num_group",
    }


def _concurrency_stage(
    processed: Path,
    h200_profiled: pd.DataFrame,
    source_summary: pd.DataFrame,
    bootstrap_replicates: int,
) -> dict:
    summary = read_processed_table(processed / "id_concurrency_summary.parquet")
    if summary.empty and not h200_profiled.empty:
        summary = summarize_id_concurrency(h200_profiled, source_summary=source_summary)
    ratios = build_id_concurrency_ratios(summary)
    paired = build_paired_turn_comparisons(h200_profiled, require_exact_source_match=True)
    paired_summary = clustered_ratio_summary(paired, n_bootstrap=bootstrap_replicates)
    exact_cache = build_exact_turn_cache_shape_table(h200_profiled)
    cache_summary = summarize_cache_shape_relationship(exact_cache)
    ratios.to_csv(processed / "id_concurrency_ratios.csv", index=False)
    paired.to_parquet(processed / "paired_turn_comparisons.parquet", index=False)
    paired_summary.to_csv(processed / "paired_ratio_cluster_bootstrap.csv", index=False)
    exact_cache.to_parquet(processed / "exact_turn_cache_shape.parquet", index=False)
    cache_summary.to_csv(processed / "cache_shape_relationship_summary.csv", index=False)
    return {
        "id_concurrency_ratio_rows": int(len(ratios)),
        "paired_turn_rows": int(len(paired)),
        "clustered_summary_rows": int(len(paired_summary)),
        "exact_turn_cache_shape_rows": int(len(exact_cache)),
        "cache_shape_summary_rows": int(len(cache_summary)),
    }


def _validation_stage(processed: Path, raw_root: Path, h200_profiled: pd.DataFrame) -> dict:
    raw = recompute_raw_aggregates(h200_profiled)
    inventory = load_artifact_inventory(REPOSITORY_ROOT / "manifests/github_artifacts.json")
    aggregate_paths = find_aggregate_jsons(raw_root, artifacts=inventory)
    published = load_published_aggregates(
        aggregate_paths, artifact_context=aggregate_artifact_context(aggregate_paths, inventory)
    )
    validation = validate_aggregates(raw, published)
    # Report-compatible aliases retain the unambiguous canonical fields too.
    validation["published"] = validation.get("published_value")
    validation["recomputed"] = validation.get("raw_value")
    validation["absolute_delta"] = validation.get("absolute_difference")
    validation["relative_delta"] = validation.get("relative_difference")
    validation["status"] = validation.get("validation_status")
    raw.to_csv(processed / "raw_aggregate_recomputed.csv", index=False)
    published.to_csv(processed / "published_aggregate_extracted.csv", index=False)
    validation.to_csv(processed / "aggregate_validation.csv", index=False)
    return {
        "raw_aggregate_rows": int(len(raw)),
        "published_aggregate_files": len(aggregate_paths),
        "validation_rows": int(len(validation)),
        "validation_pass_count": int(
            validation.get("validation_status", pd.Series(dtype="object"))
            .isin(["pass", "pass_alias_equivalent"])
            .sum()
        )
        if not validation.empty
        else 0,
    }


def _source_ids(source_summary: pd.DataFrame) -> set[str]:
    if "root_trace_id" not in source_summary:
        return set()
    return {str(value) for value in source_summary["root_trace_id"].dropna() if str(value).strip()}


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_blocked_coverage_outputs(processed: Path, concurrencies: list[int]) -> None:
    matrix_columns = ["root_trace_id", *[f"conc{value}" for value in concurrencies]]
    summary_columns = [
        "concurrency",
        "all_request_count",
        "profiled_request_count",
        "distinct_root_ids",
        "matched_root_ids",
        "root_match_rate",
        "coverage_status",
    ]
    pd.DataFrame(columns=matrix_columns).to_csv(processed / "id_coverage_matrix.csv", index=False)
    pd.DataFrame(columns=summary_columns).to_csv(
        processed / "concurrency_coverage_summary.csv", index=False
    )
    pd.DataFrame().to_csv(processed / "coverage_bias_summary.csv", index=False)
    pd.DataFrame().to_csv(processed / "coverage_bias_model_composition.csv", index=False)
    pd.DataFrame().to_parquet(processed / "source_observation_probability.parquet", index=False)
    write_json(
        processed / "coverage_status.json",
        {
            "status": "blocked_no_profile_export",
            "interpretation": "No H200 raw profile export was acquired; zero coverage must not be inferred.",
        },
    )


def _human_id_summary(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "root_trace_id",
        "concurrency",
        "source_models",
        "distinct_replay_instances",
        "session_num_group_count",
        "session_num_unique_row_rate",
        "replay_instance_identity_status",
        "profiled_request_count",
        # Legacy names below are H200 replay suffix counts, not source-origin
        # nested-agent counts. Explicit columns make that distinction visible.
        "root_request_count",
        "subagent_request_count",
        "replay_root_request_count",
        "replay_nonroot_branch_request_count",
        "source_origin_root_request_count",
        "source_origin_subagent_request_count",
        "total_input_tokens",
        "total_output_tokens",
        "median_ttft_ms",
        "p90_ttft_ms",
        "median_itl_ms",
        "p90_itl_ms",
        "median_e2e_ms",
        "p90_e2e_ms",
        "wall_clock_output_rate",
        "sample_quality_flag",
    ]
    return frame[[column for column in columns if column in frame]]


if __name__ == "__main__":
    raise SystemExit(main())
