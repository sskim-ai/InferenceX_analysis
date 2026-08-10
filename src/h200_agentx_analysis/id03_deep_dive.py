"""Evidence-preserving helpers for the ID03 public-H200 deep dive.

The functions here deliberately work at the source-key/replay level.  A fixed
duration AgentX run can contain warmup, recycling, and partial trajectory
coverage, so raw request rows are never silently treated as independent,
one-to-one measurements across concurrencies.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .metrics import percentile, token_weighted_itl_ms, wall_clock_span

ID03_CANONICAL_ID = "07dd40536557a1d6440a923557c3129dc929"
CONTEXT_202752_UNAVAILABLE = "unavailable_exact_target_tokenization"
_CONCURRENCIES = (8, 12, 16)


def id03_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Select the fixed canonical ID03 without accepting a prefix substitute."""

    roots = frame.get(
        "root_trace_id", pd.Series(index=frame.index, dtype="string")
    ).astype("string")
    selected = frame.loc[roots == ID03_CANONICAL_ID].copy()
    return selected


def add_execution_ordinals(frame: pd.DataFrame) -> pd.DataFrame:
    """Add deterministic 0- and 1-based ordinals for raw/profile/root/branch order.

    Ordering is public replay chronology: request start timestamp, source file,
    then raw record ordinal.  Profile ordinals are null for rows that did not
    pass the study's documented successful-profiling filter.
    """

    work = frame.copy()
    if work.empty:
        return _empty_ordinal_columns(work)
    work = _sort_chronological(work).reset_index(drop=True)
    concurrency = pd.to_numeric(work.get("concurrency"), errors="coerce")
    work["execution_ordinal_all_0_based"] = work.groupby(concurrency, dropna=False).cumcount()
    work["execution_ordinal_all_1_based"] = work["execution_ordinal_all_0_based"] + 1
    root_keys = [
        concurrency,
        work.get("root_trace_id", pd.Series(index=work.index, dtype="string")).astype("string"),
    ]
    work["execution_ordinal_within_root_0_based"] = work.groupby(root_keys, dropna=False).cumcount()
    work["execution_ordinal_within_root_1_based"] = work["execution_ordinal_within_root_0_based"] + 1
    branch_keys = [
        concurrency,
        work.get("root_trace_id", pd.Series(index=work.index, dtype="string")).astype("string"),
        work.get("source_conversation_path", pd.Series(index=work.index, dtype="string"))
        .astype("string")
        .fillna("<unknown>"),
    ]
    work["execution_ordinal_within_branch_0_based"] = work.groupby(
        branch_keys, dropna=False
    ).cumcount()
    work["execution_ordinal_within_branch_1_based"] = (
        work["execution_ordinal_within_branch_0_based"] + 1
    )
    valid = _successful_profile_mask(work)
    profile_ordinal = pd.Series(pd.NA, index=work.index, dtype="Int64")
    profile_ordinal.loc[valid] = work.loc[valid].groupby(concurrency.loc[valid], dropna=False).cumcount().astype("Int64")
    work["execution_ordinal_profile_0_based"] = profile_ordinal
    work["execution_ordinal_profile_1_based"] = profile_ordinal + 1
    return work


