"""Observed conversation-ID coverage and source-workload bias diagnostics."""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from typing import Any


def build_id_coverage_matrix(
    profiled_frame: Any,
    *,
    source_ids: Iterable[str] | None = None,
    concurrencies: Iterable[int] = range(1, 9),
) -> Any:
    """Create a root-ID × concurrency matrix of profiled request counts.

    Source IDs that were never observed are retained with zeroes.  H200 IDs
    unmatched to the source table are also retained rather than silently lost.
    """

    import pandas as pd

    concurrencies = list(concurrencies)
    expected_columns = [f"conc{value}" for value in concurrencies]
    source_set = {str(value) for value in (source_ids or []) if value is not None and str(value)}
    if profiled_frame.empty or "root_trace_id" not in profiled_frame.columns:
        result = pd.DataFrame({"root_trace_id": sorted(source_set)})
        for column in expected_columns:
            result[column] = 0
        return result

    frame = profiled_frame.copy()
    if "concurrency" not in frame.columns:
        frame["concurrency"] = None
    frame = frame.loc[frame["root_trace_id"].notna()].copy()
    frame["root_trace_id"] = frame["root_trace_id"].astype(str)
    frame["concurrency"] = pd.to_numeric(frame["concurrency"], errors="coerce")
    grouped = (
        frame.groupby(["root_trace_id", "concurrency"], dropna=False)
        .size()
        .rename("profiled_request_count")
        .reset_index()
    )
    observed_roots = set(grouped["root_trace_id"])
    all_roots = sorted(source_set | observed_roots)
    result = pd.DataFrame({"root_trace_id": all_roots})
    for concurrency in concurrencies:
        values = grouped.loc[
            grouped["concurrency"] == concurrency, ["root_trace_id", "profiled_request_count"]
        ]
        value_map = dict(
            zip(values["root_trace_id"], values["profiled_request_count"], strict=True)
        )
        result[f"conc{concurrency}"] = result["root_trace_id"].map(value_map).fillna(0).astype(int)
    return result


