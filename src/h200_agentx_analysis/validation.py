"""Raw-profile versus published aggregate result validation."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .artifact_parser import (
    AGGREGATE_CATEGORY,
    RUN_SUMMARY_CATEGORY,
    ArtifactInfo,
    _duration_to_ms,
    flatten_record,
    lookup_flat_value,
    parse_concurrency,
)
from .metrics import percentile, wall_clock_span

_VALIDATION_METRICS: dict[str, tuple[str, ...]] = {
    "successful_profiled_request_count": (
        "successful_profiled_request_count",
        "successful_requests",
        "num_successful_requests",
        "num_requests_successful",
        "success_count",
        "request_count",
    ),
    "total_input_tokens": ("total_input_tokens", "input_tokens_total", "input_token_count"),
    "total_output_tokens": ("total_output_tokens", "output_tokens_total", "output_token_count"),
    "mean_ttft_ms": (
        "mean_ttft_ms",
        "mean_time_to_first_token_ms",
        "mean_time_to_first_token",
        "ttft_mean",
    ),
    "p50_ttft_ms": ("p50_ttft_ms", "ttft_p50", "ttft_p50_ms", "time_to_first_token_p50"),
    "p75_ttft_ms": ("p75_ttft_ms", "ttft_p75", "ttft_p75_ms", "time_to_first_token_p75"),
    "p90_ttft_ms": ("p90_ttft_ms", "ttft_p90", "ttft_p90_ms", "time_to_first_token_p90"),
    "p95_ttft_ms": ("p95_ttft_ms", "ttft_p95", "ttft_p95_ms", "time_to_first_token_p95"),
    "mean_itl_ms": (
        "mean_itl_ms",
        "mean_inter_token_latency_ms",
        "mean_inter_token_latency",
        "itl_mean",
        "mean_tpot_ms",
    ),
    "p50_itl_ms": ("p50_itl_ms", "itl_p50", "inter_token_latency_p50", "tpot_p50"),
    "p75_itl_ms": ("p75_itl_ms", "itl_p75", "inter_token_latency_p75", "tpot_p75"),
    "p90_itl_ms": ("p90_itl_ms", "itl_p90", "inter_token_latency_p90", "tpot_p90"),
    "p95_itl_ms": ("p95_itl_ms", "itl_p95", "inter_token_latency_p95", "tpot_p95"),
    "mean_e2e_ms": ("mean_e2e_ms", "mean_request_latency_ms", "mean_request_latency", "e2e_mean"),
    "p50_e2e_ms": ("p50_e2e_ms", "e2e_p50", "request_latency_p50"),
    "p75_e2e_ms": ("p75_e2e_ms", "e2e_p75", "request_latency_p75"),
    "p90_e2e_ms": ("p90_e2e_ms", "e2e_p90", "request_latency_p90"),
    "p95_e2e_ms": ("p95_e2e_ms", "e2e_p95", "request_latency_p95"),
    "input_throughput_tps": (
        "input_throughput_tps",
        "input_token_throughput",
        "input_tokens_per_second",
    ),
    "output_throughput_tps": (
        "output_throughput_tps",
        "output_token_throughput",
        "output_tokens_per_second",
    ),
    "total_throughput_tps": (
        "total_throughput_tps",
        "total_token_throughput",
        "total_tokens_per_second",
    ),
    "duration_s": ("duration_s", "benchmark_duration_s", "duration_seconds", "elapsed_time_s"),
    "gpu_count": ("gpu_count", "num_gpus", "total_gpus"),
    "per_gpu_input_throughput_tps": ("per_gpu_input_throughput_tps",),
    "per_gpu_output_throughput_tps": ("per_gpu_output_throughput_tps",),
    "per_gpu_total_throughput_tps": ("per_gpu_total_throughput_tps",),
    "target_model": ("model", "target_model"),
    "precision": ("precision",),
    "framework": ("framework",),
    "metadata_concurrency": ("conc", "concurrency", "target_concurrency"),
}

_CATEGORICAL_METRICS = {"target_model", "precision", "framework"}

# The pinned InferenceX processor writes nested request metrics in seconds.
# AIPerf's own profile_export_aiperf.json instead uses metric ``avg`` values
# with an adjacent unit. Both layouts are accepted, while their units remain
# explicit in the extraction code below.
_PUBLISHED_PATH_ALIASES: dict[str, tuple[str, ...]] = {
    "successful_profiled_request_count": ("num_requests_successful",),
    "mean_ttft_ms": ("request_metrics.latency.ttft.mean", "time_to_first_token.avg"),
    "p50_ttft_ms": ("request_metrics.latency.ttft.p50", "time_to_first_token.p50"),
    "p75_ttft_ms": ("request_metrics.latency.ttft.p75", "time_to_first_token.p75"),
    "p90_ttft_ms": ("request_metrics.latency.ttft.p90", "time_to_first_token.p90"),
    "p95_ttft_ms": ("request_metrics.latency.ttft.p95", "time_to_first_token.p95"),
    "mean_itl_ms": (
        "request_metrics.latency.itl.mean",
        "request_metrics.latency.tpot.mean",
        "inter_token_latency.avg",
    ),
    "p50_itl_ms": (
        "request_metrics.latency.itl.p50",
        "request_metrics.latency.tpot.p50",
        "inter_token_latency.p50",
    ),
    "p75_itl_ms": (
        "request_metrics.latency.itl.p75",
        "request_metrics.latency.tpot.p75",
        "inter_token_latency.p75",
    ),
    "p90_itl_ms": (
        "request_metrics.latency.itl.p90",
        "request_metrics.latency.tpot.p90",
        "inter_token_latency.p90",
    ),
    "p95_itl_ms": (
        "request_metrics.latency.itl.p95",
        "request_metrics.latency.tpot.p95",
        "inter_token_latency.p95",
    ),
    "mean_e2e_ms": ("request_metrics.latency.e2el.mean", "request_latency.avg"),
    "p50_e2e_ms": ("request_metrics.latency.e2el.p50", "request_latency.p50"),
    "p75_e2e_ms": ("request_metrics.latency.e2el.p75", "request_latency.p75"),
    "p90_e2e_ms": ("request_metrics.latency.e2el.p90", "request_latency.p90"),
    "p95_e2e_ms": ("request_metrics.latency.e2el.p95", "request_latency.p95"),
    "input_throughput_tps": ("request_metrics.throughput.input.tokens_per_second",),
    "output_throughput_tps": ("request_metrics.throughput.output.tokens_per_second",),
    "total_throughput_tps": ("request_metrics.throughput.total.tokens_per_second",),
    "duration_s": ("request_metrics.throughput.duration_seconds", "benchmark_duration"),
    "gpu_count": ("num_gpus",),
    "per_gpu_input_throughput_tps": ("request_metrics.throughput.per_gpu.input_tput_tps",),
    "per_gpu_output_throughput_tps": ("request_metrics.throughput.per_gpu.output_tput_tps",),
    "per_gpu_total_throughput_tps": ("request_metrics.throughput.per_gpu.total_tput_tps",),
    "target_model": ("model",),
    "precision": ("precision",),
    "framework": ("framework",),
    "metadata_concurrency": ("conc",),
}


def recompute_raw_aggregates(profiled_frame: Any) -> Any:
    """Recompute aggregate metrics using exactly the supplied profiling rows."""

    import pandas as pd

    columns = ["concurrency", *_VALIDATION_METRICS.keys()]
    if profiled_frame.empty:
        return pd.DataFrame(columns=columns)
    frame = profiled_frame.copy()
    _ensure_columns(
        frame,
        [
            "concurrency",
            "input_tokens",
            "output_tokens",
            "ttft_ms",
            "itl_ms",
            "e2e_ms",
            "target_gpu_count",
            "target_model",
            "target_precision",
            "framework",
        ],
    )
    rows: list[dict[str, Any]] = []
    for concurrency, group in frame.groupby("concurrency", dropna=False):
        input_tokens = pd.to_numeric(group["input_tokens"], errors="coerce")
        output_tokens = pd.to_numeric(group["output_tokens"], errors="coerce")
        ttft = pd.to_numeric(group["ttft_ms"], errors="coerce")
        itl = pd.to_numeric(group["itl_ms"], errors="coerce")
        e2e = pd.to_numeric(group["e2e_ms"], errors="coerce")
        span, _ = wall_clock_span(group)
        total_input = float(input_tokens.fillna(0).sum())
        total_output = float(output_tokens.fillna(0).sum())
        gpu_values = pd.to_numeric(group["target_gpu_count"], errors="coerce").dropna()
        input_tps = total_input / span if span and span > 0 else None
        output_tps = total_output / span if span and span > 0 else None
        total_tps = (total_input + total_output) / span if span and span > 0 else None
        gpu_count = float(gpu_values.median()) if not gpu_values.empty else None
        row = {
            "concurrency": concurrency,
            "successful_profiled_request_count": int(len(group)),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "mean_ttft_ms": _mean(ttft),
            "p50_ttft_ms": percentile(ttft, 0.5),
            "p75_ttft_ms": percentile(ttft, 0.75),
            "p90_ttft_ms": percentile(ttft, 0.9),
            "p95_ttft_ms": percentile(ttft, 0.95),
            "mean_itl_ms": _mean(itl.loc[itl > 0]),
            "p50_itl_ms": percentile(itl.loc[itl > 0], 0.5),
            "p75_itl_ms": percentile(itl.loc[itl > 0], 0.75),
            "p90_itl_ms": percentile(itl.loc[itl > 0], 0.9),
            "p95_itl_ms": percentile(itl.loc[itl > 0], 0.95),
            "mean_e2e_ms": _mean(e2e),
            "p50_e2e_ms": percentile(e2e, 0.5),
            "p75_e2e_ms": percentile(e2e, 0.75),
            "p90_e2e_ms": percentile(e2e, 0.9),
            "p95_e2e_ms": percentile(e2e, 0.95),
            "input_throughput_tps": input_tps,
            "output_throughput_tps": output_tps,
            "total_throughput_tps": total_tps,
            "duration_s": span,
            "gpu_count": gpu_count,
            "per_gpu_input_throughput_tps": input_tps / gpu_count if input_tps is not None and gpu_count else None,
            "per_gpu_output_throughput_tps": output_tps / gpu_count if output_tps is not None and gpu_count else None,
            "per_gpu_total_throughput_tps": total_tps / gpu_count if total_tps is not None and gpu_count else None,
            "target_model": _first_text(group["target_model"]),
            "precision": _first_text(group["target_precision"]),
            "framework": _first_text(group["framework"]),
            "metadata_concurrency": concurrency,
        }
        rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def load_published_aggregates(
    aggregate_paths: Iterable[str | Path],
    *,
    artifact_context: Mapping[str, Mapping[str, Any]] | None = None,
) -> Any:
    """Extract known metrics from aggregate JSON files without assuming layout."""

    import pandas as pd

    columns = [
        "source_file_path",
        "concurrency",
        "artifact_match_status",
        "artifact_id",
        "artifact_name",
        *[f"published_{key}" for key in _VALIDATION_METRICS],
        "published_total_input_tokens_derivation",
        "published_total_output_tokens_derivation",
        "unparsed",
    ]
    rows: list[dict[str, Any]] = []
    for source in sorted(Path(path) for path in aggregate_paths):
        try:
            with source.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            rows.append(
                {"source_file_path": str(source), "concurrency": None, "unparsed": str(exc)}
            )
            continue
        mappings = _candidate_result_objects(payload)
        if not mappings:
            mappings = [payload] if isinstance(payload, Mapping) else []
        context = (artifact_context or {}).get(str(source), {})
        context_concurrency = context.get("concurrency")
        for mapping in mappings:
            flattened = flatten_record(mapping)
            concurrency_value, _ = lookup_flat_value(
                flattened, ("concurrency", "target_concurrency", "conc")
            )
            concurrency = _number(concurrency_value)
            if concurrency is None:
                concurrency = _number(context_concurrency)
            if concurrency is None:
                concurrency = parse_concurrency(str(source))
            row: dict[str, Any] = {
                "source_file_path": str(source),
                "concurrency": int(concurrency) if concurrency is not None else None,
                "artifact_match_status": context.get("artifact_match_status", "unmatched"),
                "artifact_id": context.get("artifact_id"),
                "artifact_name": context.get("artifact_name"),
                "unparsed": None,
            }
            found = 0
            for canonical, aliases in _VALIDATION_METRICS.items():
                value = _published_metric_value(flattened, canonical, aliases)
                derivation = None
                if value is None and canonical in {
                    "total_input_tokens",
                    "total_output_tokens",
                }:
                    value, derivation = _derive_published_token_total(flattened, canonical)
                row[f"published_{canonical}"] = value
                if derivation is not None:
                    row[f"published_{canonical}_derivation"] = derivation
                found += int(value is not None)
            if found == 0:
                row["unparsed"] = "no recognized aggregate metrics"
            rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def validate_aggregates(raw_aggregates: Any, published_aggregates: Any) -> Any:
    """Compare recalculated raw aggregates against published JSON values.

    A metric is only marked pass/fail when both sides are present.  Otherwise
    it stays ``not_comparable``—absence of a metric is never a validation pass.
    """

    import pandas as pd

    columns = [
        "concurrency",
        "metric",
        "raw_value",
        "published_value",
        "published_value_derivation",
        "absolute_difference",
        "relative_difference",
        "tolerance_absolute",
        "tolerance_relative",
        "validation_status",
        "validation_note",
        "published_source_file_path",
        "published_candidate_file_count",
        "published_candidate_object_count",
        "published_candidate_source_paths",
        "published_artifact_match_status",
        "published_artifact_id",
        "published_artifact_name",
    ]
    if raw_aggregates.empty and published_aggregates.empty:
        return pd.DataFrame(columns=columns)
    raw = raw_aggregates.copy()
    published = published_aggregates.copy()
    _ensure_columns(raw, ["concurrency"])
    _ensure_columns(published, ["concurrency", "source_file_path"])
    # A run summary and its per-concurrency aggregate can both contain values
    # for one concurrency.  Picking the first path would fabricate a direct
    # validation target, so multiple published JSON candidates are explicitly
    # flagged and skipped below.
    published = published.sort_values("source_file_path", na_position="last")
    source_by_conc: dict[Any, tuple[Any | None, dict[str, Any]]] = {}
    for concurrency, group in published.groupby("concurrency", dropna=False):
        source_by_conc[concurrency] = _select_published_candidate(group)
    raw_by_conc: dict[Any, Any] = {}
    for concurrency, group in raw.groupby("concurrency", dropna=False):
        raw_by_conc[concurrency] = group.iloc[0]
    concurrencies = sorted(
        set(raw_by_conc) | set(source_by_conc),
        key=lambda value: (value is None, value if value is not None else -1),
    )
    rows: list[dict[str, Any]] = []
    for concurrency in concurrencies:
        raw_row = raw_by_conc.get(concurrency)
        published_row, candidate_context = source_by_conc.get(
            concurrency, (None, _empty_candidate_context())
        )
        for metric in _VALIDATION_METRICS:
            raw_value = raw_row.get(metric) if raw_row is not None else None
            published_value = (
                published_row.get(f"published_{metric}")
                if published_row is not None
                else None
            )
            published_derivation = (
                published_row.get(f"published_{metric}_derivation")
                if published_row is not None
                else None
            )
            blocked_status = candidate_context.get("selection_status")
            if blocked_status:
                absolute = relative = None
                status = str(blocked_status)
                published_value = None
                published_derivation = None
            else:
                absolute, relative, status = _compare_metric(
                    metric, raw_value, published_value, derivation=published_derivation
                )
            absolute_tolerance, relative_tolerance = _tolerances(
                metric, raw_value, published_value, derivation=published_derivation
            )
            note = candidate_context.get("selection_note") or _validation_note(
                metric, raw_value, published_value, status, derivation=published_derivation
            )
            rows.append(
                {
                    "concurrency": concurrency,
                    "metric": metric,
                    "raw_value": raw_value,
                    "published_value": published_value,
                    "published_value_derivation": published_derivation,
                    "absolute_difference": absolute,
                    "relative_difference": relative,
                    "tolerance_absolute": absolute_tolerance,
                    "tolerance_relative": relative_tolerance,
                    "validation_status": status,
                    "validation_note": note,
                    "published_source_file_path": published_row.get("source_file_path")
                    if published_row is not None
                    else None,
                    "published_candidate_file_count": candidate_context[
                        "candidate_file_count"
                    ],
                    "published_candidate_object_count": candidate_context[
                        "candidate_object_count"
                    ],
                    "published_candidate_source_paths": candidate_context["source_paths"],
                    "published_artifact_match_status": candidate_context[
                        "artifact_match_status"
                    ],
                    "published_artifact_id": candidate_context["artifact_id"],
                    "published_artifact_name": candidate_context["artifact_name"],
                }
            )
    return pd.DataFrame(rows, columns=columns)


def _select_published_candidate(group: Any) -> tuple[Any | None, dict[str, Any]]:
    """Return one auditable aggregate candidate, or an explicit skip status.

    A single JSON file may legitimately contain one result object for each
    concurrency.  More than one recognized object for the *same* concurrency,
    or recognized objects from multiple JSON files, is ambiguous without a
    source-level equivalence rule and must not be resolved by path ordering.
    """

    recognized = group.loc[group.apply(_has_recognized_published_metric, axis=1)].copy()
    source_paths = _unique_text_values(recognized.get("source_file_path"))
    context = _empty_candidate_context()
    context.update(
        {
            "candidate_file_count": len(source_paths),
            "candidate_object_count": int(len(recognized)),
            "source_paths": "; ".join(source_paths) if source_paths else None,
        }
    )
    if recognized.empty:
        all_paths = _unique_text_values(group.get("source_file_path"))
        context["source_paths"] = "; ".join(all_paths) if all_paths else None
        if all_paths:
            context.update(
                {
                    "selection_status": "no_recognized_published_metrics",
                    "selection_note": (
                        "Unknown: published aggregate file(s) were found, but no supported "
                        "metric path was recognized for this concurrency."
                    ),
                }
            )
        return None, context
    if len(source_paths) > 1:
        context.update(
            {
                "selection_status": "ambiguous_published_candidates",
                "selection_note": (
                    "Unknown: multiple published aggregate JSON candidates exist for this "
                    "concurrency; raw-vs-published comparison was skipped rather than "
                    "selecting one by path order."
                ),
            }
        )
        return None, context
    if len(recognized) > 1:
        context.update(
            {
                "selection_status": "ambiguous_published_candidates",
                "selection_note": (
                    "Unknown: one published aggregate JSON contains multiple recognized "
                    "objects for this concurrency; comparison was skipped."
                ),
            }
        )
        return None, context
    candidate = recognized.iloc[0]
    artifact_status = _text(candidate.get("artifact_match_status")) or "unambiguous"
    context.update(
        {
            "artifact_match_status": artifact_status,
            "artifact_id": _text(candidate.get("artifact_id")),
            "artifact_name": _text(candidate.get("artifact_name")),
        }
    )
    if artifact_status != "unambiguous":
        status = (
            "ambiguous_artifact_context"
            if artifact_status == "ambiguous"
            else "unmatched_artifact_context"
        )
        context.update(
            {
                "selection_status": status,
                "selection_note": (
                    "Unknown: aggregate JSON could not be mapped unambiguously to an "
                    "inventory-confirmed aggregate/run-summary artifact; comparison was skipped."
                ),
            }
        )
        return None, context
    return candidate, context


def _empty_candidate_context() -> dict[str, Any]:
    return {
        "candidate_file_count": 0,
        "candidate_object_count": 0,
        "source_paths": None,
        "artifact_match_status": None,
        "artifact_id": None,
        "artifact_name": None,
        "selection_status": None,
        "selection_note": None,
    }


def _has_recognized_published_metric(row: Any) -> bool:
    return any(
        _text(row.get(f"published_{metric}")) is not None
        for metric in _VALIDATION_METRICS
    )


def _unique_text_values(values: Any) -> list[str]:
    if values is None:
        return []
    result: list[str] = []
    for value in values:
        text = _text(value)
        if text and text not in result:
            result.append(text)
    return result


def find_aggregate_jsons(
    raw_root: str | Path, *, artifacts: Iterable[ArtifactInfo] | None = None
) -> list[Path]:
    """Prefer per-concurrency aggregate JSONs; use run summaries only as fallback.

    ``results_bmk`` duplicates the same concurrency results in a list.  It is
    valuable as a secondary cross-check, but it is not a second independent
    validation target when an inventory-confirmed ``bmk_agentic`` artifact is
    present for that concurrency.
    """

    root = Path(raw_root)
    aggregate_artifacts = [
        artifact
        for artifact in (artifacts or [])
        if artifact.category == AGGREGATE_CATEGORY
    ]
    summary_artifacts = [
        artifact
        for artifact in (artifacts or [])
        if artifact.category == RUN_SUMMARY_CATEGORY
    ]
    if not root.exists():
        return []
    direct = sorted(
        path
        for path in root.rglob("*.json")
        if _matching_aggregate_artifacts(path, aggregate_artifacts)
    )
    if direct:
        return direct
    return sorted(
        path
        for path in root.rglob("*.json")
        if _matching_aggregate_artifacts(path, summary_artifacts)
    )


def aggregate_artifact_context(
    aggregate_paths: Iterable[str | Path], artifacts: Iterable[ArtifactInfo]
) -> dict[str, dict[str, Any]]:
    """Attach inventory metadata and flag ambiguous aggregate-file matches."""

    eligible = [
        artifact
        for artifact in artifacts
        if artifact.category in {AGGREGATE_CATEGORY, RUN_SUMMARY_CATEGORY}
    ]
    context: dict[str, dict[str, Any]] = {}
    for source in aggregate_paths:
        path = Path(source)
        matches = _matching_aggregate_artifacts(path, eligible)
        status = "unambiguous" if len(matches) == 1 else ("ambiguous" if matches else "unmatched")
        item = matches[0] if len(matches) == 1 else None
        context[str(path)] = {
            "artifact_match_status": status,
            "artifact_id": item.artifact_id if item else None,
            "artifact_name": item.name if item else None,
            "concurrency": item.concurrency if item else None,
        }
    return context


def _matching_aggregate_artifacts(path: Path, artifacts: Iterable[ArtifactInfo]) -> list[ArtifactInfo]:
    path_text = str(path).lower()
    return [
        artifact
        for artifact in artifacts
        if artifact.artifact_id in path_text or artifact.name.lower() in path_text
    ]


def _candidate_result_objects(payload: Any) -> list[Mapping[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, Mapping)]
    if not isinstance(payload, Mapping):
        return []
    # Result files often contain an outer metadata wrapper and a list/object
    # named results, benchmarks, or summary.  Prefer these to avoid treating
    # every nested metric object as a separate benchmark result.
    for key in ("results", "benchmarks", "benchmark_results", "summary", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            candidates = [item for item in value if isinstance(item, Mapping)]
            if candidates:
                return candidates
        if isinstance(value, Mapping):
            return [value]
    return [payload]


def _published_metric_value(
    flattened: Mapping[str, Any], canonical: str, aliases: tuple[str, ...]
) -> Any | None:
    paths = (*_PUBLISHED_PATH_ALIASES.get(canonical, ()), *aliases)
    value, path = lookup_flat_value(flattened, paths)
    if canonical in _CATEGORICAL_METRICS:
        return _text(value)
    if canonical == "gpu_count":
        direct = _number(value)
        if direct is not None:
            return direct
        prefill, _ = lookup_flat_value(flattened, ("num_prefill_gpu",))
        decode, _ = lookup_flat_value(flattened, ("num_decode_gpu",))
        prefill_count, decode_count = _number(prefill), _number(decode)
        if prefill_count is not None and decode_count is not None:
            return prefill_count + decode_count
        return None
    if canonical.endswith("_ms"):
        if path and "request_metrics.latency" in path:
            number = _number(value)
            return number * 1000.0 if number is not None else None
        # AIPerf direct aggregate fields carry their unit in a sibling key.
        if path:
            parent = path.rsplit(".", 1)[0]
            unit, _ = lookup_flat_value(flattened, (f"{parent}.unit",))
            if isinstance(unit, str) and unit.strip().lower() in {"s", "sec", "seconds"}:
                number = _number(value)
                return number * 1000.0 if number is not None else None
        return _duration_to_ms(value, path)
    return _number(value)


def _derive_published_token_total(
    flattened: Mapping[str, Any], canonical: str
) -> tuple[float | None, str | None]:
    """Derive profile-token totals only from documented aggregate components.

    InferenceX publishes successful request count and request-level token mean,
    but not necessarily an explicit total.  The product is an auditable
    aggregate reconstruction, not a replacement for unrelated server token
    counters that may include warmup or cache accounting.
    """

    metric_path = {
        "total_input_tokens": "request_metrics.tokens.input.mean",
        "total_output_tokens": "request_metrics.tokens.output_actual.mean",
    }.get(canonical)
    if metric_path is None:
        return None, None
    mean_value, resolved_mean_path = lookup_flat_value(flattened, (metric_path,))
    successful_value, resolved_successful_path = lookup_flat_value(
        flattened, ("num_requests_successful",)
    )
    mean, successful = _number(mean_value), _number(successful_value)
    if mean is None or successful is None:
        return None, None
    derivation = (
        f"derived from {resolved_mean_path} × {resolved_successful_path}; "
        "published mean is rounded"
    )
    return mean * successful, derivation


def _compare_metric(
    metric: str,
    raw: Any,
    published: Any,
    *,
    derivation: str | None = None,
) -> tuple[float | None, float | None, str]:
    if metric in _CATEGORICAL_METRICS:
        raw_text, published_text = _text(raw), _text(published)
        if raw_text is None or published_text is None:
            return None, None, "not_comparable"
        if _normalized_text(raw_text) == _normalized_text(published_text):
            return None, None, "pass"
        if metric == "target_model" and _target_model_alias_equivalent(raw_text, published_text):
            return None, None, "pass_alias_equivalent"
        return None, None, "mismatch"
    raw_number, published_number = _number(raw), _number(published)
    if raw_number is None or published_number is None:
        return None, None, "not_comparable"
    absolute = abs(raw_number - published_number)
    relative = (
        absolute / abs(published_number)
        if published_number != 0
        else (0.0 if absolute == 0 else None)
    )
    absolute_tolerance, relative_tolerance = _tolerances(
        metric, raw_number, published_number, derivation=derivation
    )
    passed = absolute <= (absolute_tolerance or 0.0) or (
        relative is not None and relative <= (relative_tolerance or 0.0)
    )
    return absolute, relative, "pass" if passed else "mismatch"


def _validation_note(
    metric: str,
    raw: Any,
    published: Any,
    status: str,
    *,
    derivation: str | None = None,
) -> str | None:
    if status == "not_comparable":
        return "Unknown: one or both values are unavailable in raw/profiled or published aggregate data."
    if status == "pass_alias_equivalent":
        return (
            "Evidence: literal target-model labels differ but are the documented "
            "GLM-5.2 FP8 alias pair (`GLM-5.2 FP8` and `zai-org/GLM-5.2-FP8`)."
        )
    if derivation:
        return f"Evidence: {derivation}; validation uses an explicit rounding tolerance."
    if metric in _CATEGORICAL_METRICS:
        return "Metadata comparison; raw context provenance must be checked separately from numeric reconstruction."
    if metric.startswith("per_gpu_"):
        return "Raw value divides reconstructed shared-system throughput by recorded GPU count."
    return None


def _tolerances(
    metric: str,
    raw: Any,
    published: Any,
    *,
    derivation: str | None = None,
) -> tuple[float | None, float | None]:
    if metric in _CATEGORICAL_METRICS:
        return None, None
    if metric.endswith("count") or metric.endswith("tokens") or metric == "gpu_count":
        if derivation and metric.endswith("tokens"):
            # Token means in the public aggregate are rounded, so a product
            # with request count can differ by a small fractional token.
            return 1.0, 0.0
        return 0.0, 0.0
    if metric.endswith("_ms"):
        return 1.0, 0.01
    if metric.endswith("_tps"):
        return 0.1, 0.02
    if metric == "duration_s":
        return 0.1, 0.02
    return 1e-9, 1e-9


def _first_text(series: Any) -> str | None:
    values = series.dropna()
    for value in values:
        text = _text(value)
        if text:
            return text
    return None


def _text(value: Any) -> str | None:
    if value is None or type(value).__name__ == "NAType":
        return None
    try:
        if bool(value != value):  # NaN / NaT without a pandas dependency.
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text or None


def _normalized_text(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())


def _target_model_alias_equivalent(raw: str, published: str) -> bool:
    """Recognize the single documented GLM-5.2 FP8 literal alias pair."""

    aliases = {_normalized_text(raw), _normalized_text(published)}
    return aliases == {"glm52fp8", "zaiorgglm52fp8"}


def _mean(series: Any) -> float | None:
    values = series.dropna()
    return float(values.mean()) if not values.empty else None


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in {float("inf"), float("-inf")}:
        return None
    return number


def _ensure_columns(frame: Any, columns: Sequence[str]) -> None:
    for column in columns:
        if column not in frame.columns:
            frame[column] = None