def build_reference_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Return every ID03 raw/profile row in a local-join-ready public schema."""

    work = add_execution_ordinals(id03_rows(frame))
    if work.empty:
        return pd.DataFrame(columns=_REFERENCE_COLUMNS)
    logical_observed = pd.to_numeric(work.get("logical_prompt_tokens"), errors="coerce").notna()
    cache_observed = pd.to_numeric(work.get("cache_read_tokens"), errors="coerce").notna()
    itl = pd.to_numeric(work.get("itl_ms"), errors="coerce")
    output = pd.to_numeric(work.get("output_tokens"), errors="coerce")
    work["logical_prompt_metric_status"] = np.where(
        logical_observed,
        "explicit_target_logical_prompt_metric_observed",
        "not_exported_or_not_mapped",
    )
    work["cache_read_metric_status"] = np.where(
        cache_observed,
        "profile_counter_scope_unvalidated",
        "not_exported",
    )
    work["decode_tps"] = np.where((itl > 0) & (output > 1), 1000.0 / itl, np.nan)
    work["error"] = work.get("error_present", pd.Series(False, index=work.index)).fillna(False)
    work["cancelled"] = work.get("was_cancelled", pd.Series(False, index=work.index)).fillna(False)
    work["raw_record_ordinal"] = work.get("record_ordinal", pd.Series(pd.NA, index=work.index))
    # The raw source table represents root-level inner index as null, whereas
    # the public exact key represents it as -1.  Retain the raw fields and
    # publish explicit normalized companions for a local extractor to use.
    work["source_outer_idx_exact_key_normalized"] = _exact_key_index(
        work, "source_outer_idx"
    )
    work["source_inner_idx_exact_key_normalized"] = _exact_key_index(
        work, "source_inner_idx"
    )
    work["is_profiled_valid"] = _successful_profile_mask(work)
    for column in _REFERENCE_COLUMNS:
        if column not in work:
            work[column] = pd.NA
    return work[_REFERENCE_COLUMNS].copy()


def source_coverage_by_concurrency(
    reference: pd.DataFrame,
    *,
    source_request_count: int,
) -> pd.DataFrame:
    """Describe where each public replay entered and exited the source trajectory."""

    rows: list[dict[str, Any]] = []
    for concurrency in _CONCURRENCIES:
        group = reference.loc[pd.to_numeric(reference.get("concurrency"), errors="coerce") == concurrency]
        profile = group.loc[_successful_profile_mask(group)]
        chronological = _sort_chronological(group)
        profile_chronological = _sort_chronological(profile)
        starts = pd.to_numeric(group.get("request_start_ns"), errors="coerce")
        ends = pd.to_numeric(group.get("request_end_ns"), errors="coerce")
        span = None
        if starts.notna().any() and ends.notna().any():
            span = float((ends.max() - starts.min()) / 1e9)
        exact_profile = profile.get("exact_source_key", pd.Series(dtype="string")).dropna().astype(str)
        rows.append(
            {
                "concurrency": concurrency,
                "all_request_count": int(len(group)),
                "warmup_count": int(_phase_mask(group, "warmup").sum()),
                "profiling_phase_count": int(_phase_mask(group, "profiling").sum()),
                "successful_profiling_count": int(len(profile)),
                "first_source_outer_idx": _first_numeric(chronological, "source_outer_idx"),
                "last_source_outer_idx": _last_numeric(chronological, "source_outer_idx"),
                "first_source_inner_idx": _first_numeric(chronological, "source_inner_idx"),
                "last_source_inner_idx": _last_numeric(chronological, "source_inner_idx"),
                "first_exact_source_key": _first_text(chronological, "exact_source_key"),
                "last_exact_source_key": _last_text(chronological, "exact_source_key"),
                "first_profile_source_outer_idx": _first_numeric(profile_chronological, "source_outer_idx"),
                "last_profile_source_outer_idx": _last_numeric(profile_chronological, "source_outer_idx"),
                "first_profile_source_inner_idx": _first_numeric(profile_chronological, "source_inner_idx"),
                "last_profile_source_inner_idx": _last_numeric(profile_chronological, "source_inner_idx"),
                "first_profile_exact_source_key": _first_text(profile_chronological, "exact_source_key"),
                "last_profile_exact_source_key": _last_text(profile_chronological, "exact_source_key"),
                "distinct_source_outer_idx_count": _nunique(group, "source_outer_idx"),
                "distinct_exact_source_key_count_all": int(
                    group.get("exact_source_key", pd.Series(dtype="string")).dropna().astype(str).nunique()
                ),
                "distinct_exact_source_key_count_profile": int(exact_profile.nunique()),
                "source_coverage_ratio_profile": _ratio(int(exact_profile.nunique()), source_request_count),
                "source_trace_request_count": source_request_count,
                "distinct_source_branches": _nunique(group, "source_branch_type"),
                "distinct_conversation_paths": _nunique(group, "source_conversation_path"),
                "source_request_index_min": _min_numeric(group, "source_request_index"),
                "source_request_index_max": _max_numeric(group, "source_request_index"),
                "profile_source_request_index_min": _min_numeric(profile, "source_request_index"),
                "profile_source_request_index_max": _max_numeric(profile, "source_request_index"),
                "warmup_source_request_indices": _joined_sorted_numbers(group.loc[_phase_mask(group, "warmup")], "source_request_index"),
                "profiling_source_request_indices": _joined_sorted_numbers(profile, "source_request_index"),
                "source_input_tokens_min": _min_numeric(group, "source_input_tokens"),
                "source_input_tokens_max": _max_numeric(group, "source_input_tokens"),
                "source_output_tokens_total_all": _sum_numeric(group, "source_output_tokens"),
                "source_output_tokens_total_profile": _sum_numeric(profile, "source_output_tokens"),
                "first_request_start_ns": _first_numeric(chronological, "request_start_ns"),
                "last_request_end_ns": _last_numeric(chronological, "request_end_ns"),
                "wall_span_s": span,
                "error_count": int(_truthy_count(group.get("error"))),
                "cancellation_count": int(_truthy_count(group.get("cancelled"))),
                "duplicate_exact_source_key_count_profile": int(
                    exact_profile.duplicated(keep=False).sum()
                ),
                "coverage_ordering": "request_start_ns, source file, raw record ordinal",
            }
        )
    return pd.DataFrame(rows)


def collapse_source_key_profiles(reference: pd.DataFrame) -> pd.DataFrame:
    """Collapse repeated successful profile records to source-key medians."""

    profile = reference.loc[_successful_profile_mask(reference)].copy()
    if profile.empty:
        return pd.DataFrame(columns=_COLLAPSED_COLUMNS)
    rows: list[dict[str, Any]] = []
    for (concurrency, key), group in profile.groupby(["concurrency", "exact_source_key"], dropna=False):
        ordered = _sort_chronological(group)
        row: dict[str, Any] = {
            "concurrency": int(concurrency),
            "exact_source_key": key,
            "record_count": int(len(group)),
        }
        for field in (
            "root_trace_id",
            "source_trace_id",
            "source_conversation_path",
            "source_branch_type",
            "benchmark_phase",
        ):
            row[field] = _first_text(ordered, field)
        for field in (
            "source_outer_idx",
            "source_inner_idx",
            "source_outer_idx_exact_key_normalized",
            "source_inner_idx_exact_key_normalized",
            "source_request_index",
            "source_branch_request_index",
            "turn_index",
            "input_sequence_length",
            "usage_prompt_tokens",
            "source_input_tokens",
            "output_tokens",
            "ttft_ms",
            "itl_ms",
            "decode_tps",
            "e2e_ms",
        ):
            row[field] = _median_numeric(group, field)
        rows.append(row)
    result = pd.DataFrame(rows)
    for column in _COLLAPSED_COLUMNS:
        if column not in result:
            result[column] = pd.NA
    return result[_COLLAPSED_COLUMNS].sort_values(["concurrency", "exact_source_key"]).reset_index(drop=True)


def exact_pair_table(
    collapsed: pd.DataFrame,
    left_concurrency: int,
    right_concurrency: int,
) -> pd.DataFrame:
    """Build a conservative source-key median pair table for two concurrencies."""

    left = collapsed.loc[collapsed.get("concurrency") == left_concurrency].copy()
    right = collapsed.loc[collapsed.get("concurrency") == right_concurrency].copy()
    if left.empty or right.empty:
        return pd.DataFrame(columns=_PAIR_COLUMNS)
    left = left.add_prefix("left_").rename(columns={"left_exact_source_key": "exact_source_key"})
    right = right.add_prefix("right_").rename(columns={"right_exact_source_key": "exact_source_key"})
    result = left.merge(right, on="exact_source_key", how="inner", validate="one_to_one")
    result["left_concurrency"] = left_concurrency
    result["right_concurrency"] = right_concurrency
    result["source_path_validation"] = _source_path_validation(result)
    result["turn_index_validation"] = _numeric_validation(result, "turn_index")
    result["match_validation_status"] = _match_validation_status(
        result["source_path_validation"], result["turn_index_validation"]
    )
    result["same_output_length"] = _same_numeric(result, "output_tokens")
    result["ttft_ratio_right_over_left"] = _series_ratio(result, "ttft_ms")
    result["itl_ratio_right_over_left"] = _series_ratio(result, "itl_ms")
    result["decode_tps_ratio_right_over_left"] = _series_ratio(result, "decode_tps")
    result["e2e_ratio_right_over_left"] = _series_ratio(result, "e2e_ms")
    left_ttft = pd.to_numeric(result.get("left_ttft_ms"), errors="coerce")
    right_ttft = pd.to_numeric(result.get("right_ttft_ms"), errors="coerce")
    left_itl = pd.to_numeric(result.get("left_itl_ms"), errors="coerce")
    right_itl = pd.to_numeric(result.get("right_itl_ms"), errors="coerce")
    outputs = pd.to_numeric(result.get("left_output_tokens"), errors="coerce")
    # A source-key collision alone is not enough for the high-confidence
    # subset.  The path and turn remain validation fields because they are
    # loader-facing identifiers rather than part of the canonical join key.
    result["strict_ttft_subset"] = (
        (left_ttft > 0)
        & (right_ttft > 0)
        & (result["match_validation_status"] == "high_confidence_exact")
    )
    result["strict_decode_subset"] = (
        result["strict_ttft_subset"]
        & result["same_output_length"]
        & (outputs > 1)
        & (left_itl > 0)
        & (right_itl > 0)
    )
    result["matching_method"] = "source_trace_id+source_outer_idx+source_inner_idx; source-key median per concurrency"
    for column in _PAIR_COLUMNS:
        if column not in result:
            result[column] = pd.NA
    return result[_PAIR_COLUMNS].sort_values("exact_source_key").reset_index(drop=True)


def exact_all_table(collapsed: pd.DataFrame) -> pd.DataFrame:
    """Intersect c8/c12/c16 source keys, retaining all three source-key medians."""

    pair_8_12 = exact_pair_table(collapsed, 8, 12)
    pair_8_16 = exact_pair_table(collapsed, 8, 16)
    pair_12_16 = exact_pair_table(collapsed, 12, 16)
    if pair_8_12.empty or pair_8_16.empty or pair_12_16.empty:
        return pd.DataFrame(columns=_ALL_PAIR_COLUMNS)
    columns_8_12 = [
        "exact_source_key",
        "left_source_trace_id",
        "left_source_outer_idx",
        "left_source_inner_idx",
        "left_source_outer_idx_exact_key_normalized",
        "left_source_inner_idx_exact_key_normalized",
        "left_source_conversation_path",
        "left_turn_index",
        "left_input_sequence_length",
        "left_source_input_tokens",
        "left_output_tokens",
        "left_ttft_ms",
        "left_itl_ms",
        "left_decode_tps",
        "left_e2e_ms",
        "right_source_conversation_path",
        "right_turn_index",
        "right_input_sequence_length",
        "right_source_input_tokens",
        "right_output_tokens",
        "right_ttft_ms",
        "right_itl_ms",
        "right_decode_tps",
        "right_e2e_ms",
        "same_output_length",
        "strict_ttft_subset",
        "strict_decode_subset",
    ]
    base = pair_8_12[[column for column in columns_8_12 if column in pair_8_12]].copy()
    base = base.rename(
        columns={
            "left_source_trace_id": "source_trace_id",
            "left_source_outer_idx": "source_outer_idx",
            "left_source_inner_idx": "source_inner_idx",
            "left_source_outer_idx_exact_key_normalized": "source_outer_idx_exact_key_normalized",
            "left_source_inner_idx_exact_key_normalized": "source_inner_idx_exact_key_normalized",
            "left_source_conversation_path": "c8_source_conversation_path",
            "left_turn_index": "c8_turn_index",
            "left_input_sequence_length": "c8_input_sequence_length",
            "left_source_input_tokens": "c8_source_input_tokens",
            "left_output_tokens": "c8_output_tokens",
            "left_ttft_ms": "c8_ttft_ms",
            "left_itl_ms": "c8_itl_ms",
            "left_decode_tps": "c8_decode_tps",
            "left_e2e_ms": "c8_e2e_ms",
            "right_source_conversation_path": "c12_source_conversation_path",
            "right_turn_index": "c12_turn_index",
            "right_input_sequence_length": "c12_input_sequence_length",
            "right_source_input_tokens": "c12_source_input_tokens",
            "right_output_tokens": "c12_output_tokens",
            "right_ttft_ms": "c12_ttft_ms",
            "right_itl_ms": "c12_itl_ms",
            "right_decode_tps": "c12_decode_tps",
            "right_e2e_ms": "c12_e2e_ms",
            "same_output_length": "same_output_length_c8_c12",
            "strict_ttft_subset": "strict_ttft_c8_c12",
            "strict_decode_subset": "strict_decode_c8_c12",
        }
    )
    right_columns = [
        "exact_source_key",
        "right_source_conversation_path",
        "right_turn_index",
        "right_input_sequence_length",
        "right_source_input_tokens",
        "right_output_tokens",
        "right_ttft_ms",
        "right_itl_ms",
        "right_decode_tps",
        "right_e2e_ms",
        "same_output_length",
        "strict_ttft_subset",
        "strict_decode_subset",
        "ttft_ratio_right_over_left",
        "itl_ratio_right_over_left",
        "decode_tps_ratio_right_over_left",
        "e2e_ratio_right_over_left",
    ]
    c16 = pair_8_16[[column for column in right_columns if column in pair_8_16]].copy().rename(
        columns={
            "right_source_conversation_path": "c16_source_conversation_path",
            "right_turn_index": "c16_turn_index",
            "right_input_sequence_length": "c16_input_sequence_length",
            "right_source_input_tokens": "c16_source_input_tokens",
            "right_output_tokens": "c16_output_tokens",
            "right_ttft_ms": "c16_ttft_ms",
            "right_itl_ms": "c16_itl_ms",
            "right_decode_tps": "c16_decode_tps",
            "right_e2e_ms": "c16_e2e_ms",
            "same_output_length": "same_output_length_c8_c16",
            "strict_ttft_subset": "strict_ttft_c8_c16",
            "strict_decode_subset": "strict_decode_c8_c16",
            "ttft_ratio_right_over_left": "ttft_ratio_c16_over_c8",
            "itl_ratio_right_over_left": "itl_ratio_c16_over_c8",
            "decode_tps_ratio_right_over_left": "decode_tps_ratio_c16_over_c8",
            "e2e_ratio_right_over_left": "e2e_ratio_c16_over_c8",
        }
    )
    result = base.merge(c16, on="exact_source_key", how="inner", validate="one_to_one")
    c12_16_columns = [
        "exact_source_key",
        "same_output_length",
        "strict_ttft_subset",
        "strict_decode_subset",
        "ttft_ratio_right_over_left",
        "itl_ratio_right_over_left",
        "decode_tps_ratio_right_over_left",
        "e2e_ratio_right_over_left",
        "match_validation_status",
    ]
    c12_16 = pair_12_16[
        [column for column in c12_16_columns if column in pair_12_16]
    ].copy().rename(
        columns={
            "same_output_length": "same_output_length_c12_c16",
            "strict_ttft_subset": "strict_ttft_c12_c16",
            "strict_decode_subset": "strict_decode_c12_c16",
            "ttft_ratio_right_over_left": "ttft_ratio_c16_over_c12",
            "itl_ratio_right_over_left": "itl_ratio_c16_over_c12",
            "decode_tps_ratio_right_over_left": "decode_tps_ratio_c16_over_c12",
            "e2e_ratio_right_over_left": "e2e_ratio_c16_over_c12",
            "match_validation_status": "match_validation_status_c12_c16",
        }
    )
    result = result.merge(c12_16, on="exact_source_key", how="inner", validate="one_to_one")
    result["same_output_length_all"] = (
        result.get("same_output_length_c8_c12", False)
        & result.get("same_output_length_c8_c16", False)
        & result.get("same_output_length_c12_c16", False)
    )
    result["matching_method"] = "source_trace_id+source_outer_idx+source_inner_idx; source-key median per concurrency"
    for column in _ALL_PAIR_COLUMNS:
        if column not in result:
            result[column] = pd.NA
    return result[_ALL_PAIR_COLUMNS].sort_values("exact_source_key").reset_index(drop=True)


def cross_concurrency_summary(
    collapsed: pd.DataFrame,
    pairs: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Summarize exact source-key overlap and conservative ratio metrics."""

    rows: list[dict[str, Any]] = []
    for pair_name, table in pairs.items():
        if table.empty:
            left_concurrency, right_concurrency = _parse_pair_name(pair_name)
            rows.append(_empty_pair_summary(pair_name, left_concurrency, right_concurrency))
            continue
        left_concurrency = int(table["left_concurrency"].iloc[0])
        right_concurrency = int(table["right_concurrency"].iloc[0])
        left_keys = set(
            collapsed.loc[collapsed["concurrency"] == left_concurrency, "exact_source_key"].dropna()
        )
        right_keys = set(
            collapsed.loc[collapsed["concurrency"] == right_concurrency, "exact_source_key"].dropna()
        )
        strict_decode = table.loc[table["strict_decode_subset"]].copy()
        left_weighted = _weighted_itl_from_pair(strict_decode, "left")
        right_weighted = _weighted_itl_from_pair(strict_decode, "right")
        rows.append(
            {
                "pair": pair_name,
                "left_concurrency": left_concurrency,
                "right_concurrency": right_concurrency,
                "matched_source_key_count": int(len(table)),
                "same_output_length_count": int(table["same_output_length"].sum()),
                "strict_ttft_count": int(table["strict_ttft_subset"].sum()),
                "strict_decode_count": int(table["strict_decode_subset"].sum()),
                "median_ttft_ratio_right_over_left": percentile(
                    table.loc[table["strict_ttft_subset"], "ttft_ratio_right_over_left"], 0.5
                ),
                "p90_ttft_ratio_right_over_left": percentile(
                    table.loc[table["strict_ttft_subset"], "ttft_ratio_right_over_left"], 0.9
                ),
                "median_itl_ratio_right_over_left": percentile(
                    strict_decode["itl_ratio_right_over_left"], 0.5
                ),
                "weighted_itl_left_ms": left_weighted,
                "weighted_itl_right_ms": right_weighted,
                "weighted_itl_ratio_right_over_left": _ratio(right_weighted, left_weighted),
                "median_e2e_ratio_right_over_left": percentile(
                    table.loc[table["strict_ttft_subset"], "e2e_ratio_right_over_left"], 0.5
                ),
                "coverage_overlap_ratio_jaccard": _ratio(len(left_keys & right_keys), len(left_keys | right_keys)),
                "matching_method": "source_trace_id+source_outer_idx+source_inner_idx; source-key median per concurrency",
            }
        )
    return pd.DataFrame(rows)


