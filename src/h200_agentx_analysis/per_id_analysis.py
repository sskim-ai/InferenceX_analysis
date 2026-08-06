"""Opaque session-group and root-ID-level H200 request aggregation."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .metrics import percentile, token_weighted_itl_ms, wall_clock_span


def summarize_replay_instances(profiled_frame: Any) -> Any:
    """Aggregate request records by opaque session-number groups.

    The primary key is ``(concurrency, root_trace_id, session_num)``.  This is
    retained as a *candidate* replay-instance key for compatibility with the
    benchmark schema, not proof that it identifies an independent replay.  In
    particular, when every profiling record has a unique session number this
    table does not de-correlate repeated records.  See
    :func:`summarize_session_num_grouping` for an auditable diagnostic.
    """

    import pandas as pd

    columns = _replay_columns()
    if profiled_frame.empty:
        return pd.DataFrame(columns=columns)
    frame = profiled_frame.copy()
    _ensure_columns(
        frame,
        [
            "concurrency",
            "root_trace_id",
            "session_num",
            "conversation_id",
            "branch_type",
            "source_branch_type",
            "input_tokens",
            "output_tokens",
            "ttft_ms",
            "itl_ms",
            "e2e_ms",
            "request_start_ns",
            "request_end_ns",
            "error_present",
            "was_cancelled",
        ],
    )
    frame = frame.loc[frame["root_trace_id"].notna()].copy()
    rows: list[dict[str, Any]] = []
    for (concurrency, root_trace_id, session_num), group in frame.groupby(
        ["concurrency", "root_trace_id", "session_num"], dropna=False
    ):
        rows.append(
            _summarize_group(
                group,
                {
                    "concurrency": concurrency,
                    "root_trace_id": root_trace_id,
                    "session_num": session_num,
                    "distinct_branch_count": group["conversation_id"].nunique(dropna=True),
                    "replay_instance_identity_status": "unvalidated_session_num_group",
                    **_branch_counts(group),
                },
            )
        )
    return pd.DataFrame(rows, columns=columns)


def summarize_id_concurrency(
    profiled_frame: Any,
    *,
    source_summary: Any | None = None,
    all_frame: Any | None = None,
    min_request_count: int = 3,
) -> Any:
    """Aggregate profile records by root trace ID and concurrency.

    This is the table used for cross-concurrency ratios.  It retains raw
    profiled request counts and replay count beside every latency statistic so
    sparse IDs can be flagged rather than over-interpreted.
    """

    import pandas as pd

    columns = _id_summary_columns()
    if profiled_frame.empty:
        return pd.DataFrame(columns=columns)
    frame = profiled_frame.copy()
    _ensure_columns(
        frame,
        [
            "concurrency",
            "root_trace_id",
            "session_num",
            "conversation_id",
            "branch_type",
            "source_branch_type",
            "input_tokens",
            "output_tokens",
            "ttft_ms",
            "itl_ms",
            "e2e_ms",
            "request_start_ns",
            "request_end_ns",
            "error_present",
            "was_cancelled",
        ],
    )
    frame = frame.loc[frame["root_trace_id"].notna()].copy()
    rows: list[dict[str, Any]] = []
    for (concurrency, root_trace_id), group in frame.groupby(
        ["concurrency", "root_trace_id"], dropna=False
    ):
        base = {
            "concurrency": concurrency,
            "root_trace_id": root_trace_id,
            # Legacy ``distinct_replay_instances`` is an opaque session-group
            # count.  It must not be interpreted as independent replay count
            # until the loader's session semantics are directly established.
            "distinct_replay_instances": _distinct_replay_count(group),
            "session_num_group_count": _distinct_replay_count(group),
            "session_num_unique_row_rate": _session_num_unique_row_rate(group),
            "replay_instance_identity_status": "unvalidated_session_num_group",
            "distinct_branch_count": group["conversation_id"].nunique(dropna=True),
            **_branch_counts(group),
            "error_count": _truthy_count(group["error_present"]),
            "cancellation_count": _truthy_count(group["was_cancelled"]),
        }
        row = _summarize_group(group, base)
        row["sample_quality_flag"] = _sample_quality_flag(
            row["profiled_request_count"], row["session_num_group_count"], min_request_count
        )
        rows.append(row)
    result = pd.DataFrame(rows)
    if all_frame is not None and not all_frame.empty:
        status_counts = _status_counts_by_id(all_frame)
        if not status_counts.empty:
            result = result.merge(
                status_counts,
                on=["concurrency", "root_trace_id"],
                how="left",
                suffixes=("", "_all"),
            )
            for field in ("error_count", "cancellation_count"):
                source_field = f"{field}_all"
                if source_field in result:
                    result[field] = result[source_field].fillna(result[field]).fillna(0).astype(int)
                    result = result.drop(columns=[source_field])
    if (
        source_summary is not None
        and not source_summary.empty
        and "root_trace_id" in source_summary.columns
    ):
        fields = ["root_trace_id"]
        for field in (
            "source_models",
            "source_request_count_total",
            "source_subagent_count",
            "source_total_input_tokens",
            "source_total_output_tokens",
            "source_recorded_span_s",
            "source_max_input_tokens",
            "source_max_output_tokens",
        ):
            if field in source_summary.columns:
                fields.append(field)
        result = result.merge(
            source_summary[fields], on="root_trace_id", how="left", validate="many_to_one"
        )
    # Guarantee stable columns even if the source table was unavailable.
    for column in columns:
        if column not in result.columns:
            result[column] = None
    return result[columns]


def summarize_weightings(profiled_frame: Any) -> Any:
    """Report request-, root-ID-, session-group-, and token-weighted statistics.

    These figures describe different estimands and must never be conflated in a
    report.  ``session_num`` group weighting is explicitly unvalidated as a
    replay-instance estimator; root-ID weighting is the conservative grouping
    used for repeated-ID interpretation.
    """

    import pandas as pd

    output_columns = [
        "weighting",
        "sample_count",
        "median_ttft_ms",
        "median_itl_ms",
        "median_e2e_ms",
    ]
    if profiled_frame.empty:
        return pd.DataFrame(columns=output_columns)
    frame = profiled_frame.copy()
    _ensure_columns(
        frame,
        [
            "root_trace_id",
            "concurrency",
            "session_num",
            "ttft_ms",
            "itl_ms",
            "e2e_ms",
            "output_tokens",
        ],
    )
    rows = [
        {
            "weighting": "request_weighted",
            "sample_count": int(len(frame)),
            "median_ttft_ms": percentile(frame["ttft_ms"], 0.5),
            "median_itl_ms": percentile(frame["itl_ms"], 0.5),
            "median_e2e_ms": percentile(frame["e2e_ms"], 0.5),
        }
    ]
    id_rows = []
    for _, group in frame.groupby(["concurrency", "root_trace_id"], dropna=False):
        id_rows.append(
            {
                "ttft_ms": percentile(group["ttft_ms"], 0.5),
                "itl_ms": percentile(group["itl_ms"], 0.5),
                "e2e_ms": percentile(group["e2e_ms"], 0.5),
            }
        )
    replay_rows = []
    for _, group in frame.groupby(["concurrency", "root_trace_id", "session_num"], dropna=False):
        replay_rows.append(
            {
                "ttft_ms": percentile(group["ttft_ms"], 0.5),
                "itl_ms": percentile(group["itl_ms"], 0.5),
                "e2e_ms": percentile(group["e2e_ms"], 0.5),
            }
        )
    for name, values in (
        ("root_id_weighted", id_rows),
        ("session_num_group_weighted_unvalidated", replay_rows),
    ):
        values_frame = pd.DataFrame(values)
        rows.append(
            {
                "weighting": name,
                "sample_count": int(len(values_frame)),
                "median_ttft_ms": percentile(values_frame["ttft_ms"], 0.5)
                if not values_frame.empty
                else None,
                "median_itl_ms": percentile(values_frame["itl_ms"], 0.5)
                if not values_frame.empty
                else None,
                "median_e2e_ms": percentile(values_frame["e2e_ms"], 0.5)
                if not values_frame.empty
                else None,
            }
        )
    # Token weighting is meaningful for ITL only (weights = output intervals).
    rows.append(
        {
            "weighting": "output_token_weighted_itl",
            "sample_count": int((frame["output_tokens"] > 1).sum()),
            "median_ttft_ms": None,
            "median_itl_ms": token_weighted_itl_ms(frame),
            "median_e2e_ms": None,
        }
    )
    return pd.DataFrame(rows, columns=output_columns)


def summarize_branch_types(profiled_frame: Any, *, all_frame: Any | None = None) -> Any:
    """Compare H200 replay conversation-ID suffix categories by concurrency.

    This is intentionally separate from :func:`summarize_source_branch_origins`.
    A replay ``fanout`` or direct ``auxiliary`` suffix may map to a source-root
    request through the loader metadata.
    """

    import pandas as pd

    columns = [
        "concurrency",
        "branch_type",
        "branch_taxonomy",
        "profiled_request_count",
        "distinct_root_ids",
        "total_input_tokens",
        "total_output_tokens",
        "median_input_tokens",
        "median_output_tokens",
        "median_ttft_ms",
        "p90_ttft_ms",
        "median_itl_ms",
        "p90_itl_ms",
        "median_e2e_ms",
        "p90_e2e_ms",
        "token_weighted_itl_ms",
        "error_count",
        "cancellation_count",
    ]
    if profiled_frame.empty:
        return pd.DataFrame(columns=columns)
    frame = profiled_frame.copy()
    _ensure_columns(
        frame, ["concurrency", "branch_type", "root_trace_id", "error_present", "was_cancelled"]
    )
    frame["branch_type"] = frame["branch_type"].fillna("unknown")
    rows: list[dict[str, Any]] = []
    for (concurrency, branch_type), group in frame.groupby(
        ["concurrency", "branch_type"], dropna=False
    ):
        row = _summarize_group(
            group,
            {
                "concurrency": concurrency,
                "branch_type": branch_type,
                "branch_taxonomy": "h200_replay_conversation_suffix",
            },
        )
        row["distinct_root_ids"] = group["root_trace_id"].nunique(dropna=True)
        row["error_count"] = _truthy_count(group["error_present"])
        row["cancellation_count"] = _truthy_count(group["was_cancelled"])
        rows.append(row)
    result = pd.DataFrame(rows)
    if all_frame is not None and not all_frame.empty:
        status_counts = _status_counts_by_branch(all_frame)
        if not status_counts.empty:
            result = result.merge(
                status_counts,
                on=["concurrency", "branch_type"],
                how="left",
                suffixes=("", "_all"),
            )
            for field in ("error_count", "cancellation_count"):
                source_field = f"{field}_all"
                if source_field in result:
                    result[field] = result[source_field].fillna(result[field]).fillna(0).astype(int)
                    result = result.drop(columns=[source_field])
    for column in columns:
        if column not in result:
            result[column] = None
    return result[columns]


def summarize_source_branch_origins(profiled_frame: Any, *, all_frame: Any | None = None) -> Any:
    """Compare source root versus nested-subagent origin by concurrency.

    ``source_branch_type`` comes from the authoritative loader metadata/source
    join, rather than from the H200 replay conversation-ID suffix.  Values
    outside the source parser's ``root``/``subagent`` vocabulary are retained
    as ``unknown``.  This makes the source-origin table appropriate for the
    root-agent/subagent workload comparison while ``root_subagent_summary``
    remains a replay-category table for backwards compatibility.
    """

    import pandas as pd

    columns = [
        "concurrency",
        "source_origin_branch_type",
        "branch_taxonomy",
        "profiled_request_count",
        "distinct_root_ids",
        "total_input_tokens",
        "total_output_tokens",
        "median_input_tokens",
        "median_output_tokens",
        "median_ttft_ms",
        "p90_ttft_ms",
        "median_itl_ms",
        "p90_itl_ms",
        "median_e2e_ms",
        "p90_e2e_ms",
        "token_weighted_itl_ms",
        "error_count",
        "cancellation_count",
    ]
    if profiled_frame.empty:
        return pd.DataFrame(columns=columns)
    frame = profiled_frame.copy()
    _ensure_columns(
        frame,
        ["concurrency", "source_branch_type", "root_trace_id", "error_present", "was_cancelled"],
    )
    frame["source_origin_branch_type"] = _normalized_source_branch_type(
        frame["source_branch_type"]
    )
    rows: list[dict[str, Any]] = []
    for (concurrency, branch_type), group in frame.groupby(
        ["concurrency", "source_origin_branch_type"], dropna=False
    ):
        row = _summarize_group(
            group,
            {
                "concurrency": concurrency,
                "source_origin_branch_type": branch_type,
                "branch_taxonomy": "source_trace_flattening_origin",
            },
        )
        row["distinct_root_ids"] = group["root_trace_id"].nunique(dropna=True)
        row["error_count"] = _truthy_count(group["error_present"])
        row["cancellation_count"] = _truthy_count(group["was_cancelled"])
        rows.append(row)
    result = pd.DataFrame(rows)
    if all_frame is not None and not all_frame.empty:
        status_counts = _status_counts_by_source_origin(all_frame)
        if not status_counts.empty:
            result = result.merge(
                status_counts,
                on=["concurrency", "source_origin_branch_type"],
                how="left",
                suffixes=("", "_all"),
            )
            for field in ("error_count", "cancellation_count"):
                source_field = f"{field}_all"
                if source_field in result:
                    result[field] = result[source_field].fillna(result[field]).fillna(0).astype(int)
                    result = result.drop(columns=[source_field])
    for column in columns:
        if column not in result:
            result[column] = None
    return result[columns]


def summarize_session_num_grouping(profiled_frame: Any) -> Any:
    """Diagnose whether ``session_num`` can support replay-instance grouping.

    The benchmark records do not document session semantics in the profile
    export.  A one-to-one session-number-to-row pattern is therefore reported
    as an **Unknown** replay identity, not as evidence of independent replay
    instances.  Root trace ID remains the cluster unit for paired bootstrap
    summaries.
    """

    import pandas as pd

    columns = [
        "scope",
        "concurrency",
        "profiled_request_count",
        "non_null_session_num_count",
        "distinct_session_num",
        "distinct_concurrency_session_num",
        "duplicate_non_null_session_num_row_count",
        "duplicate_concurrency_session_num_row_count",
        "session_num_unique_row_rate",
        "session_num_uniqueness_key",
        "session_num_semantics",
        "interpretation",
        "replay_instance_identity_status",
        "cross_concurrency_cluster_unit",
        "root_trace_id_cluster_count",
    ]
    if profiled_frame.empty:
        return pd.DataFrame(columns=columns)
    frame = profiled_frame.copy()
    _ensure_columns(frame, ["concurrency", "session_num", "root_trace_id"])
    rows: list[dict[str, Any]] = []
    groups: list[tuple[str, Any, Any]] = [("all_profiled_rows", None, frame)]
    groups.extend(("per_concurrency", concurrency, group) for concurrency, group in frame.groupby("concurrency", dropna=False))
    for scope, concurrency, group in groups:
        values = group["session_num"]
        non_null = values.dropna()
        count = int(len(group))
        raw_distinct = int(non_null.nunique(dropna=True))
        non_null_count = int(len(non_null))
        # The numeric session counter is scoped to a concurrency run. For the
        # all-rows diagnostic, assess uniqueness by the actual observed pair
        # rather than claiming a reset counter is a global replay identifier.
        keyed = group.loc[group["session_num"].notna(), ["concurrency", "session_num"]]
        scoped_distinct = int(len(keyed.drop_duplicates()))
        semantics = (
            "Unknown: session_num is unique per profiling row within observed "
            "concurrencies, but the profile export does not establish it as a "
            "replay-instance identifier."
        )
        rows.append(
            {
                "scope": scope,
                "concurrency": concurrency,
                "profiled_request_count": count,
                "non_null_session_num_count": non_null_count,
                "distinct_session_num": raw_distinct,
                "distinct_concurrency_session_num": scoped_distinct,
                "duplicate_non_null_session_num_row_count": max(non_null_count - raw_distinct, 0),
                "duplicate_concurrency_session_num_row_count": max(
                    non_null_count - scoped_distinct, 0
                ),
                "session_num_unique_row_rate": (
                    scoped_distinct / non_null_count if non_null_count else None
                ),
                "session_num_uniqueness_key": "(concurrency, session_num)",
                "session_num_semantics": semantics,
                # Compatibility alias for report readers; semantics are
                # intentionally explicit rather than a boolean replay claim.
                "interpretation": semantics,
                "replay_instance_identity_status": "unvalidated_session_num_group",
                "cross_concurrency_cluster_unit": "root_trace_id",
                "root_trace_id_cluster_count": int(group["root_trace_id"].nunique(dropna=True)),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def top_ids_by_workload(id_summary: Any, *, limit: int = 20) -> Any:
    """Rank ID/concurrency observations by recorded target replay workload."""

    import pandas as pd

    if id_summary.empty:
        return pd.DataFrame(columns=list(id_summary.columns) + ["rank_metric", "rank"])
    metrics = [
        "total_input_tokens",
        "total_output_tokens",
        "replay_nonroot_branch_request_count",
    ]
    parts = []
    for metric in metrics:
        if metric not in id_summary:
            continue
        part = (
            id_summary.sort_values(metric, ascending=False, na_position="last").head(limit).copy()
        )
        part["rank_metric"] = metric
        part["rank"] = range(1, len(part) + 1)
        parts.append(part)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def top_ids_by_latency(id_summary: Any, *, limit: int = 20) -> Any:
    """Rank ID/concurrency observations by latency burden, retaining sample sizes."""

    import pandas as pd

    if id_summary.empty:
        return pd.DataFrame(columns=list(id_summary.columns) + ["rank_metric", "rank"])
    metrics = [
        "median_ttft_ms",
        "p90_ttft_ms",
        "median_e2e_ms",
        "total_h200_wall_time_s",
        "wall_clock_output_rate",
    ]
    parts = []
    for metric in metrics:
        if metric not in id_summary:
            continue
        ascending = metric == "wall_clock_output_rate"
        part = (
            id_summary.sort_values(metric, ascending=ascending, na_position="last")
            .head(limit)
            .copy()
        )
        part["rank_metric"] = metric
        part["rank"] = range(1, len(part) + 1)
        parts.append(part)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def _summarize_group(group: Any, base: dict[str, Any]) -> dict[str, Any]:
    import pandas as pd

    # Public grouping helpers are also used with small fixtures and partial
    # schemas. Missing metrics represent unavailable measurements, not a
    # parser error, so retain the group with null summary values.
    group = group.copy()
    _ensure_columns(
        group,
        [
            "input_tokens",
            "output_tokens",
            "ttft_ms",
            "itl_ms",
            "e2e_ms",
            "request_start_ns",
            "request_end_ns",
        ],
    )
    input_tokens = pd.to_numeric(group["input_tokens"], errors="coerce")
    output_tokens = pd.to_numeric(group["output_tokens"], errors="coerce")
    e2e = pd.to_numeric(group["e2e_ms"], errors="coerce")
    span, wall_rate = wall_clock_span(group)
    row = dict(base)
    row.update(
        {
            "profiled_request_count": int(len(group)),
            "total_input_tokens": float(input_tokens.fillna(0).sum()),
            "total_output_tokens": float(output_tokens.fillna(0).sum()),
            "median_input_tokens": percentile(input_tokens, 0.5),
            "p90_input_tokens": percentile(input_tokens, 0.9),
            "median_output_tokens": percentile(output_tokens, 0.5),
            "median_ttft_ms": percentile(group["ttft_ms"], 0.5),
            "p75_ttft_ms": percentile(group["ttft_ms"], 0.75),
            "p90_ttft_ms": percentile(group["ttft_ms"], 0.9),
            "p95_ttft_ms": percentile(group["ttft_ms"], 0.95),
            "median_itl_ms": percentile(group["itl_ms"], 0.5),
            "p90_itl_ms": percentile(group["itl_ms"], 0.9),
            "median_e2e_ms": percentile(e2e, 0.5),
            "p90_e2e_ms": percentile(e2e, 0.9),
            "median_observed_itl_implied_tps": percentile(
                group["observed_itl_implied_tps"]
                if "observed_itl_implied_tps" in group
                else pd.Series(dtype=float),
                0.5,
            ),
            "token_weighted_itl_ms": token_weighted_itl_ms(group),
            "median_post_ttft_tps": percentile(
                group["post_ttft_tps"] if "post_ttft_tps" in group else pd.Series(dtype=float), 0.5
            ),
            "wall_span_s": span,
            "wall_clock_output_rate": wall_rate,
            "total_h200_wall_time_s": float(e2e.clip(lower=0).fillna(0).sum() / 1000.0),
        }
    )
    return row


def _sample_quality_flag(request_count: int, session_group_count: int, min_request_count: int) -> str:
    flags: list[str] = []
    if request_count < min_request_count:
        flags.append("low_request_count")
    if session_group_count < 1:
        flags.append("missing_session_num_group")
    elif session_group_count == 1:
        flags.append("single_session_num_group_unvalidated")
    if request_count > 0 and session_group_count == request_count:
        flags.append("session_num_unique_per_profiled_row")
    return ";".join(flags) if flags else "ok"


def _branch_counts(group: Any) -> dict[str, int]:
    branch_type = group["branch_type"].astype("string").str.strip().str.lower().fillna("unknown")
    known_subagent = branch_type.isin(_KNOWN_SUBAGENT_BRANCH_TYPES)
    source_branch_type = _normalized_source_branch_type(group["source_branch_type"])
    replay_root = int((branch_type == "root").sum())
    replay_nonroot = int(known_subagent.sum())
    replay_unknown = int((~branch_type.eq("root") & ~known_subagent).sum())
    return {
        # Legacy names have H200 replay-suffix semantics. Explicit aliases
        # below prevent them from being mistaken for source nested agents.
        "root_request_count": replay_root,
        "subagent_request_count": replay_nonroot,
        "unknown_branch_request_count": replay_unknown,
        "replay_root_request_count": replay_root,
        "replay_nonroot_branch_request_count": replay_nonroot,
        "replay_unknown_branch_request_count": replay_unknown,
        "source_origin_root_request_count": int((source_branch_type == "root").sum()),
        "source_origin_subagent_request_count": int((source_branch_type == "subagent").sum()),
        "source_origin_unknown_branch_request_count": int((source_branch_type == "unknown").sum()),
    }


def _distinct_replay_count(group: Any) -> int:
    # Missing session metadata is one opaque session group for aggregation; it
    # is not a claim that all rows are independent or one replay instance.
    values = group["session_num"]
    count = values.nunique(dropna=True)
    return int(count + int(values.isna().any()))


def _session_num_unique_row_rate(group: Any) -> float | None:
    values = group["session_num"].dropna()
    if values.empty:
        return None
    return float(values.nunique(dropna=True) / len(values))


def _truthy_count(series: Any) -> int:
    normalized = series.astype("string").str.strip().str.lower()
    return int(normalized.isin(["true", "1", "yes", "y"]).sum())


def _status_counts_by_id(frame: Any) -> Any:
    import pandas as pd

    copy = frame.copy()
    _ensure_columns(copy, ["concurrency", "root_trace_id", "error_present", "was_cancelled"])
    copy = copy.loc[copy["root_trace_id"].notna()].copy()
    rows: list[dict[str, Any]] = []
    for (concurrency, root_trace_id), group in copy.groupby(
        ["concurrency", "root_trace_id"], dropna=False
    ):
        rows.append(
            {
                "concurrency": concurrency,
                "root_trace_id": root_trace_id,
                "error_count": _truthy_count(group["error_present"]),
                "cancellation_count": _truthy_count(group["was_cancelled"]),
            }
        )
    return pd.DataFrame(rows)


def _status_counts_by_branch(frame: Any) -> Any:
    import pandas as pd

    copy = frame.copy()
    _ensure_columns(copy, ["concurrency", "branch_type", "error_present", "was_cancelled"])
    copy["branch_type"] = copy["branch_type"].fillna("unknown")
    rows: list[dict[str, Any]] = []
    for (concurrency, branch_type), group in copy.groupby(
        ["concurrency", "branch_type"], dropna=False
    ):
        rows.append(
            {
                "concurrency": concurrency,
                "branch_type": branch_type,
                "error_count": _truthy_count(group["error_present"]),
                "cancellation_count": _truthy_count(group["was_cancelled"]),
            }
        )
    return pd.DataFrame(rows)


def _status_counts_by_source_origin(frame: Any) -> Any:
    import pandas as pd

    copy = frame.copy()
    _ensure_columns(copy, ["concurrency", "source_branch_type", "error_present", "was_cancelled"])
    copy["source_origin_branch_type"] = _normalized_source_branch_type(copy["source_branch_type"])
    rows: list[dict[str, Any]] = []
    for (concurrency, branch_type), group in copy.groupby(
        ["concurrency", "source_origin_branch_type"], dropna=False
    ):
        rows.append(
            {
                "concurrency": concurrency,
                "source_origin_branch_type": branch_type,
                "error_count": _truthy_count(group["error_present"]),
                "cancellation_count": _truthy_count(group["was_cancelled"]),
            }
        )
    return pd.DataFrame(rows)


def _normalized_source_branch_type(series: Any) -> Any:
    """Map source-flattening labels to the compact root/subagent vocabulary."""

    normalized = series.astype("string").str.strip().str.lower()
    return normalized.where(normalized.isin(["root", "subagent"]), "unknown").fillna("unknown")


def _ensure_columns(frame: Any, columns: Sequence[str]) -> None:
    for column in columns:
        if column not in frame.columns:
            frame[column] = None


def _replay_columns() -> list[str]:
    return [
        "concurrency",
        "root_trace_id",
        "session_num",
        "replay_instance_identity_status",
        "profiled_request_count",
        "distinct_branch_count",
        # Legacy replay-suffix count names.
        "root_request_count",
        "subagent_request_count",
        "unknown_branch_request_count",
        # Explicit H200 replay-suffix taxonomy counts.
        "replay_root_request_count",
        "replay_nonroot_branch_request_count",
        "replay_unknown_branch_request_count",
        # Source flattening origin counts (independent of replay suffix).
        "source_origin_root_request_count",
        "source_origin_subagent_request_count",
        "source_origin_unknown_branch_request_count",
        "total_input_tokens",
        "total_output_tokens",
        "median_input_tokens",
        "p90_input_tokens",
        "median_output_tokens",
        "median_ttft_ms",
        "p75_ttft_ms",
        "p90_ttft_ms",
        "p95_ttft_ms",
        "median_itl_ms",
        "p90_itl_ms",
        "median_e2e_ms",
        "p90_e2e_ms",
        "median_observed_itl_implied_tps",
        "token_weighted_itl_ms",
        "median_post_ttft_tps",
        "wall_span_s",
        "wall_clock_output_rate",
        "total_h200_wall_time_s",
    ]


def _id_summary_columns() -> list[str]:
    return [
        "root_trace_id",
        "concurrency",
        "source_models",
        # ``distinct_replay_instances`` is a legacy alias for opaque
        # session-number groups; see status field and diagnostics table.
        "distinct_replay_instances",
        "session_num_group_count",
        "session_num_unique_row_rate",
        "replay_instance_identity_status",
        "profiled_request_count",
        "root_request_count",
        "subagent_request_count",
        "unknown_branch_request_count",
        "replay_root_request_count",
        "replay_nonroot_branch_request_count",
        "replay_unknown_branch_request_count",
        "source_origin_root_request_count",
        "source_origin_subagent_request_count",
        "source_origin_unknown_branch_request_count",
        "distinct_branch_count",
        "total_input_tokens",
        "total_output_tokens",
        "median_input_tokens",
        "p90_input_tokens",
        "median_output_tokens",
        "median_ttft_ms",
        "p75_ttft_ms",
        "p90_ttft_ms",
        "p95_ttft_ms",
        "median_itl_ms",
        "p90_itl_ms",
        "median_e2e_ms",
        "p90_e2e_ms",
        "median_observed_itl_implied_tps",
        "token_weighted_itl_ms",
        "median_post_ttft_tps",
        "wall_span_s",
        "wall_clock_output_rate",
        "total_h200_wall_time_s",
        "error_count",
        "cancellation_count",
        "sample_quality_flag",
        "source_request_count_total",
        "source_subagent_count",
        "source_total_input_tokens",
        "source_total_output_tokens",
        "source_recorded_span_s",
        "source_max_input_tokens",
        "source_max_output_tokens",
    ]


_KNOWN_SUBAGENT_BRANCH_TYPES = {
    "subagent",
    "subagent_main",
    "fanout",
    "auxiliary",
    "worker_group",
}
