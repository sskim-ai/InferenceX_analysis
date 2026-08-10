#!/usr/bin/env python3
"""Build reviewable GPU-resident MTP study outputs from public raw artifacts.

Raw JSONL is read one line at a time into bounded Parquet batches.  The
versioned CSVs below are deliberately compact summaries/subsets; full request
tables remain local and are ignored by Git.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from h200_agentx_analysis.artifact_parser import (  # noqa: E402
    find_profile_exports,
    infer_profile_context,
    iter_jsonl_records,
    load_artifact_inventory,
    parse_concurrency,
    profile_schema_inventory,
)
from h200_agentx_analysis.metrics import percentile  # noqa: E402
from h200_agentx_analysis.mtp_study import (  # noqa: E402
    EXTRA_FIELDS,
    add_requested_id_coverage,
    add_source_metadata_join,
    build_pair_table,
    extract_mtp_profile_record,
    profile_filter,
    requested_id_resolution,
    summarize_requests,
)
from h200_agentx_analysis.validation import (  # noqa: E402
    aggregate_artifact_context,
    find_aggregate_jsons,
    load_published_aggregates,
    recompute_raw_aggregates,
    validate_aggregates,
)

STUDY_ROOT_DEFAULT = REPOSITORY_ROOT / "studies/h200_gpu_resident_mtp"
RAW_ROOT_DEFAULT = REPOSITORY_ROOT / "data/raw/h200_gpu_resident_mtp"

STRING_COLUMNS = {
    "github_run_id",
    "artifact_id",
    "artifact_name",
    "target_model",
    "target_precision",
    "target_hardware",
    "framework",
    "conversation_id",
    "source_trace_id",
    "root_trace_id",
    "root_trace_id_provenance",
    "branch_suffix",
    "branch_type",
    "normalization_rule",
    "benchmark_phase",
    "worker_id",
    "correlation_id",
    "error_category",
    "source_metric_name",
    "itl_interpretation",
    "source_file_path",
    "raw_ttft_field",
    "raw_e2e_field",
    "raw_itl_field",
    "raw_status",
    "status",
    "match_class",
    "exact_source_key",
    "source_conversation_path",
    "source_branch_type",
    "source_model",
    *{f"raw_{field}_field" for field in EXTRA_FIELDS},
    "raw_input_sequence_length_field",
    "raw_output_sequence_length_field",
}
INT_COLUMNS = {
    "concurrency",
    "target_gpu_count",
    "source_outer_idx",
    "source_inner_idx",
    "session_num",
    "turn_index",
    "request_start_ns",
    "request_ack_ns",
    "request_end_ns",
    "cancellation_time_ns",
    "record_ordinal",
}
BOOL_COLUMNS = {
    "source_id_matched",
    "was_cancelled",
    "error_present",
}
ROW_COLUMNS = [
    "github_run_id",
    "artifact_id",
    "artifact_name",
    "concurrency",
    "target_model",
    "target_precision",
    "target_hardware",
    "target_gpu_count",
    "framework",
    "conversation_id",
    "source_trace_id",
    "source_outer_idx",
    "source_inner_idx",
    "root_trace_id",
    "root_trace_id_provenance",
    "branch_suffix",
    "branch_type",
    "normalization_rule",
    "source_id_matched",
    "session_num",
    "turn_index",
    "request_start_ns",
    "request_ack_ns",
    "request_end_ns",
    "benchmark_phase",
    "worker_id",
    "correlation_id",
    "was_cancelled",
    "cancellation_time_ns",
    "error_present",
    "error_category",
    "input_tokens",
    "output_tokens",
    "input_sequence_length",
    "output_sequence_length",
    "ttft_ms",
    "e2e_ms",
    "itl_ms",
    "theoretical_prefix_cache_hit",
    "source_metric_name",
    "itl_interpretation",
    "record_ordinal",
    "source_file_path",
    "raw_ttft_field",
    "raw_e2e_field",
    "raw_itl_field",
    "raw_status",
    "status",
    "decode_duration_ms",
    "full_decode_duration_ms",
    "logical_prompt_tokens",
    "usage_prompt_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "new_prompt_tokens",
    "kv_write_eligible_tokens",
    "mtp_draft_tokens",
    "mtp_accepted_tokens",
    "mtp_acceptance_length",
    "mtp_acceptance_rate",
    "mtp_observed_acceptance_rate",
    "match_class",
    "exact_source_key",
    "source_conversation_path",
    "source_branch_type",
    "source_branch_request_index",
    "source_request_index",
    "source_input_tokens",
    "source_output_tokens",
    "source_t_s",
    "source_model",
    "hash_block_count",
    "lcp_block_count",
    "theoretical_cached_tokens",
    "theoretical_new_tokens",
    "theoretical_cache_ratio",
    "rollback_blocks",
    "branch_fork_indicator",
    "loader_metadata_turn_match",
    "loader_metadata_input_tokens_match",
    "loader_metadata_output_tokens_match",
    "raw_input_sequence_length_field",
    "raw_output_sequence_length_field",
    *[f"raw_{field}_field" for field in EXTRA_FIELDS],
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, default=RAW_ROOT_DEFAULT)
    parser.add_argument("--study-root", type=Path, default=STUDY_ROOT_DEFAULT)
    parser.add_argument(
        "--source-summary", type=Path, default=REPOSITORY_ROOT / "data/processed/source_trace_summary.parquet"
    )
    parser.add_argument(
        "--source-requests", type=Path, default=REPOSITORY_ROOT / "data/processed/source_requests.parquet"
    )
    parser.add_argument(
        "--hisparse-profiled",
        type=Path,
        default=REPOSITORY_ROOT / "data/processed/h200_requests_profiled.parquet",
    )
    parser.add_argument("--batch-size", type=int, default=5_000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be positive")
    processed = args.study_root / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    inventory_path = args.raw_root / "run_artifacts.json"
    artifacts = load_artifact_inventory(inventory_path)
    profiles = find_profile_exports(args.raw_root)
    if not profiles:
        _write_status(
            processed,
            {
                "status": "blocked_no_profile_export",
                "raw_root": _repository_relative(args.raw_root),
                "profile_export_count": 0,
                "next_command": "python scripts/h200_gpu_resident_mtp/acquire.py",
            },
        )
        print(json.dumps({"status": "blocked_no_profile_export"}, ensure_ascii=False))
        return 2

    field_inventory, metric_inventory, schema_issues = _profile_schema_inventory_tables(
        profiles, artifacts
    )
    field_inventory.to_csv(processed / "profile_field_inventory.csv", index=False)
    metric_inventory.to_csv(processed / "profile_metric_inventory.csv", index=False)

    stream_path = processed / "_streamed_profile_rows.parquet"
    stream_status = _stream_profiles(
        profiles,
        artifacts,
        stream_path,
        batch_size=args.batch_size,
    )
    raw = pd.read_parquet(stream_path)
    source_summary = _read_parquet_or_empty(args.source_summary)
    source_requests = _read_parquet_or_empty(args.source_requests)
    source_ids = set(source_summary.get("root_trace_id", pd.Series(dtype="string")).dropna().astype(str))
    if not source_ids:
        source_ids = set(source_requests.get("root_trace_id", pd.Series(dtype="string")).dropna().astype(str))
    joined = add_source_metadata_join(raw, source_requests, source_ids)
    profiled, exclusions = profile_filter(joined)
    classified = pd.concat([profiled, exclusions], ignore_index=True, sort=False)
    _write_parquet(classified, processed / "h200_requests_all.parquet")
    _write_parquet(profiled, processed / "h200_requests_profiled.parquet")
    exclusions.to_csv(processed / "h200_request_exclusions.csv", index=False)
    _write_processed_tables(
        processed,
        raw_all=classified,
        profiled=profiled,
        source_ids=source_ids,
        hisparse_profiled=_read_parquet_or_empty(args.hisparse_profiled),
        source_summary=source_summary,
        raw_root=args.raw_root,
        artifacts=artifacts,
    )
    status = {
        "status": "completed",
        "raw_root": _repository_relative(args.raw_root),
        "profile_export_count": len(profiles),
        "all_record_count": int(len(classified)),
        "profiled_record_count": int(len(profiled)),
        "excluded_record_count": int(len(exclusions)),
        "schema_inventory_issue_count": len(schema_issues),
        **stream_status,
    }
    _write_status(processed, status)
    print(json.dumps(status, ensure_ascii=False, sort_keys=True))
    return 0


def _profile_schema_inventory_tables(
    profiles: list[Path], artifacts: list[Any]
) -> tuple[pd.DataFrame, pd.DataFrame, list[Any]]:
    """Inventory every raw profile field with the shared streaming helper."""

    field_rows, metric_rows, issues = profile_schema_inventory(profiles)
    context_by_path: dict[str, dict[str, Any]] = {}
    for path in profiles:
        artifact = infer_profile_context(path, artifacts)
        context_by_path[str(path)] = {
            "concurrency": getattr(artifact, "concurrency", None),
            "artifact_id": getattr(artifact, "artifact_id", None),
            "artifact_name": getattr(artifact, "name", None),
        }

    def frame_for(rows: list[dict[str, Any]]) -> pd.DataFrame:
        frame = pd.DataFrame(rows)
        if frame.empty:
            return frame
        for field in ("concurrency", "artifact_id", "artifact_name"):
            frame[field] = frame["source_file_path"].map(
                lambda path, field_name=field: context_by_path.get(str(path), {}).get(field_name)
            )
        frame["source_file_path"] = frame["source_file_path"].map(_repository_relative)
        return frame.sort_values(["concurrency", "field_name"], na_position="last")

    return frame_for(field_rows), frame_for(metric_rows), issues


def _repository_relative(path: Path | str) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPOSITORY_ROOT))
    except ValueError:
        return str(path)


def _stream_profiles(
    profiles: list[Path], artifacts: list[Any], destination: Path, *, batch_size: int
) -> dict[str, Any]:
    """Stream JSONL profile rows into a fixed-schema local Parquet file."""

    import pyarrow as pa
    import pyarrow.parquet as pq

    schema = pa.schema([pa.field(column, _arrow_type(column), nullable=True) for column in ROW_COLUMNS])
    writer = pq.ParquetWriter(destination, schema, compression="zstd")
    malformed = 0
    written = 0
    field_paths: Counter[str] = Counter()
    batch: list[dict[str, Any]] = []
    try:
        for profile in profiles:
            artifact = infer_profile_context(profile, artifacts)
            context = {
                "github_run_id": "31235207041",
                "artifact_id": getattr(artifact, "artifact_id", None),
                "artifact_name": getattr(artifact, "name", None),
                "concurrency": getattr(artifact, "concurrency", None),
                "target_model": "zai-org/GLM-5.2-FP8",
                "target_precision": "FP8",
                "target_hardware": "H200",
                "target_gpu_count": 32,
                "framework": "Dynamo + SGLang",
            }
            issues: list[Any] = []
            for ordinal, record in iter_jsonl_records(profile, issues=issues):
                row = extract_mtp_profile_record(
                    record,
                    context=context,
                    source_file=str(profile),
                    record_ordinal=ordinal,
                )
                for field in ROW_COLUMNS:
                    path = row.get(f"raw_{field}_field")
                    if path:
                        field_paths[f"{field}:{path}"] += 1
                batch.append(_coerce_row(row))
                if len(batch) >= batch_size:
                    writer.write_table(pa.Table.from_pylist(batch, schema=schema))
                    written += len(batch)
                    batch.clear()
            malformed += len(issues)
        if batch:
            writer.write_table(pa.Table.from_pylist(batch, schema=schema))
            written += len(batch)
    finally:
        writer.close()
    return {
        "streamed_record_count": written,
        "malformed_jsonl_line_count": malformed,
        "observed_raw_field_path_count": len(field_paths),
    }


def _write_processed_tables(
    processed: Path,
    *,
    raw_all: pd.DataFrame,
    profiled: pd.DataFrame,
    source_ids: set[str],
    hisparse_profiled: pd.DataFrame,
    source_summary: pd.DataFrame,
    raw_root: Path,
    artifacts: list[Any],
) -> None:
    _schema_mapping(raw_all).to_csv(processed / "schema_mapping.csv", index=False)
    concurrency = _concurrency_summary(raw_all, profiled)
    concurrency.to_csv(processed / "concurrency_summary.csv", index=False)
    _cache_metrics(
        concurrency, _server_cache_metrics(raw_root, artifacts)
    ).to_csv(processed / "cache_metrics.csv", index=False)
    _mtp_metrics(concurrency).to_csv(processed / "mtp_metrics.csv", index=False)
    _coverage_matrix(profiled, source_ids).to_csv(processed / "id_coverage_matrix.csv", index=False)
    _worker_distribution(profiled).to_csv(processed / "worker_distribution.csv", index=False)
    _root_subagent_summary(profiled).to_csv(processed / "root_subagent_summary.csv", index=False)
    _context_cache_relationship(profiled).to_csv(
        processed / "context_cache_relationship.csv", index=False
    )
    resolution = requested_id_resolution(
        profiled,
        source_ids=source_ids,
        hisparse_c8=hisparse_profiled.loc[
            pd.to_numeric(hisparse_profiled.get("concurrency"), errors="coerce") == 8
        ]
        if not hisparse_profiled.empty
        else hisparse_profiled,
    )
    resolution = add_requested_id_coverage(
        resolution,
        raw_all=raw_all,
        profiled=profiled,
    )
    resolution.to_csv(processed / "requested_id_resolution.csv", index=False)
    _write_requested_id_tables(processed, raw_all, profiled, resolution)
    pairs = _cross_concurrency_pairs(profiled)
    _write_parquet(pairs, processed / "cross_concurrency_pairs.parquet")
    _pair_summary(pairs).to_csv(processed / "cross_concurrency_match_summary.csv", index=False)
    system_pairs = _hisparse_c8_pairs(profiled, hisparse_profiled)
    _write_parquet(system_pairs, processed / "c8_exact_matched_requests.parquet")
    _system_comparison(system_pairs, profiled, hisparse_profiled).to_csv(
        processed / "h200_c8_hisparse_vs_gpu_resident.csv", index=False
    )
    _pair_summary(system_pairs, by_root=True).to_csv(processed / "exact_match_c8_summary.csv", index=False)
    _review_pairs(system_pairs).to_csv(processed / "c8_exact_matched_requests_review.csv", index=False)
    _top_ids(profiled).to_csv(processed / "top_ids_by_workload_or_latency.csv", index=False)
    _runtime_configuration().to_csv(processed / "runtime_configuration.csv", index=False)
    _three_system_architecture().to_csv(processed / "three_system_architecture.csv", index=False)
    validation = _aggregate_validation(profiled, raw_root, artifacts)
    validation.to_csv(processed / "aggregate_validation.csv", index=False)
    _validation_summary(validation).to_csv(processed / "validation_summary.csv", index=False)
    # The source summary is loaded above to make its provenance an explicit
    # analysis dependency even though aggregate rows already retain source IDs.
    pd.DataFrame(
        [
            {
                "source_trace_count": len(source_ids),
                "source_summary_rows": int(len(source_summary)),
                "profiled_h200_rows": int(len(profiled)),
                "source_model_interpretation": "workload provenance only; not target model performance",
            }
        ]
    ).to_csv(processed / "source_dependency_summary.csv", index=False)


def _schema_mapping(frame: pd.DataFrame) -> pd.DataFrame:
    fields = [
        (
            "root_trace_id",
            "metadata.source_trace_id preferred; otherwise conversation ID normalization",
            "ID provenance",
            "metadata.source_trace_id/conversation_id normalization",
            None,
        ),
        ("source_trace_id", "metadata.source_trace_id", "loader source ID", "metadata.source_trace_id", None),
        ("conversation_id", "metadata.conversation_id", "replay branch identifier", "metadata.conversation_id", None),
        ("session_num", "metadata.session_num", "opaque replay/session field", "metadata.session_num", None),
        ("turn_index", "metadata.turn_index", "replay turn field", "metadata.turn_index", None),
        ("source_outer_idx", "metadata.source_outer_idx", "source request index", "metadata.source_outer_idx", None),
        ("source_inner_idx", "metadata.source_inner_idx", "nested source request index", "metadata.source_inner_idx", None),
        ("source_conversation_path", "joined source request metadata", "source branch path", "source table join", None),
        ("source_branch_type", "joined source request metadata", "root/subagent origin", "source table join", None),
        ("benchmark_phase", "metadata.benchmark_phase", "profiling/warmup label", "metadata.benchmark_phase", None),
        ("request_start_ns", "metadata.request_start_ns", "replay timestamp", "metadata.request_start_ns", None),
        ("request_ack_ns", "metadata.request_ack_ns", "replay timestamp", "metadata.request_ack_ns", None),
        ("request_end_ns", "metadata.request_end_ns", "replay timestamp", "metadata.request_end_ns", None),
        ("worker_id", "metadata.worker_id", "observed request worker ID", "metadata.worker_id", None),
        ("correlation_id", "metadata.x_correlation_id", "request correlation ID", "metadata.x_correlation_id", None),
        ("was_cancelled", "metadata.was_cancelled", "cancellation status", "metadata.was_cancelled", None),
        ("error_present", "error/status derived flag", "parsed error condition", "derived from error/status", None),
        (
            "input_sequence_length",
            "metrics.input_sequence_length.value",
            "AIPerf metric; not asserted logical prompt",
            None,
            "raw_input_sequence_length_field",
        ),
        (
            "usage_prompt_tokens",
            "metrics.usage_prompt_tokens.value",
            "AIPerf usage field; semantics independently unvalidated",
            None,
            "raw_usage_prompt_tokens_field",
        ),
        ("logical_prompt_tokens", "explicit logical/frontend metric only", "logical prompt only if explicitly exported", None, "raw_logical_prompt_tokens_field"),
        ("cache_read_tokens", "explicit cache-read metric only", "actual cache load only if explicitly exported", None, "raw_cache_read_tokens_field"),
        ("new_prompt_tokens", "logical_prompt_tokens - cache_read_tokens", "derived only when both operands exist", "derived", None),
        (
            "output_sequence_length",
            "metrics.output_sequence_length.value",
            "AIPerf output metric",
            None,
            "raw_output_sequence_length_field",
        ),
        ("ttft_ms", "metrics.time_to_first_token.value", "observed H200 replay latency", None, "raw_ttft_field"),
        ("itl_ms", "metrics.inter_token_latency.value", "request-level ITL/TPOT metric", None, "raw_itl_field"),
        ("e2e_ms", "metrics.request_latency.value", "observed H200 replay latency", None, "raw_e2e_field"),
        ("mtp_accepted_tokens", "explicit MTP metric only", "actual MTP counter only if exported", None, "raw_mtp_accepted_tokens_field"),
        ("mtp_draft_tokens", "explicit MTP metric only", "actual MTP counter only if exported", None, "raw_mtp_draft_tokens_field"),
        ("mtp_acceptance_length", "explicit MTP metric only", "actual MTP counter only if exported", None, "raw_mtp_acceptance_length_field"),
        ("mtp_acceptance_rate", "explicit MTP metric only", "actual MTP counter only if exported", None, "raw_mtp_acceptance_rate_field"),
    ]
    rows = []
    for canonical, requested, interpretation, direct_path, raw_path_column in fields:
        candidates = []
        if raw_path_column and raw_path_column in frame:
            candidates.extend(str(value) for value in frame[raw_path_column].dropna().unique())
        if not candidates and direct_path and canonical in frame and frame[canonical].notna().any():
            candidates = [direct_path]
        status = "observed" if candidates else "not_exported_or_not_mapped"
        rows.append(
            {
                "canonical_field": canonical,
                "requested_mapping": requested,
                "observed_raw_field_paths": ";".join(sorted(set(candidates))) if candidates else None,
                "mapping_status": status,
                "interpretation": interpretation,
            }
        )
    return pd.DataFrame(rows)


def _concurrency_summary(raw_all: pd.DataFrame, profiled: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for concurrency in (8, 12, 16):
        all_group = raw_all.loc[pd.to_numeric(raw_all.get("concurrency"), errors="coerce") == concurrency]
        profile_group = profiled.loc[
            pd.to_numeric(profiled.get("concurrency"), errors="coerce") == concurrency
        ]
        phase = all_group.get("benchmark_phase", pd.Series(dtype="string")).astype("string").str.lower()
        metrics = summarize_requests(profile_group)
        metrics.update(
            {
                "concurrency": concurrency,
                "all_request_count": int(len(all_group)),
                "warmup_count": int(phase.isin(["warmup", "warming", "warm_up"]).sum()),
                "profiling_phase_count": int(phase.isin(["profiling", "profile"]).sum()),
                "error_count_all_rows": int(_truthy_count(all_group.get("error_present"))),
                "cancellation_count_all_rows": int(_truthy_count(all_group.get("was_cancelled"))),
                "profiling_filter": "benchmark_phase=profiling; no error/cancellation; nonnegative tokens; positive TTFT/E2E",
                "weighting_primary_decode_tps": "output-transition-token-weighted ITL",
            }
        )
        rows.append(metrics)
    return pd.DataFrame(rows).sort_values("concurrency")


def _cache_metrics(summary: pd.DataFrame, server_cache: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in summary.iterrows():
        cache_total = _number(row.get("cache_read_tokens_total"))
        usage_total = _number(row.get("usage_prompt_tokens_total"))
        raw_ratio = _ratio(cache_total, usage_total)
        server_row = server_cache.loc[server_cache["concurrency"] == row["concurrency"]]
        server = server_row.iloc[0].to_dict() if not server_row.empty else {}
        if cache_total is None:
            profile_status = "not_available_in_profile_export"
        elif raw_ratio is not None and raw_ratio > 1:
            profile_status = "profile_counter_scope_unvalidated_ratio_gt_1"
        else:
            profile_status = "observed_profile_metric_scope_unvalidated"
        rows.append(
            {
                "concurrency": row["concurrency"],
                "usage_prompt_tokens_total": usage_total,
                "logical_prompt_tokens_total": row.get("logical_prompt_tokens_total"),
                "cache_read_tokens_total": cache_total,
                "cache_read_ratio": row.get("cache_read_ratio"),
                "profile_cache_read_to_usage_prompt_ratio_raw": raw_ratio,
                "new_prompt_tokens_total": row.get("new_prompt_tokens_total"),
                "kv_write_eligible_tokens_total": row.get("kv_write_eligible_tokens_total"),
                "profile_cache_read_status": profile_status,
                "server_frontend_cached_tokens": server.get("server_frontend_cached_tokens"),
                "server_frontend_input_tokens": server.get("server_frontend_input_tokens"),
                "server_frontend_cache_hit_rate": server.get("server_frontend_cache_hit_rate"),
                "server_frontend_cached_to_input_ratio": server.get(
                    "server_frontend_cached_to_input_ratio"
                ),
                "server_cache_metric_scope": server.get("server_cache_metric_scope"),
                "kv_write_scope": "physical store only if explicit cache_write_tokens exists; otherwise derived eligibility proxy",
                "evidence_classification": "Evidence" if cache_total is not None else "Unknown",
            }
        )
    return pd.DataFrame(rows)


def _server_cache_metrics(raw_root: Path, artifacts: list[Any]) -> pd.DataFrame:
    rows = []
    for path in find_aggregate_jsons(raw_root, artifacts=artifacts):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        concurrency = parse_concurrency(str(path))
        if concurrency is None:
            continue
        server = payload.get("server_metrics", {}) if isinstance(payload, dict) else {}
        cache = server.get("cache", {}) if isinstance(server, dict) else {}
        cached = _number(cache.get("frontend_cached_tokens")) if isinstance(cache, dict) else None
        input_tokens = _number(cache.get("frontend_input_tokens")) if isinstance(cache, dict) else None
        rows.append(
            {
                "concurrency": concurrency,
                "server_frontend_cached_tokens": cached,
                "server_frontend_input_tokens": input_tokens,
                "server_frontend_cache_hit_rate": _number(cache.get("frontend_cache_hit_rate"))
                if isinstance(cache, dict)
                else None,
                "server_frontend_cached_to_input_ratio": _ratio(cached, input_tokens),
                "server_cache_metric_scope": "aggregate.server_metrics.cache frontend scope; not per-request physical KV allocation",
            }
        )
    columns = [
        "concurrency",
        "server_frontend_cached_tokens",
        "server_frontend_input_tokens",
        "server_frontend_cache_hit_rate",
        "server_frontend_cached_to_input_ratio",
        "server_cache_metric_scope",
    ]
    return pd.DataFrame(rows, columns=columns)


def _mtp_metrics(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in summary.iterrows():
        observed = _number(row.get("mtp_draft_tokens_total")) is not None
        rows.append(
            {
                "concurrency": row["concurrency"],
                "configured_algorithm": "EAGLE",
                "configured_simulated_acceptance_length": 2.99,
                "configured_draft_tokens": 4,
                "mtp_draft_tokens_total": row.get("mtp_draft_tokens_total"),
                "mtp_accepted_tokens_total": row.get("mtp_accepted_tokens_total"),
                "mtp_acceptance_rate_mean": row.get("mtp_acceptance_rate_mean"),
                "mtp_acceptance_length_mean": row.get("mtp_acceptance_length_mean"),
                "request_metric_status": "observed" if observed else "not_exported_in_profile_rows",
                "tps_interpretation": "weighted decode TPS includes configured MTP behavior; it is not non-MTP hardware TPS",
                "evidence_classification": "Evidence" if observed else "Unknown",
            }
        )
    return pd.DataFrame(rows)


def _coverage_matrix(profiled: pd.DataFrame, source_ids: set[str]) -> pd.DataFrame:
    roots = sorted(source_ids | set(profiled.get("root_trace_id", pd.Series(dtype="string")).dropna().astype(str)))
    result = pd.DataFrame({"root_trace_id": roots})
    for concurrency in (8, 12, 16):
        subset = profiled.loc[pd.to_numeric(profiled.get("concurrency"), errors="coerce") == concurrency]
        counts = subset.groupby("root_trace_id").size() if not subset.empty else pd.Series(dtype=int)
        result[f"conc{concurrency}_profiled_request_count"] = result["root_trace_id"].map(counts).fillna(0).astype(int)
        result[f"conc{concurrency}_present"] = result[f"conc{concurrency}_profiled_request_count"] > 0
    return result


def _worker_distribution(profiled: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (concurrency, worker), group in profiled.groupby(["concurrency", "worker_id"], dropna=False):
        values = summarize_requests(group)
        rows.append(
            {
                "concurrency": concurrency,
                "worker_id": worker,
                "profiled_request_count": values["profiled_request_count"],
                "root_id_count": values["root_id_count"],
                "output_tokens_total": values["output_tokens_total"],
                "ttft_median_ms": values["ttft_median_ms"],
                "weighted_decode_tps": values["weighted_decode_tps"],
                "scope": "observed request worker_id; absent/null identifiers are retained",
            }
        )
    return pd.DataFrame(rows)


def _root_subagent_summary(profiled: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (concurrency, branch), group in profiled.groupby(
        ["concurrency", "source_branch_type"], dropna=False
    ):
        values = summarize_requests(group)
        rows.append(
            {
                "concurrency": concurrency,
                "source_branch_type": branch if pd.notna(branch) else "unknown",
                "profiled_request_count": values["profiled_request_count"],
                "root_id_count": values["root_id_count"],
                "input_sequence_length_total": values["input_sequence_length_total"],
                "output_tokens_total": values["output_tokens_total"],
                "ttft_median_ms": values["ttft_median_ms"],
                "ttft_p90_ms": values["ttft_p90_ms"],
                "itl_weighted_ms": values["itl_weighted_ms"],
                "weighted_decode_tps": values["weighted_decode_tps"],
                "e2e_median_ms": values["e2e_median_ms"],
                "wall_output_tps": values["wall_output_tps"],
                "scope": "source branch origin joined through loader metadata; not replay suffix taxonomy",
            }
        )
    return pd.DataFrame(rows)


def _context_cache_relationship(profiled: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for concurrency, group in profiled.groupby("concurrency", dropna=False):
        for field in ("source_input_tokens", "theoretical_new_tokens", "theoretical_cache_ratio"):
            values = pd.to_numeric(group.get(field), errors="coerce")
            ttft = pd.to_numeric(group.get("ttft_ms"), errors="coerce")
            valid = values.notna() & ttft.notna()
            rows.append(
                {
                    "concurrency": concurrency,
                    "relationship": f"{field}_vs_ttft_ms",
                    "sample_count": int(valid.sum()),
                    "spearman_rho": float(values[valid].corr(ttft[valid], method="spearman"))
                    if valid.sum() >= 3
                    else None,
                    "interpretation": (
                        "source-workload theoretical cache shape; not actual H200 cache residency"
                        if field.startswith("theoretical")
                        else "source workload input token count; may differ from AIPerf input sequence length"
                    ),
                }
            )
    return pd.DataFrame(rows)


def _write_requested_id_tables(
    processed: Path, raw_all: pd.DataFrame, profiled: pd.DataFrame, resolution: pd.DataFrame
) -> None:
    for _, item in resolution.iterrows():
        resolved = item.get("resolved_full_source_trace_id")
        if not isinstance(resolved, str) or not resolved:
            continue
        rows = []
        for concurrency in (8, 12, 16):
            all_group = raw_all.loc[
                (pd.to_numeric(raw_all.get("concurrency"), errors="coerce") == concurrency)
                & (raw_all.get("root_trace_id").astype("string") == resolved)
            ]
            profile_group = profiled.loc[
                (pd.to_numeric(profiled.get("concurrency"), errors="coerce") == concurrency)
                & (profiled.get("root_trace_id").astype("string") == resolved)
            ]
            if all_group.empty and profile_group.empty:
                continue
            metrics = summarize_requests(profile_group)
            phase = all_group.get("benchmark_phase", pd.Series(dtype="string")).astype("string").str.lower()
            metrics.update(
                {
                    "id_label": item["id_label"],
                    "root_trace_id": resolved,
                    "concurrency": concurrency,
                    "all_request_count": int(len(all_group)),
                    "warmup_count": int(phase.isin(["warmup", "warming", "warm_up"]).sum()),
                    "error_count": int(_truthy_count(all_group.get("error_present"))),
                    "cancellation_count": int(_truthy_count(all_group.get("was_cancelled"))),
                    "sample_quality": "sparse" if len(profile_group) < 3 else "observed",
                }
            )
            rows.append(metrics)
        if rows:
            pd.DataFrame(rows).sort_values("concurrency").to_csv(
                processed / f"{str(item['id_label']).lower()}_by_concurrency.csv", index=False
            )
            subset = profiled.loc[profiled.get("root_trace_id").astype("string") == resolved]
            review = subset[
                [
                    column
                    for column in (
                        "concurrency",
                        "root_trace_id",
                        "conversation_id",
                        "source_outer_idx",
                        "source_inner_idx",
                        "turn_index",
                        "worker_id",
                        "input_sequence_length",
                        "logical_prompt_tokens",
                        "cache_read_tokens",
                        "new_prompt_tokens",
                        "output_tokens",
                        "ttft_ms",
                        "itl_ms",
                        "e2e_ms",
                        "match_class",
                    )
                    if column in subset
                ]
            ].copy()
            review.to_csv(processed / f"{str(item['id_label']).lower()}_requests_review.csv", index=False)


def _cross_concurrency_pairs(profiled: pd.DataFrame) -> pd.DataFrame:
    pairs = build_pair_table(profiled)
    if pairs.empty:
        return pairs
    pairs["comparison_kind"] = "within_gpu_resident_mtp_cross_concurrency"
    return pairs


def _hisparse_c8_pairs(profiled: pd.DataFrame, hisparse: pd.DataFrame) -> pd.DataFrame:
    if hisparse.empty:
        return pd.DataFrame()
    new = profiled.loc[pd.to_numeric(profiled.get("concurrency"), errors="coerce") == 8].copy()
    old = hisparse.loc[pd.to_numeric(hisparse.get("concurrency"), errors="coerce") == 8].copy()
    old = _add_source_key(old)
    new = _add_source_key(new)
    new["comparison_group"] = "gpu_resident_mtp_c8"
    old["comparison_group"] = "hisparse_c8"
    pairs = build_pair_table(
        pd.concat([old, new], ignore_index=True, sort=False),
        systems=("hisparse_c8", "gpu_resident_mtp_c8"),
    )
    if not pairs.empty:
        pairs["comparison_kind"] = "observed_system_ratio"
    return pairs


def _add_source_key(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    root = result.get("root_trace_id", pd.Series(dtype="string")).astype("string")
    outer = pd.to_numeric(result.get("source_outer_idx"), errors="coerce")
    inner = pd.to_numeric(result.get("source_inner_idx"), errors="coerce").fillna(-1)
    valid = root.notna() & outer.notna()
    result["exact_source_key"] = (
        root.astype(str) + "|" + outer.fillna(-999999).astype("int64").astype(str) + "|" + inner.astype("int64").astype(str)
    ).where(valid)
    return result


def _pair_summary(pairs: pd.DataFrame, *, by_root: bool = False) -> pd.DataFrame:
    if pairs.empty:
        return pd.DataFrame(
            columns=[
                "left_group",
                "right_group",
                "matched_source_key_count",
                "strict_ttft_count",
                "strict_decode_count",
            ]
        )
    group_columns = ["left_group", "right_group"]
    if by_root:
        group_columns.insert(0, "root_trace_id")
    rows = []
    for keys, group in pairs.groupby(group_columns, dropna=False):
        values = dict(zip(group_columns, keys if isinstance(keys, tuple) else (keys,), strict=True))
        values.update(
            {
                "matched_source_key_count": int(len(group)),
                "same_output_length_count": int(group["same_output_length"].sum()),
                "strict_ttft_count": int(group["strict_ttft_subset"].sum()),
                "strict_decode_count": int(group["strict_decode_subset"].sum()),
                "median_ttft_ratio_right_over_left": percentile(group["ttft_ratio_right_over_left"], 0.5),
                "median_itl_ratio_right_over_left": percentile(
                    group.loc[group["strict_decode_subset"], "itl_ratio_right_over_left"], 0.5
                ),
                "median_e2e_ratio_right_over_left": percentile(group["e2e_ratio_right_over_left"], 0.5),
                "matching_method": "source_trace_id+source_outer_idx+source_inner_idx",
            }
        )
        rows.append(values)
    return pd.DataFrame(rows)


def _system_comparison(
    pairs: pd.DataFrame, profiled: pd.DataFrame, hisparse: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    new_summary = summarize_requests(
        profiled.loc[pd.to_numeric(profiled.get("concurrency"), errors="coerce") == 8]
    )
    old_summary = summarize_requests(
        hisparse.loc[pd.to_numeric(hisparse.get("concurrency"), errors="coerce") == 8]
    )
    for metric in ("ttft_median_ms", "weighted_decode_tps", "wall_output_tps", "output_tokens_total"):
        old_value = old_summary.get(metric)
        new_value = new_summary.get(metric)
        rows.append(
            {
                "comparison_scope": "run_level_unpaired_observed_system_difference",
                "metric": metric,
                "hisparse_c8_value": old_value,
                "gpu_resident_mtp_c8_value": new_value,
                "gpu_resident_over_hisparse_ratio": _ratio(_number(new_value), _number(old_value)),
                "sample_count": min(old_summary["profiled_request_count"], new_summary["profiled_request_count"]),
                "caveat": "16→32 GPUs, 1P1D→2P2D, KV mode/dtype, MTP, and software may differ; not a causal HiSparse estimate.",
            }
        )
    if not pairs.empty:
        summary = _pair_summary(pairs)
        for _, item in summary.iterrows():
            for metric in ("ttft", "itl", "e2e"):
                rows.append(
                    {
                        "comparison_scope": "source_key_matched_median_observed_system_ratio",
                        "metric": f"{metric}_ratio_gpu_resident_over_hisparse",
                        "hisparse_c8_value": None,
                        "gpu_resident_mtp_c8_value": item.get(
                            f"median_{metric}_ratio_right_over_left"
                        ),
                        "gpu_resident_over_hisparse_ratio": item.get(
                            f"median_{metric}_ratio_right_over_left"
                        ),
                        "sample_count": item.get(
                            "strict_decode_count" if metric == "itl" else "strict_ttft_count"
                        ),
                        "caveat": "Source-key matching controls workload identity only; it does not isolate a single architecture change.",
                    }
                )
    return pd.DataFrame(rows)


def _review_pairs(pairs: pd.DataFrame) -> pd.DataFrame:
    if pairs.empty:
        return pairs
    columns = [
        column
        for column in (
            "root_trace_id",
            "exact_source_key",
            "left_group",
            "right_group",
            "left_record_count",
            "right_record_count",
            "left_ttft_ms",
            "right_ttft_ms",
            "ttft_ratio_right_over_left",
            "left_itl_ms",
            "right_itl_ms",
            "itl_ratio_right_over_left",
            "same_output_length",
            "strict_ttft_subset",
            "strict_decode_subset",
        )
        if column in pairs
    ]
    return pairs.sort_values(["root_trace_id", "exact_source_key"])[columns].head(500)


def _top_ids(profiled: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (concurrency, root), group in profiled.groupby(["concurrency", "root_trace_id"], dropna=False):
        metrics = summarize_requests(group)
        rows.append(
            {
                "concurrency": concurrency,
                "root_trace_id": root,
                "profiled_request_count": metrics["profiled_request_count"],
                "input_sequence_length_total": metrics["input_sequence_length_total"],
                "output_tokens_total": metrics["output_tokens_total"],
                "ttft_median_ms": metrics["ttft_median_ms"],
                "e2e_median_ms": metrics["e2e_median_ms"],
                "wall_span_s": metrics["wall_span_s"],
                "wall_output_tps": metrics["wall_output_tps"],
            }
        )
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values(["concurrency", "input_sequence_length_total"], ascending=[True, False])


def _runtime_configuration() -> pd.DataFrame:
    rows = [
        ("target_model", "zai-org/GLM-5.2-FP8", "Evidence", "at-run recipe"),
        ("hardware", "H200", "Evidence", "at-run recipe and server logs"),
        (
            "total_gpus",
            "32 backend H200 (2×8 prefill + 2×8 decode; 40 configured GPUs includes non-backend allocation)",
            "Evidence",
            "server logs/resource snapshot",
        ),
        ("serving", "P/D disaggregated with Mooncake", "Evidence", "at-run recipe and server logs"),
        ("kv_cache_dtype", "fp8_e4m3", "Evidence", "runtime decode ServerArgs"),
        (
            "kv_offloading",
            "none (CPU offload=0; decode KV offload=false; LMCache=false)",
            "Evidence",
            "runtime decode ServerArgs",
        ),
        ("hisparse", "OFF (enable_hisparse=false)", "Evidence", "runtime decode ServerArgs"),
        ("context_length", "1048576", "Evidence", "at-run recipe and server logs"),
        ("decode_page_size", "64", "Evidence", "runtime decode ServerArgs"),
        ("decode_max_running_requests", "200", "Evidence", "at-run recipe"),
        ("mtp", "EAGLE steps=3 topk=1 draft_tokens=4", "Evidence", "at-run recipe and server logs"),
        ("simulated_acceptance", "2.99; match-expected; real-draft-token", "Evidence", "runtime server log"),
    ]
    return pd.DataFrame(rows, columns=["field", "value", "classification", "source"])


def _three_system_architecture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "system": "A: user-reported local reference",
                "gpu_count": 2,
                "topology": "aggregated",
                "concurrency": 1,
                "context": 202752,
                "kv_mode": "inference_gpu_resident_unverified",
                "hisparse": "inference_off_unverified",
                "mtp": "Unknown",
                "comparison_status": "contextual reference only; no raw local logs",
            },
            {
                "system": "B: public H200 HiSparse",
                "gpu_count": 16,
                "topology": "1P×8 + 1D×8",
                "concurrency": 8,
                "context": 1048576,
                "kv_mode": "HiSparse / host-pinned full decode KV per baseline provenance",
                "hisparse": "on",
                "mtp": "off",
                "comparison_status": "same-concurrency observed-system comparison available",
            },
            {
                "system": "C: public H200 GPU-resident MTP",
                "gpu_count": 32,
                "topology": "2P×8 + 2D×8",
                "concurrency": "8,12,16",
                "context": 1048576,
                "kv_mode": "runtime evidence: FP8 GPU-resident controls; CPU/KV offload and LMCache disabled",
                "hisparse": "runtime evidence: OFF (enable_hisparse=false)",
                "mtp": "runtime evidence: EAGLE MTP with simulated acceptance",
                "comparison_status": "primary study",
            },
        ]
    )


def _aggregate_validation(profiled: pd.DataFrame, raw_root: Path, artifacts: list[Any]) -> pd.DataFrame:
    raw = recompute_raw_aggregates(profiled)
    paths = find_aggregate_jsons(raw_root, artifacts=artifacts)
    published = load_published_aggregates(
        paths, artifact_context=aggregate_artifact_context(paths, artifacts)
    )
    return validate_aggregates(raw, published)


def _validation_summary(validation: pd.DataFrame) -> pd.DataFrame:
    if validation.empty:
        return pd.DataFrame(columns=["concurrency", "validation_status", "metric_count"])
    return (
        validation.groupby(["concurrency", "validation_status"], dropna=False)
        .size()
        .rename("metric_count")
        .reset_index()
    )


def _truthy_count(series: Any) -> int:
    if series is None:
        return 0
    normalized = pd.Series(series).astype("string").str.lower().str.strip()
    return int(normalized.isin(["true", "1", "yes", "y"]).sum())


def _read_parquet_or_empty(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()


def _write_parquet(frame: pd.DataFrame, path: Path) -> None:
    frame.to_parquet(path, index=False)


def _write_status(processed: Path, payload: dict[str, Any]) -> None:
    with (processed / "analysis_status.json").open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _arrow_type(column: str) -> Any:
    import pyarrow as pa

    if column in STRING_COLUMNS:
        return pa.string()
    if column in INT_COLUMNS:
        return pa.int64()
    if column in BOOL_COLUMNS:
        return pa.bool_()
    return pa.float64()


def _coerce_row(row: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for column in ROW_COLUMNS:
        value = row.get(column)
        if _missing(value):
            clean[column] = None
        elif column in STRING_COLUMNS:
            clean[column] = str(value)
        elif column in INT_COLUMNS:
            clean[column] = int(float(value))
        elif column in BOOL_COLUMNS:
            clean[column] = bool(value)
        else:
            clean[column] = float(value)
    return clean


def _missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(value != value)
    except (TypeError, ValueError):
        return False


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if number != number else number


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


if __name__ == "__main__":
    raise SystemExit(main())