def h200_scaling_curve(reference: pd.DataFrame, *, source_request_count: int) -> pd.DataFrame:
    """Build the ID03 public curve, using c8 as the explicit reference point."""

    rows: list[dict[str, Any]] = []
    for concurrency in _CONCURRENCIES:
        profile = reference.loc[
            (pd.to_numeric(reference.get("concurrency"), errors="coerce") == concurrency)
            & _successful_profile_mask(reference)
        ].copy()
        itl_weighted = token_weighted_itl_ms(profile)
        span, wall_tps = wall_clock_span(profile)
        exact_count = int(profile.get("exact_source_key", pd.Series(dtype="string")).dropna().nunique())
        rows.append(
            {
                "concurrency": concurrency,
                "profile_request_count": int(len(profile)),
                "coverage_ratio": _ratio(exact_count, source_request_count),
                "distinct_exact_source_key_count": exact_count,
                "ttft_mean_ms": _mean_numeric(profile, "ttft_ms"),
                "ttft_median_ms": percentile(profile.get("ttft_ms"), 0.5),
                "ttft_p90_ms": percentile(profile.get("ttft_ms"), 0.9),
                "ttft_p95_ms": percentile(profile.get("ttft_ms"), 0.95),
                "itl_sample_count": int(_itl_mask(profile).sum()),
                "weighted_itl_ms": itl_weighted,
                "weighted_decode_tps": _ratio(1000.0, itl_weighted),
                "e2e_median_ms": percentile(profile.get("e2e_ms"), 0.5),
                "e2e_p90_ms": percentile(profile.get("e2e_ms"), 0.9),
                "wall_span_s": span,
                "wall_output_tps": wall_tps,
                "output_tokens_total": _sum_numeric(profile, "output_tokens"),
            }
        )
    result = pd.DataFrame(rows).sort_values("concurrency").reset_index(drop=True)
    baseline = result.loc[result["concurrency"] == 8].iloc[0] if not result.empty else pd.Series()
    result["ttft_inflation_vs_c8"] = result["ttft_median_ms"].map(
        lambda value: _ratio(_number(value), _number(baseline.get("ttft_median_ms")))
    )
    result["tps_retention_vs_c8"] = result["weighted_decode_tps"].map(
        lambda value: _ratio(_number(value), _number(baseline.get("weighted_decode_tps")))
    )
    result["wall_throughput_ratio_vs_c8"] = result["wall_output_tps"].map(
        lambda value: _ratio(_number(value), _number(baseline.get("wall_output_tps")))
    )
    result["weighting"] = "output-transition-token-weighted ITL; wall output TPS is parallel-system rate"
    return result


