"""Within-ID and high-confidence paired concurrency comparisons."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .metrics import percentile


def build_id_concurrency_ratios(id_summary: Any) -> Any:
    """Compare each ID/concurrency summary with conc1 or its lowest observed conc.

    This operates on ID-level summaries, never directly on request rows.  A
    baseline with different request coverage is retained and flagged rather
    than misrepresented as a one-for-one experiment.
    """

    import pandas as pd

    columns = _ratio_columns()
    if id_summary.empty:
        return pd.DataFrame(columns=columns)
    frame = id_summary.copy()
    _ensure_columns(
        frame,
        [
            "root_trace_id",
            "concurrency",
            "profiled_request_count",
            "total_input_tokens",
            "total_output_tokens",
            "median_ttft_ms",
            "median_itl_ms",
            "median_e2e_ms",
            "wall_clock_output_rate",
        ],
    )
    frame["concurrency"] = pd.to_numeric(frame["concurrency"], errors="coerce")
    frame = frame.loc[frame["root_trace_id"].notna() & frame["concurrency"].notna()].copy()
    rows: list[dict[str, Any]] = []
    for root_trace_id, group in frame.groupby("root_trace_id", dropna=False):
        group = group.sort_values("concurrency")
        baseline_candidates = group.loc[group["concurrency"] == 1]
        baseline = baseline_candidates.iloc[0] if not baseline_candidates.empty else group.iloc[0]
        baseline_concurrency = int(baseline["concurrency"])
        for _, current in group.iterrows():
            row = {
                "root_trace_id": root_trace_id,
                "concurrency": int(current["concurrency"]),
                "baseline_concurrency": baseline_concurrency,
                "baseline_available_at_conc1": bool(not baseline_candidates.empty),
                "profiled_request_count": _number(current["profiled_request_count"]),
                "baseline_profiled_request_count": _number(baseline["profiled_request_count"]),
                "total_input_tokens": _number(current["total_input_tokens"]),
                "baseline_total_input_tokens": _number(baseline["total_input_tokens"]),
                "total_output_tokens": _number(current["total_output_tokens"]),
                "baseline_total_output_tokens": _number(baseline["total_output_tokens"]),
                "median_ttft_ms": _number(current["median_ttft_ms"]),
                "baseline_median_ttft_ms": _number(baseline["median_ttft_ms"]),
                "median_itl_ms": _number(current["median_itl_ms"]),
                "baseline_median_itl_ms": _number(baseline["median_itl_ms"]),
                "median_e2e_ms": _number(current["median_e2e_ms"]),
                "baseline_median_e2e_ms": _number(baseline["median_e2e_ms"]),
                "wall_clock_output_rate": _number(current["wall_clock_output_rate"]),
                "baseline_wall_clock_output_rate": _number(baseline["wall_clock_output_rate"]),
            }
            row.update(
                {
                    "ttft_ratio": _ratio(row["median_ttft_ms"], row["baseline_median_ttft_ms"]),
                    "itl_ratio": _ratio(row["median_itl_ms"], row["baseline_median_itl_ms"]),
                    "e2e_ratio": _ratio(row["median_e2e_ms"], row["baseline_median_e2e_ms"]),
                    "wall_clock_output_rate_ratio": _ratio(
                        row["wall_clock_output_rate"], row["baseline_wall_clock_output_rate"]
                    ),
                    "request_coverage_ratio": _ratio(
                        row["profiled_request_count"], row["baseline_profiled_request_count"]
                    ),
                    "input_token_coverage_ratio": _ratio(
                        row["total_input_tokens"], row["baseline_total_input_tokens"]
                    ),
                    "output_token_coverage_ratio": _ratio(
                        row["total_output_tokens"], row["baseline_total_output_tokens"]
                    ),
                }
            )
            row["coverage_comparable"] = _coverage_comparable(row)
            rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def build_paired_turn_comparisons(
    profiled_frame: Any,
    *,
    require_exact_source_match: bool = True,
) -> Any:
    """Build cross-concurrency comparisons for a high-confidence request subset.

    Before matching different concurrency runs, repeated measurements in a
    run are collapsed to a pair-key/concurrency median.  The comparison is
    consequently a paired *turn-shape* comparison, not an assertion that two
    individual request records are independent or identical in timing.
    """

    import pandas as pd

    columns = _paired_columns()
    if profiled_frame.empty:
        return pd.DataFrame(columns=columns)
    frame = profiled_frame.copy()
    _ensure_columns(
        frame,
        [
            "root_trace_id",
            "conversation_id",
            "turn_index",
            "input_tokens",
            "output_tokens",
            "concurrency",
            "ttft_ms",
            "itl_ms",
            "e2e_ms",
            "request_start_ns",
            "match_class",
            "source_conversation_path",
            "source_branch_request_index",
            "branch_type",
            "source_branch_type",
            "theoretical_cached_tokens",
            "theoretical_new_tokens",
            "theoretical_cache_ratio",
            "rollback_blocks",
        ],
    )
    frame["concurrency"] = pd.to_numeric(frame["concurrency"], errors="coerce")
    frame["turn_index"] = pd.to_numeric(frame["turn_index"], errors="coerce")
    frame["input_tokens"] = pd.to_numeric(frame["input_tokens"], errors="coerce")
    if require_exact_source_match:
        # Missing source classification is not evidence of an exact turn.
        # Do not promote branch/turn-shaped H200 rows into a paired subset.
        frame = frame.loc[frame["match_class"] == "exact_turn_match"].copy()
    branch_path = frame["source_conversation_path"].where(
        frame["source_conversation_path"].notna(), frame["conversation_id"]
    )
    turn = frame["source_branch_request_index"].where(
        frame["source_branch_request_index"].notna(), frame["turn_index"]
    )
    frame["normalized_branch_path"] = branch_path.astype("string")
    frame["normalized_turn_index"] = pd.to_numeric(turn, errors="coerce")
    required = [
        "root_trace_id",
        "normalized_branch_path",
        "normalized_turn_index",
        "input_tokens",
        "concurrency",
    ]
    valid = frame[required].notna().all(axis=1)
    frame = frame.loc[valid].copy()
    if frame.empty:
        return pd.DataFrame(columns=columns)

    key_columns = [
        "root_trace_id",
        "normalized_branch_path",
        "normalized_turn_index",
        "input_tokens",
    ]
    collapsed_rows: list[dict[str, Any]] = []
    for keys, group in frame.groupby(key_columns + ["concurrency"], dropna=False):
        root, branch, turn_index, input_tokens, concurrency = keys
        collapsed_rows.append(
            {
                "root_trace_id": root,
                "normalized_branch_path": branch,
                "turn_index": int(turn_index),
                "input_tokens": float(input_tokens),
                "concurrency": int(concurrency),
                "replay_record_count": int(len(group)),
                "median_ttft_ms": percentile(group["ttft_ms"], 0.5),
                "median_itl_ms": percentile(group["itl_ms"], 0.5),
                "median_e2e_ms": percentile(group["e2e_ms"], 0.5),
                "median_output_tokens": percentile(group["output_tokens"], 0.5),
                "median_request_start_ns": percentile(group["request_start_ns"], 0.5),
                "branch_type": _first_nonnull(group["branch_type"]),
                "source_branch_type": _first_nonnull(group["source_branch_type"]),
                "theoretical_cached_tokens": percentile(group["theoretical_cached_tokens"], 0.5),
                "theoretical_new_tokens": percentile(group["theoretical_new_tokens"], 0.5),
                "theoretical_cache_ratio": percentile(group["theoretical_cache_ratio"], 0.5),
                "rollback_blocks": percentile(group["rollback_blocks"], 0.5),
            }
        )
    collapsed = pd.DataFrame(collapsed_rows)
    rows: list[dict[str, Any]] = []
    collapsed_key_columns = [
        "root_trace_id",
        "normalized_branch_path",
        "turn_index",
        "input_tokens",
    ]
    for _, group in collapsed.groupby(collapsed_key_columns, dropna=False):
        group = group.sort_values("concurrency")
        conc1 = group.loc[group["concurrency"] == 1]
        baseline = conc1.iloc[0] if not conc1.empty else group.iloc[0]
        baseline_concurrency = int(baseline["concurrency"])
        for _, current in group.iterrows():
            # A baseline-vs-itself row always has ratio 1 and is not a
            # cross-concurrency observation. Keeping it would bias paired
            # ratio distributions and clustered summaries toward no change.
            if int(current["concurrency"]) == baseline_concurrency:
                continue
            row = {
                "root_trace_id": current["root_trace_id"],
                "normalized_branch_path": current["normalized_branch_path"],
                "turn_index": int(current["turn_index"]),
                "input_tokens": current["input_tokens"],
                "concurrency": int(current["concurrency"]),
                "baseline_concurrency": baseline_concurrency,
                "baseline_available_at_conc1": bool(not conc1.empty),
                "matched_sample_count": int(current["replay_record_count"]),
                "baseline_matched_sample_count": int(baseline["replay_record_count"]),
                "ttft_ms": current["median_ttft_ms"],
                "baseline_ttft_ms": baseline["median_ttft_ms"],
                "itl_ms": current["median_itl_ms"],
                "baseline_itl_ms": baseline["median_itl_ms"],
                "e2e_ms": current["median_e2e_ms"],
                "baseline_e2e_ms": baseline["median_e2e_ms"],
                "output_tokens": current["median_output_tokens"],
                "baseline_output_tokens": baseline["median_output_tokens"],
                "request_start_ns": current["median_request_start_ns"],
                "baseline_request_start_ns": baseline["median_request_start_ns"],
                "branch_type": current["branch_type"],
                "source_branch_type": current["source_branch_type"],
                "theoretical_cached_tokens": current["theoretical_cached_tokens"],
                "theoretical_new_tokens": current["theoretical_new_tokens"],
                "theoretical_cache_ratio": current["theoretical_cache_ratio"],
                "rollback_blocks": current["rollback_blocks"],
            }
            row["ttft_delta_ms"] = _difference(row["ttft_ms"], row["baseline_ttft_ms"])
            row["itl_delta_ms"] = _difference(row["itl_ms"], row["baseline_itl_ms"])
            row["e2e_delta_ms"] = _difference(row["e2e_ms"], row["baseline_e2e_ms"])
            row["ttft_ratio"] = _ratio(row["ttft_ms"], row["baseline_ttft_ms"])
            row["itl_ratio"] = _ratio(row["itl_ms"], row["baseline_itl_ms"])
            row["e2e_ratio"] = _ratio(row["e2e_ms"], row["baseline_e2e_ms"])
            row["output_token_delta"] = _difference(
                row["output_tokens"], row["baseline_output_tokens"]
            )
            row["request_start_delta_s"] = _difference(
                row["request_start_ns"], row["baseline_request_start_ns"], scale=1e9
            )
            rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def build_exact_turn_cache_shape_table(profiled_frame: Any) -> Any:
    """Retain exact source/H200 turn joins for cache-shape relationship analysis.

    The source hash-derived values are theoretical workload prefix reuse, not
    evidence of server cache residency or actual cache-hit rate.
    """

    import pandas as pd

    columns = [
        "root_trace_id",
        "concurrency",
        "conversation_id",
        "branch_type",
        "source_branch_type",
        "turn_index",
        "input_tokens",
        "output_tokens",
        "ttft_ms",
        "itl_ms",
        "e2e_ms",
        "theoretical_cached_tokens",
        "theoretical_new_tokens",
        "theoretical_cache_ratio",
        "rollback_blocks",
        "match_class",
    ]
    if profiled_frame.empty or "match_class" not in profiled_frame:
        return pd.DataFrame(columns=columns)
    frame = profiled_frame.loc[profiled_frame["match_class"] == "exact_turn_match"].copy()
    for column in columns:
        if column not in frame:
            frame[column] = None
    return frame[columns]


def summarize_cache_shape_relationship(exact_turn_frame: Any) -> Any:
    """Summarize theoretical source cache shape versus observed H200 TTFT.

    Spearman correlations are descriptive, computed only at the request level
    inside an exact-match stratum. Replays and shared-system effects mean they
    are not causal estimates or independent-request confidence intervals.
    """

    import pandas as pd

    columns = [
        "concurrency",
        "branch_group",
        "exact_turn_request_count",
        "distinct_root_ids",
        "median_input_tokens",
        "median_ttft_ms",
        "median_theoretical_new_tokens",
        "median_theoretical_cache_ratio",
        "spearman_ttft_vs_input_tokens",
        "spearman_ttft_vs_theoretical_new_tokens",
        "spearman_ttft_vs_theoretical_cache_ratio",
    ]
    if exact_turn_frame.empty:
        return pd.DataFrame(columns=columns)
    frame = exact_turn_frame.copy()
    _ensure_columns(
        frame,
        [
            "concurrency",
            "branch_type",
            "root_trace_id",
            "input_tokens",
            "ttft_ms",
            "theoretical_new_tokens",
            "theoretical_cache_ratio",
        ],
    )
    rows: list[dict[str, Any]] = []
    for concurrency, conc_group in frame.groupby("concurrency", dropna=False):
        groups = [("all", conc_group)]
        groups.extend((str(name), group) for name, group in conc_group.groupby("branch_type", dropna=False))
        for branch_group, group in groups:
            numeric = group.copy()
            for field in (
                "input_tokens",
                "ttft_ms",
                "theoretical_new_tokens",
                "theoretical_cache_ratio",
            ):
                numeric[field] = pd.to_numeric(numeric[field], errors="coerce")
            rows.append(
                {
                    "concurrency": concurrency,
                    "branch_group": branch_group,
                    "exact_turn_request_count": int(len(group)),
                    "distinct_root_ids": int(group["root_trace_id"].nunique(dropna=True)),
                    "median_input_tokens": percentile(numeric["input_tokens"], 0.5),
                    "median_ttft_ms": percentile(numeric["ttft_ms"], 0.5),
                    "median_theoretical_new_tokens": percentile(
                        numeric["theoretical_new_tokens"], 0.5
                    ),
                    "median_theoretical_cache_ratio": percentile(
                        numeric["theoretical_cache_ratio"], 0.5
                    ),
                    "spearman_ttft_vs_input_tokens": _spearman(
                        numeric, "ttft_ms", "input_tokens"
                    ),
                    "spearman_ttft_vs_theoretical_new_tokens": _spearman(
                        numeric, "ttft_ms", "theoretical_new_tokens"
                    ),
                    "spearman_ttft_vs_theoretical_cache_ratio": _spearman(
                        numeric, "ttft_ms", "theoretical_cache_ratio"
                    ),
                }
            )
    return pd.DataFrame(rows, columns=columns)


def clustered_ratio_summary(
    paired_frame: Any,
    *,
    n_bootstrap: int = 1_000,
    random_state: int = 20260806,
) -> Any:
    """Summarize paired ratios with a root-ID-cluster bootstrap confidence interval."""

    import numpy as np
    import pandas as pd

    columns = [
        "concurrency",
        "metric",
        "paired_turn_count",
        "root_id_cluster_count",
        "median_ratio",
        "bootstrap_ci_low",
        "bootstrap_ci_high",
        "n_bootstrap",
    ]
    if paired_frame.empty:
        return pd.DataFrame(columns=columns)
    frame = paired_frame.copy()
    _ensure_columns(frame, ["concurrency", "root_trace_id", "ttft_ratio", "itl_ratio", "e2e_ratio"])
    rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(random_state)
    for concurrency, group in frame.groupby("concurrency", dropna=False):
        for metric in ("ttft_ratio", "itl_ratio", "e2e_ratio"):
            values = group[["root_trace_id", metric]].copy()
            values[metric] = pd.to_numeric(values[metric], errors="coerce")
            values = values.loc[values[metric].notna() & (values[metric] > 0)]
            clusters = list(values["root_trace_id"].dropna().unique())
            ci_low = ci_high = None
            if clusters:
                cluster_medians = {
                    cluster: values.loc[values["root_trace_id"] == cluster, metric].to_numpy()
                    for cluster in clusters
                }
                boot = []
                for _ in range(n_bootstrap):
                    sampled = rng.choice(clusters, size=len(clusters), replace=True)
                    draw = np.concatenate([cluster_medians[item] for item in sampled])
                    boot.append(float(np.median(draw)))
                ci_low, ci_high = (float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975)))
            rows.append(
                {
                    "concurrency": concurrency,
                    "metric": metric,
                    "paired_turn_count": int(len(values)),
                    "root_id_cluster_count": int(len(clusters)),
                    "median_ratio": percentile(values[metric], 0.5) if not values.empty else None,
                    "bootstrap_ci_low": ci_low,
                    "bootstrap_ci_high": ci_high,
                    "n_bootstrap": n_bootstrap,
                }
            )
    return pd.DataFrame(rows, columns=columns)


def _coverage_comparable(row: dict[str, Any]) -> bool | None:
    ratios = [
        row.get("request_coverage_ratio"),
        row.get("input_token_coverage_ratio"),
        row.get("output_token_coverage_ratio"),
    ]
    valid = [value for value in ratios if value is not None]
    if not valid:
        return None
    return all(0.8 <= value <= 1.25 for value in valid)


def _ratio(value: Any, baseline: Any) -> float | None:
    left = _number(value)
    right = _number(baseline)
    if left is None or right is None or right == 0:
        return None
    return left / right


def _difference(value: Any, baseline: Any, *, scale: float = 1.0) -> float | None:
    left = _number(value)
    right = _number(baseline)
    if left is None or right is None:
        return None
    return (left - right) / scale


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in {float("inf"), float("-inf")}:
        return None
    return number


def _first_nonnull(series: Any) -> Any | None:
    values = series.dropna()
    return values.iloc[0] if not values.empty else None


def _spearman(frame: Any, left: str, right: str) -> float | None:
    pair = frame[[left, right]].dropna()
    if len(pair) < 3 or pair[left].nunique() < 2 or pair[right].nunique() < 2:
        return None
    value = pair[left].corr(pair[right], method="spearman")
    return float(value) if value is not None else None


def _ensure_columns(frame: Any, columns: Sequence[str]) -> None:
    for column in columns:
        if column not in frame.columns:
            frame[column] = None


def _ratio_columns() -> list[str]:
    return [
        "root_trace_id",
        "concurrency",
        "baseline_concurrency",
        "baseline_available_at_conc1",
        "profiled_request_count",
        "baseline_profiled_request_count",
        "total_input_tokens",
        "baseline_total_input_tokens",
        "total_output_tokens",
        "baseline_total_output_tokens",
        "median_ttft_ms",
        "baseline_median_ttft_ms",
        "median_itl_ms",
        "baseline_median_itl_ms",
        "median_e2e_ms",
        "baseline_median_e2e_ms",
        "wall_clock_output_rate",
        "baseline_wall_clock_output_rate",
        "ttft_ratio",
        "itl_ratio",
        "e2e_ratio",
        "wall_clock_output_rate_ratio",
        "request_coverage_ratio",
        "input_token_coverage_ratio",
        "output_token_coverage_ratio",
        "coverage_comparable",
    ]


def _paired_columns() -> list[str]:
    return [
        "root_trace_id",
        "normalized_branch_path",
        "turn_index",
        "input_tokens",
        "concurrency",
        "baseline_concurrency",
        "baseline_available_at_conc1",
        "matched_sample_count",
        "baseline_matched_sample_count",
        "ttft_ms",
        "baseline_ttft_ms",
        "itl_ms",
        "baseline_itl_ms",
        "e2e_ms",
        "baseline_e2e_ms",
        "output_tokens",
        "baseline_output_tokens",
        "request_start_ns",
        "baseline_request_start_ns",
        "ttft_delta_ms",
        "itl_delta_ms",
        "e2e_delta_ms",
        "ttft_ratio",
        "itl_ratio",
        "e2e_ratio",
        "output_token_delta",
        "request_start_delta_s",
        "branch_type",
        "source_branch_type",
        "theoretical_cached_tokens",
        "theoretical_new_tokens",
        "theoretical_cache_ratio",
        "rollback_blocks",
    ]