def build_coverage_summary(
    all_frame: Any,
    profiled_frame: Any,
    *,
    source_ids: Iterable[str] | None = None,
    concurrencies: Iterable[int] = range(1, 9),
) -> Any:
    """Summarize profiling, warmup, error, cancellation, and ID coverage by conc."""

    import pandas as pd

    concurrencies = list(concurrencies)
    source_set = {str(value) for value in (source_ids or []) if value is not None and str(value)}
    all_copy = all_frame.copy()
    profiled_copy = profiled_frame.copy()
    for frame in (all_copy, profiled_copy):
        _ensure_columns(
            frame,
            [
                "concurrency",
                "root_trace_id",
                "conversation_id",
                "session_num",
                "branch_type",
                "source_branch_type",
                "input_tokens",
                "output_tokens",
                "benchmark_phase",
                "error_present",
                "was_cancelled",
            ],
        )
        frame["concurrency"] = pd.to_numeric(frame["concurrency"], errors="coerce")
    rows: list[dict[str, Any]] = []
    all_present_concs = set(all_copy["concurrency"].dropna().astype(int))
    profile_present_concs = set(profiled_copy["concurrency"].dropna().astype(int))
    for concurrency in sorted(set(concurrencies) | all_present_concs | profile_present_concs):
        all_group = all_copy.loc[all_copy["concurrency"] == concurrency]
        profile_group = profiled_copy.loc[profiled_copy["concurrency"] == concurrency]
        roots = _nonnull_set(profile_group["root_trace_id"])
        branches = _nonnull_set(profile_group["conversation_id"])
        sessions = _nonnull_set(profile_group["session_num"])
        phase = all_group["benchmark_phase"].astype("string").str.strip().str.lower()
        replay_counts = _replay_branch_counts(profile_group["branch_type"])
        source_origin_counts = _source_origin_counts(profile_group["source_branch_type"])
        errors = _truthy_count(all_group["error_present"])
        cancellations = _truthy_count(all_group["was_cancelled"])
        matched = roots.intersection(source_set) if source_set else set()
        row = {
            "concurrency": concurrency,
            "all_request_count": int(len(all_group)),
            "profiled_request_count": int(len(profile_group)),
            "warmup_count": int(phase.isin(["warmup", "warming", "warm_up"]).sum()),
            "profiling_phase_count": int(phase.isin(["profiling", "profile"]).sum()),
            "error_count": errors,
            "cancellation_count": cancellations,
            "distinct_root_ids": len(roots),
            "matched_root_ids": len(matched) if source_set else None,
            "unmatched_root_ids": len(roots - source_set) if source_set else None,
            "root_match_rate": len(matched) / len(roots) if source_set and roots else None,
            "distinct_conversation_branches": len(branches),
            "distinct_session_num": len(sessions),
            # Legacy names refer to the H200 replay conversation-ID suffix
            # taxonomy. They are deliberately retained for compatibility, but
            # must not be read as source nested-agent counts: direct ``::fa``
            # and ``::aux`` suffixes can map to a source-root request.
            "root_request_count": replay_counts["replay_root_request_count"],
            "subagent_request_count": replay_counts["replay_nonroot_branch_request_count"],
            "unknown_branch_request_count": replay_counts[
                "replay_unknown_branch_request_count"
            ],
            **replay_counts,
            **source_origin_counts,
            "total_input_tokens": _numeric_sum(profile_group["input_tokens"]),
            "total_output_tokens": _numeric_sum(profile_group["output_tokens"]),
            "source_trace_count": len(source_set) if source_set else None,
            "never_observed_source_ids": len(source_set - matched) if source_set else None,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def build_coverage_bias_table(
    source_summary: Any,
    profiled_frame: Any,
    *,
    concurrencies: Iterable[int] = range(1, 9),
) -> Any:
    """Compare source-trace shape for observed versus unobserved IDs.

    Values are source-workload characteristics, not target-H200 performance.
    A row is emitted for every requested concurrency even when no profile data
    exists, making missing artifact coverage visible in the final report.
    """

    import pandas as pd

    columns = [
        "concurrency",
        "observation_group",
        "source_trace_count",
        "source_request_count_total_mean",
        "source_request_count_total_median",
        "source_recorded_span_s_mean",
        "source_recorded_span_s_median",
        "source_total_input_tokens_mean",
        "source_total_input_tokens_median",
        "source_total_output_tokens_mean",
        "source_total_output_tokens_median",
        "source_subagent_count_mean",
        "source_subagent_count_median",
        "source_max_input_tokens_mean",
        "source_max_input_tokens_median",
    ]
    if source_summary.empty or "root_trace_id" not in source_summary.columns:
        return pd.DataFrame(columns=columns)
    summary = source_summary.copy()
    summary["root_trace_id"] = summary["root_trace_id"].astype(str)
    frame = profiled_frame.copy()
    _ensure_columns(frame, ["concurrency", "root_trace_id"])
    frame["concurrency"] = pd.to_numeric(frame["concurrency"], errors="coerce")
    rows: list[dict[str, Any]] = []
    shape_columns = [
        "source_request_count_total",
        "source_recorded_span_s",
        "source_total_input_tokens",
        "source_total_output_tokens",
        "source_subagent_count",
        "source_max_input_tokens",
    ]
    for concurrency in concurrencies:
        observed = _nonnull_set(frame.loc[frame["concurrency"] == concurrency, "root_trace_id"])
        for group_name, mask in (
            ("observed", summary["root_trace_id"].isin(observed)),
            ("never_observed", ~summary["root_trace_id"].isin(observed)),
        ):
            group = summary.loc[mask]
            row: dict[str, Any] = {
                "concurrency": concurrency,
                "observation_group": group_name,
                "source_trace_count": int(len(group)),
            }
            for field in shape_columns:
                numeric = (
                    pd.to_numeric(group[field], errors="coerce")
                    if field in group
                    else pd.Series(dtype=float)
                )
                row[f"{field}_mean"] = float(numeric.mean()) if numeric.notna().any() else None
                row[f"{field}_median"] = float(numeric.median()) if numeric.notna().any() else None
            rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def observation_probability_by_source_shape(
    source_summary: Any,
    profiled_frame: Any,
    *,
    concurrencies: Iterable[int] = range(1, 9),
) -> Any:
    """Return source IDs with per-concurrency presence flags for plotting."""

    import pandas as pd

    if source_summary.empty or "root_trace_id" not in source_summary.columns:
        return pd.DataFrame(columns=["root_trace_id", "concurrency", "observed"])
    frame = profiled_frame.copy()
    _ensure_columns(frame, ["concurrency", "root_trace_id"])
    frame["concurrency"] = pd.to_numeric(frame["concurrency"], errors="coerce")
    rows: list[Any] = []
    for concurrency in concurrencies:
        observed = _nonnull_set(frame.loc[frame["concurrency"] == concurrency, "root_trace_id"])
        part = source_summary.copy()
        part["concurrency"] = concurrency
        part["observed"] = part["root_trace_id"].astype(str).isin(observed)
        rows.append(part)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def build_coverage_model_composition(
    source_summary: Any,
    profiled_frame: Any,
    *,
    concurrencies: Iterable[int] = range(1, 9),
) -> Any:
    """Compare source workload-model label composition by observed coverage.

    These labels describe the Claude Code collection workload only. They are
    not interpreted as target GLM model variants or H200 model performance.
    """

    import pandas as pd

    columns = [
        "concurrency",
        "observation_group",
        "source_model",
        "source_trace_count_with_model",
        "source_trace_count_in_group",
        "source_model_trace_share",
    ]
    if source_summary.empty or "root_trace_id" not in source_summary.columns:
        return pd.DataFrame(columns=columns)
    summary = source_summary.copy()
    summary["root_trace_id"] = summary["root_trace_id"].astype(str)
    model_column = "source_models" if "source_models" in summary else None
    if model_column is None:
        return pd.DataFrame(columns=columns)
    frame = profiled_frame.copy()
    _ensure_columns(frame, ["concurrency", "root_trace_id"])
    frame["concurrency"] = pd.to_numeric(frame["concurrency"], errors="coerce")
    rows: list[dict[str, Any]] = []
    for concurrency in concurrencies:
        observed = _nonnull_set(frame.loc[frame["concurrency"] == concurrency, "root_trace_id"])
        for group_name, group in (
            ("observed", summary.loc[summary["root_trace_id"].isin(observed)]),
            ("never_observed", summary.loc[~summary["root_trace_id"].isin(observed)]),
        ):
            denominator = int(len(group))
            model_counts: dict[str, int] = {}
            for value in group[model_column]:
                for model in _parse_source_models(value):
                    model_counts[model] = model_counts.get(model, 0) + 1
            if not model_counts:
                rows.append(
                    {
                        "concurrency": concurrency,
                        "observation_group": group_name,
                        "source_model": "<missing_or_unparsed>",
                        "source_trace_count_with_model": 0,
                        "source_trace_count_in_group": denominator,
                        "source_model_trace_share": None,
                    }
                )
            for model, count in sorted(model_counts.items()):
                rows.append(
                    {
                        "concurrency": concurrency,
                        "observation_group": group_name,
                        "source_model": model,
                        "source_trace_count_with_model": count,
                        "source_trace_count_in_group": denominator,
                        "source_model_trace_share": count / denominator if denominator else None,
                    }
                )
    return pd.DataFrame(rows, columns=columns)


def _ensure_columns(frame: Any, columns: Sequence[str]) -> None:
    for column in columns:
        if column not in frame.columns:
            frame[column] = None


def _nonnull_set(series: Any) -> set[str]:
    return {str(value) for value in series.dropna() if str(value).strip()}


def _numeric_sum(series: Any) -> float:
    import pandas as pd

    return float(pd.to_numeric(series, errors="coerce").fillna(0).sum())


def _truthy_count(series: Any) -> int:
    normalized = series.astype("string").str.strip().str.lower()
    return int(normalized.isin(["true", "1", "yes", "y"]).sum())


def _replay_branch_counts(series: Any) -> dict[str, int]:
    """Count H200 replay-ID suffix categories, not source-agent origin."""

    branch_type = series.astype("string").str.strip().str.lower().fillna("unknown")
    known_nonroot = branch_type.isin(_KNOWN_SUBAGENT_BRANCH_TYPES)
    return {
        "replay_root_request_count": int((branch_type == "root").sum()),
        "replay_nonroot_branch_request_count": int(known_nonroot.sum()),
        "replay_unknown_branch_request_count": int(
            (~branch_type.eq("root") & ~known_nonroot).sum()
        ),
    }


def _source_origin_counts(series: Any) -> dict[str, int]:
    """Count source-flattening origin after loader metadata mapping.

    ``source_branch_type`` is independent of the H200 replay suffix.  In the
    acquired artifacts, for example, replay ``fanout`` records map to source
    root requests.  Missing or non-canonical values are reported as unknown
    instead of being silently folded into either source class.
    """

    branch_type = series.astype("string").str.strip().str.lower().fillna("unknown")
    return {
        "source_origin_root_request_count": int((branch_type == "root").sum()),
        "source_origin_subagent_request_count": int((branch_type == "subagent").sum()),
        "source_origin_unknown_branch_request_count": int(
            (~branch_type.isin(["root", "subagent"])).sum()
        ),
    }


_KNOWN_SUBAGENT_BRANCH_TYPES = {
    "subagent",
    "subagent_main",
    "fanout",
    "auxiliary",
    "worker_group",
}


def _parse_source_models(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list | tuple | set):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
        return [value] if value.strip() else []
    return [str(value)]