def c8_latency_distribution(reference: pd.DataFrame) -> pd.DataFrame:
    """Emit c8 latency quantiles and output-length-bucket summaries in one table."""

    c8 = reference.loc[
        (pd.to_numeric(reference.get("concurrency"), errors="coerce") == 8)
        & _successful_profile_mask(reference)
    ].copy()
    rows: list[dict[str, Any]] = []
    for metric, data in (
        ("ttft_ms", pd.to_numeric(c8.get("ttft_ms"), errors="coerce")),
        ("itl_ms", pd.to_numeric(c8.get("itl_ms"), errors="coerce").loc[_itl_mask(c8)]),
        ("e2e_ms", pd.to_numeric(c8.get("e2e_ms"), errors="coerce")),
    ):
        for label, quantile in (("P10", 0.10), ("P25", 0.25), ("P50", 0.50), ("P75", 0.75), ("P90", 0.90), ("P95", 0.95), ("P99", 0.99)):
            rows.append(
                {
                    "summary_type": "latency_quantile",
                    "metric": metric,
                    "bucket": None,
                    "quantile": label,
                    "value": percentile(data, quantile),
                    "sample_count": int(data.dropna().shape[0]),
                    "weighting": "request-level quantile",
                }
            )
    output = pd.to_numeric(c8.get("output_tokens"), errors="coerce")
    labels = ["1", "2-32", "33-128", "129-512", "513-2048", ">2048"]
    buckets = pd.cut(output, bins=[0, 1, 32, 128, 512, 2048, np.inf], labels=labels, include_lowest=True)
    for label in labels:
        group = c8.loc[buckets.astype("string") == label]
        itl_weighted = token_weighted_itl_ms(group)
        rows.append(
            {
                "summary_type": "output_length_bucket",
                "metric": "mixed_latency_and_decode",
                "bucket": label,
                "quantile": None,
                "value": None,
                "sample_count": int(len(group)),
                "ttft_median_ms": percentile(group.get("ttft_ms"), 0.5),
                "ttft_p90_ms": percentile(group.get("ttft_ms"), 0.9),
                "weighted_itl_ms": itl_weighted,
                "weighted_decode_tps": _ratio(1000.0, itl_weighted),
                "output_tokens_total": _sum_numeric(group, "output_tokens"),
                "weighting": "ITL is output-transition-token weighted within bucket",
            }
        )
    return pd.DataFrame(rows)


def c8_source_input_buckets(reference: pd.DataFrame) -> pd.DataFrame:
    """Summarize source-workload input proxy buckets without calling them GLM context."""

    c8 = reference.loc[
        (pd.to_numeric(reference.get("concurrency"), errors="coerce") == 8)
        & _successful_profile_mask(reference)
    ].copy()
    source_input = pd.to_numeric(c8.get("source_input_tokens"), errors="coerce")
    labels = ["<32k", "32-64k", "64-128k", "128-192k", "192-256k", "256k+"]
    bucket = pd.cut(
        source_input,
        bins=[-np.inf, 32_000, 64_000, 128_000, 192_000, 256_000, np.inf],
        labels=labels,
        right=False,
    )
    rows: list[dict[str, Any]] = []
    for label in labels:
        group = c8.loc[bucket.astype("string") == label]
        itl_weighted = token_weighted_itl_ms(group)
        rows.append(
            {
                "source_input_token_bucket": label,
                "request_count": int(len(group)),
                "source_input_tokens_min": _min_numeric(group, "source_input_tokens"),
                "source_input_tokens_max": _max_numeric(group, "source_input_tokens"),
                "ttft_median_ms": percentile(group.get("ttft_ms"), 0.5),
                "ttft_p90_ms": percentile(group.get("ttft_ms"), 0.9),
                "weighted_itl_ms": itl_weighted,
                "weighted_decode_tps": _ratio(1000.0, itl_weighted),
                "output_tokens_total": _sum_numeric(group, "output_tokens"),
                "metric_scope": "source-workload input proxy; not target GLM logical context",
            }
        )
    return pd.DataFrame(rows)


def context_202752_status(reference: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return an empty compatible request table unless target tokenization is explicit."""

    logical = pd.to_numeric(
        reference.get("logical_prompt_tokens", pd.Series(index=reference.index, dtype=float)),
        errors="coerce",
    )
    if logical.notna().any():
        # An explicit logical value alone still lacks a requested-output limit,
        # so no fit subset is produced without the loader's documented rule.
        reason = "requested_output_limit_or_loader_fit_rule_not_available"
        status = "unavailable_incomplete_exact_fit_rule"
    else:
        reason = "no_request_level_target_model_logical_prompt_metric_in_public_profile_or_join"
        status = CONTEXT_202752_UNAVAILABLE
    empty = pd.DataFrame(
        columns=[
            "concurrency",
            "exact_source_key",
            "context_202752_subset_status",
            "target_logical_prompt_tokens",
            "requested_output_limit",
        ]
    )
    metadata = pd.DataFrame(
        [
            {
                "context_202752_subset_status": status,
                "reason": reason,
                "logical_prompt_metric_observed_row_count": int(logical.notna().sum()),
                "forbidden_proxies": "input_sequence_length; source_input_tokens",
                "required_future_evidence": "exact target logical prompt tokens + requested output limit + documented loader/server fit rule",
            }
        ]
    )
    return empty, metadata


def _successful_profile_mask(frame: pd.DataFrame) -> pd.Series:
    if "is_profiled_valid" in frame:
        values = frame["is_profiled_valid"]
        return values.fillna(False).astype(bool)
    phase = frame.get("benchmark_phase", pd.Series(index=frame.index, dtype="string")).astype("string").str.lower()
    errors = frame.get("error", frame.get("error_present", pd.Series(False, index=frame.index))).fillna(False).astype(bool)
    cancelled = frame.get("cancelled", frame.get("was_cancelled", pd.Series(False, index=frame.index))).fillna(False).astype(bool)
    return phase.isin(["profiling", "profile"]) & ~errors & ~cancelled


def _phase_mask(frame: pd.DataFrame, phase_name: str) -> pd.Series:
    phase = frame.get("benchmark_phase", pd.Series(index=frame.index, dtype="string")).astype("string").str.lower()
    aliases = {"warmup": ["warmup", "warming", "warm_up"], "profiling": ["profiling", "profile"]}
    return phase.isin(aliases[phase_name])


def _available_order_columns(frame: pd.DataFrame) -> list[str]:
    result = [
        column
        for column in ("request_start_ns", "request_ack_ns", "source_file_path", "record_ordinal")
        if column in frame
    ]
    return result


def _sort_chronological(frame: pd.DataFrame) -> pd.DataFrame:
    columns = _available_order_columns(frame)
    return frame.sort_values(columns, kind="stable") if columns else frame.copy()


def _empty_ordinal_columns(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in (
        "execution_ordinal_all_0_based",
        "execution_ordinal_all_1_based",
        "execution_ordinal_profile_0_based",
        "execution_ordinal_profile_1_based",
        "execution_ordinal_within_root_0_based",
        "execution_ordinal_within_root_1_based",
        "execution_ordinal_within_branch_0_based",
        "execution_ordinal_within_branch_1_based",
    ):
        result[column] = pd.Series(dtype="Int64")
    return result


def _first_text(frame: pd.DataFrame, field: str) -> str | None:
    if field not in frame:
        return None
    for value in frame[field]:
        if pd.notna(value) and str(value):
            return str(value)
    return None


def _last_text(frame: pd.DataFrame, field: str) -> str | None:
    if field not in frame:
        return None
    values = frame[field].dropna()
    return str(values.iloc[-1]) if not values.empty else None


def _first_numeric(frame: pd.DataFrame, field: str) -> float | int | None:
    if field not in frame:
        return None
    values = pd.to_numeric(frame[field], errors="coerce").dropna()
    return _native_number(values.iloc[0]) if not values.empty else None


def _last_numeric(frame: pd.DataFrame, field: str) -> float | int | None:
    if field not in frame:
        return None
    values = pd.to_numeric(frame[field], errors="coerce").dropna()
    return _native_number(values.iloc[-1]) if not values.empty else None


def _min_numeric(frame: pd.DataFrame, field: str) -> float | int | None:
    if field not in frame:
        return None
    values = pd.to_numeric(frame[field], errors="coerce").dropna()
    return _native_number(values.min()) if not values.empty else None


def _max_numeric(frame: pd.DataFrame, field: str) -> float | int | None:
    if field not in frame:
        return None
    values = pd.to_numeric(frame[field], errors="coerce").dropna()
    return _native_number(values.max()) if not values.empty else None


def _joined_sorted_numbers(frame: pd.DataFrame, field: str) -> str | None:
    """Keep exact source-position coverage reviewable without changing the join key."""

    if field not in frame:
        return None
    values = pd.to_numeric(frame[field], errors="coerce").dropna().astype("int64")
    if values.empty:
        return None
    return ";".join(str(value) for value in sorted(values.unique().tolist()))


def _median_numeric(frame: pd.DataFrame, field: str) -> float | None:
    if field not in frame:
        return None
    return percentile(pd.to_numeric(frame[field], errors="coerce"), 0.5)


def _mean_numeric(frame: pd.DataFrame, field: str) -> float | None:
    if field not in frame:
        return None
    values = pd.to_numeric(frame[field], errors="coerce").dropna()
    return float(values.mean()) if not values.empty else None


def _sum_numeric(frame: pd.DataFrame, field: str) -> float | None:
    if field not in frame:
        return None
    values = pd.to_numeric(frame[field], errors="coerce").dropna()
    return float(values.sum()) if not values.empty else None


def _nunique(frame: pd.DataFrame, field: str) -> int:
    if field not in frame:
        return 0
    return int(frame[field].dropna().astype(str).nunique())


def _truthy_count(series: pd.Series | None) -> int:
    if series is None:
        return 0
    return int(series.fillna(False).astype(bool).sum())


def _ratio(numerator: Any, denominator: Any) -> float | None:
    left = _number(numerator)
    right = _number(denominator)
    if left is None or right is None or right == 0:
        return None
    return left / right


def _number(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _native_number(value: Any) -> float | int:
    numeric = float(value)
    return int(numeric) if numeric.is_integer() else numeric


def _exact_key_index(frame: pd.DataFrame, field: str) -> pd.Series:
    """Normalize nullable source indices to the documented exact-key sentinel."""

    values = pd.to_numeric(
        frame.get(field, pd.Series(index=frame.index, dtype=float)), errors="coerce"
    )
    return values.fillna(-1).astype("Int64")


def _source_path_validation(frame: pd.DataFrame) -> pd.Series:
    left = frame.get("left_source_conversation_path", pd.Series(index=frame.index, dtype="string"))
    right = frame.get("right_source_conversation_path", pd.Series(index=frame.index, dtype="string"))
    return pd.Series(
        np.where(
            left.isna() | right.isna(),
            "validation_missing",
            np.where(left.astype(str) == right.astype(str), "match", "conflict"),
        ),
        index=frame.index,
        dtype="string",
    )


def _numeric_validation(frame: pd.DataFrame, field: str) -> pd.Series:
    left = pd.to_numeric(frame.get(f"left_{field}"), errors="coerce")
    right = pd.to_numeric(frame.get(f"right_{field}"), errors="coerce")
    return pd.Series(
        np.where(left.isna() | right.isna(), "validation_missing", np.where(left == right, "match", "conflict")),
        index=frame.index,
        dtype="string",
    )


def _match_validation_status(
    source_path_validation: pd.Series, turn_index_validation: pd.Series
) -> pd.Series:
    """Classify an exact-key pair without silently accepting conflicts."""

    source = source_path_validation.astype("string")
    turn = turn_index_validation.astype("string")
    return pd.Series(
        np.where(
            (source == "conflict") | (turn == "conflict"),
            "key_match_validation_conflict",
            np.where(
                (source == "match") & (turn == "match"),
                "high_confidence_exact",
                "key_match_validation_missing",
            ),
        ),
        index=source.index,
        dtype="string",
    )


def _same_numeric(frame: pd.DataFrame, field: str) -> pd.Series:
    left = pd.to_numeric(frame.get(f"left_{field}"), errors="coerce")
    right = pd.to_numeric(frame.get(f"right_{field}"), errors="coerce")
    return left.notna() & right.notna() & (left == right)


def _series_ratio(frame: pd.DataFrame, field: str) -> pd.Series:
    left = pd.to_numeric(frame.get(f"left_{field}"), errors="coerce")
    right = pd.to_numeric(frame.get(f"right_{field}"), errors="coerce")
    return right / left.where(left != 0)


def _weighted_itl_from_pair(frame: pd.DataFrame, side: str) -> float | None:
    if frame.empty:
        return None
    itl = pd.to_numeric(frame.get(f"{side}_itl_ms"), errors="coerce")
    outputs = pd.to_numeric(frame.get(f"{side}_output_tokens"), errors="coerce")
    weights = outputs - 1
    valid = (itl > 0) & (weights > 0)
    if not valid.any():
        return None
    return float((itl.loc[valid] * weights.loc[valid]).sum() / weights.loc[valid].sum())


def _parse_pair_name(value: str) -> tuple[int, int]:
    pieces = value.split("_")
    return int(pieces[-2].removeprefix("c")), int(pieces[-1].removeprefix("c"))


def _empty_pair_summary(pair: str, left: int, right: int) -> dict[str, Any]:
    return {
        "pair": pair,
        "left_concurrency": left,
        "right_concurrency": right,
        "matched_source_key_count": 0,
        "same_output_length_count": 0,
        "strict_ttft_count": 0,
        "strict_decode_count": 0,
        "median_ttft_ratio_right_over_left": None,
        "p90_ttft_ratio_right_over_left": None,
        "median_itl_ratio_right_over_left": None,
        "weighted_itl_left_ms": None,
        "weighted_itl_right_ms": None,
        "weighted_itl_ratio_right_over_left": None,
        "median_e2e_ratio_right_over_left": None,
        "coverage_overlap_ratio_jaccard": None,
        "matching_method": "source_trace_id+source_outer_idx+source_inner_idx; source-key median per concurrency",
    }


def _itl_mask(frame: pd.DataFrame) -> pd.Series:
    itl = pd.to_numeric(frame.get("itl_ms"), errors="coerce")
    outputs = pd.to_numeric(frame.get("output_tokens"), errors="coerce")
    return (itl > 0) & (outputs > 1)


_REFERENCE_COLUMNS = [
    "concurrency",
    "root_trace_id",
    "source_trace_id",
    "source_outer_idx",
    "source_inner_idx",
    "source_outer_idx_exact_key_normalized",
    "source_inner_idx_exact_key_normalized",
    "source_request_index",
    "source_conversation_path",
    "source_branch_type",
    "source_branch_request_index",
    "conversation_id",
    "session_num",
    "turn_index",
    "benchmark_phase",
    "request_start_ns",
    "request_ack_ns",
    "request_end_ns",
    "raw_record_ordinal",
    "execution_ordinal_all_0_based",
    "execution_ordinal_all_1_based",
    "execution_ordinal_profile_0_based",
    "execution_ordinal_profile_1_based",
    "execution_ordinal_within_root_0_based",
    "execution_ordinal_within_root_1_based",
    "execution_ordinal_within_branch_0_based",
    "execution_ordinal_within_branch_1_based",
    "worker_id",
    "input_sequence_length",
    "usage_prompt_tokens",
    "source_input_tokens",
    "source_output_tokens",
    "logical_prompt_tokens",
    "logical_prompt_metric_status",
    "cache_read_tokens",
    "cache_read_metric_status",
    "output_tokens",
    "ttft_ms",
    "itl_ms",
    "decode_tps",
    "e2e_ms",
    "exact_source_key",
    "error",
    "cancelled",
    "is_profiled_valid",
]

_COLLAPSED_COLUMNS = [
    "concurrency",
    "exact_source_key",
    "record_count",
    "root_trace_id",
    "source_trace_id",
    "source_conversation_path",
    "source_branch_type",
    "benchmark_phase",
    "source_outer_idx",
    "source_inner_idx",
    "source_outer_idx_exact_key_normalized",
    "source_inner_idx_exact_key_normalized",
    "source_request_index",
    "source_branch_request_index",
    "turn_index",
    "input_sequence_length",
    "usage_prompt_tokens",
    "source_input_tokens",
    "output_tokens",
    "ttft_ms",
    "itl_ms",
    "decode_tps",
    "e2e_ms",
]

_PAIR_COLUMNS = [
    "exact_source_key",
    "left_concurrency",
    "right_concurrency",
    "left_record_count",
    "right_record_count",
    "left_source_trace_id",
    "left_source_outer_idx",
    "left_source_inner_idx",
    "left_source_outer_idx_exact_key_normalized",
    "left_source_inner_idx_exact_key_normalized",
    "left_source_request_index",
    "left_source_conversation_path",
    "right_source_conversation_path",
    "left_source_branch_type",
    "right_source_branch_type",
    "left_turn_index",
    "right_turn_index",
    "source_path_validation",
    "turn_index_validation",
    "match_validation_status",
    "left_benchmark_phase",
    "right_benchmark_phase",
    "left_input_sequence_length",
    "right_input_sequence_length",
    "left_source_input_tokens",
    "right_source_input_tokens",
    "left_output_tokens",
    "right_output_tokens",
    "same_output_length",
    "left_ttft_ms",
    "right_ttft_ms",
    "ttft_ratio_right_over_left",
    "left_itl_ms",
    "right_itl_ms",
    "itl_ratio_right_over_left",
    "left_decode_tps",
    "right_decode_tps",
    "decode_tps_ratio_right_over_left",
    "left_e2e_ms",
    "right_e2e_ms",
    "e2e_ratio_right_over_left",
    "strict_ttft_subset",
    "strict_decode_subset",
    "matching_method",
]

_ALL_PAIR_COLUMNS = [
    "exact_source_key",
    "source_trace_id",
    "source_outer_idx",
    "source_inner_idx",
    "c8_source_conversation_path",
    "c12_source_conversation_path",
    "c16_source_conversation_path",
    "c8_turn_index",
    "c12_turn_index",
    "c16_turn_index",
    "c8_input_sequence_length",
    "c12_input_sequence_length",
    "c16_input_sequence_length",
    "c8_source_input_tokens",
    "c12_source_input_tokens",
    "c16_source_input_tokens",
    "c8_output_tokens",
    "c12_output_tokens",
    "c16_output_tokens",
    "same_output_length_c8_c12",
    "same_output_length_c8_c16",
    "same_output_length_all",
    "same_output_length_c12_c16",
    "strict_ttft_c12_c16",
    "strict_decode_c12_c16",
    "ttft_ratio_c16_over_c12",
    "itl_ratio_c16_over_c12",
    "decode_tps_ratio_c16_over_c12",
    "e2e_ratio_c16_over_c12",
    "match_validation_status_c12_c16",
    "c8_ttft_ms",
    "c12_ttft_ms",
    "c16_ttft_ms",
    "c8_itl_ms",
    "c12_itl_ms",
    "c16_itl_ms",
    "c8_decode_tps",
    "c12_decode_tps",
    "c16_decode_tps",
    "c8_e2e_ms",
    "c12_e2e_ms",
    "c16_e2e_ms",
    "ttft_ratio_c16_over_c8",
    "itl_ratio_c16_over_c8",
    "decode_tps_ratio_c16_over_c8",
    "e2e_ratio_c16_over_c8",
    "strict_ttft_c8_c12",
    "strict_decode_c8_c12",
    "strict_ttft_c8_c16",
    "strict_decode_c8_c16",
    "matching_method",
]
