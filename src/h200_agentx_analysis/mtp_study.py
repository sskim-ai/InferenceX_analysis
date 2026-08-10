"""Shared, evidence-preserving helpers for the GPU-resident MTP study.

The public profile export is treated as an evolving external schema.  This
module deliberately distinguishes its AIPerf input sequence length from an
explicit logical-prompt/cache metric: a missing server metric is represented
as missing data rather than inferred from a similarly named field.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from .artifact_parser import (
    _as_number_or_none,
    _duration_to_ms,
    flatten_record,
    lookup_flat_value,
    normalize_profile_record,
)
from .id_normalization import normalize_conversation_id
from .metrics import percentile, token_weighted_itl_ms, wall_clock_span

REQUESTED_IDS: tuple[tuple[str, str, str], ...] = (
    ("ID01", "0196085d85d2075a50b74cd8795ffbdcea9a", "full"),
    ("ID02", "02bc0afb13f7a2d9efa86c28511261d85c0e", "full"),
    ("ID03", "07dd405", "prefix"),
    ("ID04", "264478", "prefix"),
    ("ID05", "debc7f6", "prefix"),
)

# These aliases are intentionally strict.  In particular, input_sequence_length
# is not an alias for logical_prompt_tokens because their equivalence has to be
# established from a frontend/server metric or a documented exporter contract.
EXTRA_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "decode_duration_ms": ("decode_duration",),
    "full_decode_duration_ms": ("full_decode_duration",),
    "logical_prompt_tokens": (
        "logical_prompt_tokens",
        "logical_prompt_token_count",
        "dynamo_frontend_input_sequence_tokens",
    ),
    "usage_prompt_tokens": ("usage_prompt_tokens",),
    "cache_read_tokens": (
        "usage_prompt_cache_read_tokens",
        "usage.prompt_cache_read_tokens",
        "prompt_cache_read_tokens",
        "cache_read_tokens",
        "cached_tokens",
        "cache_hit_tokens",
        "logical_kv_load_tokens",
    ),
    "cache_write_tokens": (
        "cache_write_tokens",
        "cache_creation_input_tokens",
        "prompt_cache_write_tokens",
        "store_tokens",
        "kv_store_tokens",
    ),
    "mtp_draft_tokens": (
        "mtp_draft_tokens",
        "draft_tokens",
        "speculative_draft_tokens",
        "num_draft_tokens",
    ),
    "mtp_accepted_tokens": (
        "mtp_accepted_tokens",
        "accepted_tokens",
        "speculative_accepted_tokens",
        "num_accepted_tokens",
    ),
    "mtp_acceptance_length": (
        "mtp_acceptance_length",
        "acceptance_length",
        "accepted_length",
        "speculative_acceptance_length",
    ),
    "mtp_acceptance_rate": (
        "mtp_acceptance_rate",
        "acceptance_rate",
        "speculative_acceptance_rate",
    ),
    "status": ("status", "request_status", "result_status"),
}

EXTRA_FIELDS = tuple(EXTRA_FIELD_ALIASES)


def extract_mtp_profile_record(
    record: Mapping[str, Any],
    *,
    context: Mapping[str, Any],
    source_file: str,
    record_ordinal: int,
) -> dict[str, Any]:
    """Normalize one profile record plus explicit GPU-resident/MTP fields.

    The returned row contains a ``raw_<field>_path`` companion for every
    study-specific field, making the later schema mapping auditable.
    """

    row = normalize_profile_record(
        record,
        context=context,
        source_file=source_file,
        record_ordinal=record_ordinal,
    )
    flattened = flatten_record(record)
    for field, aliases in {
        "input_sequence_length": (
            "input_sequence_length",
            "input_tokens",
            "input_token_count",
            "isl",
        ),
        "output_sequence_length": (
            "output_sequence_length",
            "output_tokens",
            "output_token_count",
            "osl",
        ),
    }.items():
        _, path = lookup_flat_value(flattened, aliases)
        row[f"raw_{field}_field"] = path
    for field, aliases in EXTRA_FIELD_ALIASES.items():
        value, path = lookup_flat_value(flattened, aliases)
        if field == "status":
            row[field] = _text_or_none(value)
        elif field.endswith("_ms"):
            row[field] = _duration_to_ms(value, path, unit=_metric_unit(flattened, path))
        else:
            row[field] = _as_number_or_none(value)
        row[f"raw_{field}_field"] = path

    # Retain the raw exporter metric under an explicit name, independently of
    # any prospective logical-prompt interpretation.
    row["input_sequence_length"] = row.get("input_tokens")
    row["output_sequence_length"] = row.get("output_tokens")
    output_for_itl = _number(row.get("output_tokens"))
    if (
        _number(row.get("itl_ms")) is None
        and output_for_itl is not None
        and output_for_itl > 1
        and _number(row.get("decode_duration_ms")) is not None
    ):
        row["itl_ms"] = _number(row["decode_duration_ms"]) / (output_for_itl - 1)
        row["raw_itl_field"] = (
            f"derived:{row.get('raw_decode_duration_ms_field')}"
            "/(output_sequence_length-1)"
        )
        row["source_metric_name"] = "decode_duration"
        row["itl_interpretation"] = (
            "request-level ITL derived from decode_duration/(output_sequence_length-1)"
        )
    row["source_trace_id"] = _text_or_none(row.get("source_trace_id"))
    normalized = normalize_conversation_id(row.get("conversation_id"))
    if row["source_trace_id"]:
        row["root_trace_id"] = row["source_trace_id"]
        row["root_trace_id_provenance"] = "metadata.source_trace_id"
        row["normalization_rule"] = "explicit_metadata_source_trace_id"
    else:
        row.update(normalized.to_dict())
        row["root_trace_id_provenance"] = "conversation_id_normalization"
    row["branch_type"] = row.get("branch_type") or normalized.branch_type

    logical = _number(row.get("logical_prompt_tokens"))
    cache = _number(row.get("cache_read_tokens"))
    output = _number(row.get("output_tokens"))
    if logical is not None and cache is not None and logical >= cache >= 0:
        row["new_prompt_tokens"] = logical - cache
    else:
        row["new_prompt_tokens"] = None
    new_prompt = _number(row.get("new_prompt_tokens"))
    row["kv_write_eligible_tokens"] = (
        new_prompt + output if new_prompt is not None and output is not None and output >= 0 else None
    )
    accepted = _number(row.get("mtp_accepted_tokens"))
    draft = _number(row.get("mtp_draft_tokens"))
    provided_rate = _number(row.get("mtp_acceptance_rate"))
    row["mtp_observed_acceptance_rate"] = (
        provided_rate
        if provided_rate is not None
        else (accepted / draft if accepted is not None and draft is not None and draft > 0 else None)
    )
    row["source_id_matched"] = False
    row["source_conversation_path"] = None
    row["source_branch_type"] = None
    row["source_branch_request_index"] = None
    row["match_class"] = "unmatched"
    row["exact_source_key"] = None
    return row


def add_source_metadata_join(frame: Any, source_requests: Any, source_ids: Iterable[str]) -> Any:
    """Attach direct source-loader metadata without equating token semantics.

    A matching ``source_trace_id + source_outer_idx + source_inner_idx`` is a
    high-confidence provenance join.  It remains labelled
    ``loader_metadata_turn_match`` rather than an exact input-length join when
    the profile's AIPerf input length differs from the source representation.
    """

    import numpy as np
    import pandas as pd

    result = frame.copy()
    if result.empty:
        return result
    source_id_set = {str(value) for value in source_ids if _text_or_none(value)}
    result["root_trace_id"] = result["root_trace_id"].astype("string")
    result["source_trace_id"] = result.get("source_trace_id", pd.Series(dtype="string")).astype(
        "string"
    )
    result["source_id_matched"] = result["root_trace_id"].isin(source_id_set)
    result["match_class"] = np.where(result["source_id_matched"], "root_only_match", "unmatched")
    if source_requests.empty:
        return result

    source = source_requests.copy()
    required = {
        "root_trace_id",
        "source_outer_request_index",
        "source_inner_request_index",
    }
    if not required.issubset(source.columns):
        return result
    source["root_trace_id"] = source["root_trace_id"].astype("string")
    source["_outer_key"] = _index_key(source["source_outer_request_index"], missing=-999999)
    source["_inner_key"] = _index_key(source["source_inner_request_index"], missing=-1)
    source = source.loc[source["_outer_key"] != -999999].copy()
    key_columns = ["root_trace_id", "_outer_key", "_inner_key"]
    duplicate_keys = source.duplicated(key_columns, keep=False)
    source = source.loc[~duplicate_keys].copy()
    source_columns = [
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
    ]
    available = [column for column in source_columns if column in source]
    source = source[[*key_columns, *available]].copy()
    # Placeholder source fields are installed by ``extract_mtp_profile_record``
    # for a stable pre-join Parquet schema.  Remove them before merge so the
    # actual source values do not become hidden behind pandas ``_source``
    # suffixes.
    result = result.drop(columns=available, errors="ignore")
    result["_outer_key"] = _index_key(result.get("source_outer_idx"), missing=-999999)
    result["_inner_key"] = _index_key(result.get("source_inner_idx"), missing=-1)
    result = result.merge(source, how="left", on=key_columns, suffixes=("", "_source"))
    matched = result["source_conversation_path"].notna() if "source_conversation_path" in result else False
    result.loc[matched, "match_class"] = "loader_metadata_turn_match"
    input_profile = pd.to_numeric(result.get("input_sequence_length"), errors="coerce")
    input_source = pd.to_numeric(result.get("source_input_tokens"), errors="coerce")
    result["loader_metadata_turn_match"] = matched
    result["loader_metadata_input_tokens_match"] = matched & (input_profile == input_source)
    result["loader_metadata_output_tokens_match"] = matched & (
        pd.to_numeric(result.get("output_tokens"), errors="coerce")
        == pd.to_numeric(result.get("source_output_tokens"), errors="coerce")
    )
    # This is a stable source-request key used for cross-run comparisons.  It
    # intentionally includes only actual loader metadata and no timing field.
    key_values = result[["root_trace_id", "_outer_key", "_inner_key"]].astype("string")
    result["exact_source_key"] = key_values.agg("|".join, axis=1).where(matched)
    return result.drop(columns=["_outer_key", "_inner_key"], errors="ignore")


def profile_filter(frame: Any) -> tuple[Any, Any]:
    """Apply the study's successful-profiling filter and retain exclusions."""

    from .metrics import add_derived_metrics, add_request_identity_key, filter_profile_records

    included, excluded = filter_profile_records(
        frame,
        missing_phase_is_profiling=False,
        require_itl=False,
        exclude_exact_duplicates=False,
    )
    return add_derived_metrics(add_request_identity_key(included)), add_derived_metrics(
        add_request_identity_key(excluded)
    )


def summarize_requests(frame: Any, *, concurrency: int | None = None) -> dict[str, Any]:
    """Return explicit request-, token-, and wall-clock metrics for one group."""

    import pandas as pd

    group = frame.copy()
    if concurrency is not None and "concurrency" in group:
        group = group.loc[pd.to_numeric(group["concurrency"], errors="coerce") == concurrency]

    def numeric(name: str) -> Any:
        return pd.to_numeric(group.get(name, pd.Series(dtype=float)), errors="coerce")

    input_tokens = numeric("input_sequence_length")
    output_tokens = numeric("output_tokens")
    logical = numeric("logical_prompt_tokens")
    usage_prompt = numeric("usage_prompt_tokens")
    cache_read = numeric("cache_read_tokens")
    new_prompt = numeric("new_prompt_tokens")
    kv_write = numeric("kv_write_eligible_tokens")
    ttft = numeric("ttft_ms")
    itl = numeric("itl_ms")
    e2e = numeric("e2e_ms")
    span, wall_output_rate = wall_clock_span(group)
    itl_weighted = token_weighted_itl_ms(group)
    roots = group.get("root_trace_id", pd.Series(dtype="string")).dropna().astype(str).nunique()
    workers = group.get("worker_id", pd.Series(dtype="string")).dropna().astype(str).nunique()
    return {
        "profiled_request_count": int(len(group)),
        "root_id_count": int(roots),
        "worker_count_observed": int(workers),
        "input_sequence_length_total": _sum(input_tokens),
        "usage_prompt_tokens_total": _sum(usage_prompt),
        "logical_prompt_tokens_total": _sum(logical),
        "output_tokens_total": _sum(output_tokens),
        "cache_read_tokens_total": _sum(cache_read),
        "cache_read_ratio": _ratio(_sum(cache_read), _sum(logical)),
        "new_prompt_tokens_total": _sum(new_prompt),
        "kv_write_eligible_tokens_total": _sum(kv_write),
        "wall_span_s": span,
        "cumulative_request_latency_s": _sum(e2e) / 1000.0 if _sum(e2e) is not None else None,
        "logical_input_tps": _ratio(_sum(logical), span),
        "cache_load_tps": _ratio(_sum(cache_read), span),
        "new_prompt_tps": _ratio(_sum(new_prompt), span),
        "kv_write_eligible_tps": _ratio(_sum(kv_write), span),
        "wall_output_tps": wall_output_rate,
        "ttft_mean_ms": _mean(ttft),
        "ttft_median_ms": percentile(ttft, 0.5),
        "ttft_p75_ms": percentile(ttft, 0.75),
        "ttft_p90_ms": percentile(ttft, 0.9),
        "ttft_p95_ms": percentile(ttft, 0.95),
        "ttft_max_ms": _max(ttft),
        "itl_sample_count": int(((itl > 0) & (output_tokens > 1)).sum()),
        "itl_weighted_ms": itl_weighted,
        "weighted_decode_tps": _ratio(1000.0, itl_weighted),
        "itl_median_ms": percentile(itl.loc[itl > 0], 0.5),
        "itl_p90_ms": percentile(itl.loc[itl > 0], 0.9),
        "e2e_mean_ms": _mean(e2e),
        "e2e_median_ms": percentile(e2e, 0.5),
        "e2e_p90_ms": percentile(e2e, 0.9),
        "e2e_p95_ms": percentile(e2e, 0.95),
        "e2e_max_ms": _max(e2e),
        "mtp_draft_tokens_total": _sum(numeric("mtp_draft_tokens")),
        "mtp_accepted_tokens_total": _sum(numeric("mtp_accepted_tokens")),
        "mtp_acceptance_rate_mean": _mean(numeric("mtp_observed_acceptance_rate")),
        "mtp_acceptance_length_mean": _mean(numeric("mtp_acceptance_length")),
    }


def requested_id_resolution(
    frame: Any,
    *,
    source_ids: Iterable[str],
    hisparse_c8: Any | None = None,
) -> Any:
    """Resolve required full IDs/prefixes and report observation by study run."""

    import pandas as pd

    universe = {str(value) for value in source_ids if _text_or_none(value)}
    for column in ("root_trace_id", "source_trace_id"):
        if column in frame:
            universe.update(str(value) for value in frame[column].dropna() if _text_or_none(value))
    rows: list[dict[str, Any]] = []
    for label, requested, value_type in REQUESTED_IDS:
        candidates = sorted(value for value in universe if value.startswith(requested))
        status = "unique" if len(candidates) == 1 else ("ambiguous" if candidates else "not_found")
        resolved = candidates[0] if status == "unique" else None
        row: dict[str, Any] = {
            "id_label": label,
            "requested_value": requested,
            "requested_value_type": value_type,
            "resolved_full_source_trace_id": resolved,
            "resolution_match_count": len(candidates),
            "resolution_status": status,
            "candidate_full_ids": ";".join(candidates) if candidates else None,
        }
        for concurrency in (8, 12, 16):
            present = False
            if resolved and not frame.empty and "root_trace_id" in frame:
                subset = frame.loc[
                    (pd.to_numeric(frame["concurrency"], errors="coerce") == concurrency)
                    & (frame["root_trace_id"].astype("string") == resolved)
                ]
                present = not subset.empty
            row[f"present_c{concurrency}"] = present
        if resolved and hisparse_c8 is not None and not hisparse_c8.empty:
            row["present_hisparse_c8"] = bool(
                (hisparse_c8.get("root_trace_id", pd.Series(dtype="string")).astype("string") == resolved).any()
            )
        else:
            row["present_hisparse_c8"] = False
        row["notes"] = (
            "Evidence: full ID resolved by strict startswith() over source/H200 ID universe."
            if status == "unique"
            else "Unknown: no single canonical full source ID can be selected."
        )
        rows.append(row)
    return pd.DataFrame(rows)


def add_requested_id_coverage(
    resolution: Any,
    *,
    raw_all: Any,
    profiled: Any,
) -> Any:
    """Attach phase/error/success counts for every requested ID and concurrency.

    ``present_c*`` intentionally means at least one row passed the documented
    successful-profiling filter, rather than mere warmup/replay presence.  The
    adjacent raw-row counts make an ID such as ID02 (warmup-only in this run)
    visible to a reviewer without incorrectly treating it as a profiled result.
    """

    import pandas as pd

    result = resolution.copy()
    if result.empty:
        return result
    raw_roots = raw_all.get("root_trace_id", pd.Series(dtype="string")).astype("string")
    profile_roots = profiled.get("root_trace_id", pd.Series(dtype="string")).astype("string")
    raw_concurrency = pd.to_numeric(raw_all.get("concurrency"), errors="coerce")
    profile_concurrency = pd.to_numeric(profiled.get("concurrency"), errors="coerce")
    raw_phase = raw_all.get("benchmark_phase", pd.Series(dtype="string")).astype("string").str.lower()

    for index, item in result.iterrows():
        resolved = item.get("resolved_full_source_trace_id")
        for concurrency in (8, 12, 16):
            prefix = f"c{concurrency}"
            if not isinstance(resolved, str) or not resolved:
                all_group = raw_all.iloc[0:0]
                profile_group = profiled.iloc[0:0]
                phase = raw_phase.iloc[0:0]
            else:
                raw_mask = (raw_concurrency == concurrency) & (raw_roots == resolved)
                profile_mask = (profile_concurrency == concurrency) & (profile_roots == resolved)
                all_group = raw_all.loc[raw_mask]
                profile_group = profiled.loc[profile_mask]
                phase = raw_phase.loc[raw_mask]
            result.loc[index, f"all_request_count_{prefix}"] = int(len(all_group))
            result.loc[index, f"warmup_request_count_{prefix}"] = int(
                phase.isin(["warmup", "warming", "warm_up"]).sum()
            )
            result.loc[index, f"profiling_phase_count_{prefix}"] = int(
                phase.isin(["profiling", "profile"]).sum()
            )
            result.loc[index, f"successful_profile_request_count_{prefix}"] = int(len(profile_group))
            result.loc[index, f"error_count_{prefix}"] = int(
                _truthy_count(all_group.get("error_present"))
            )
            result.loc[index, f"cancellation_count_{prefix}"] = int(
                _truthy_count(all_group.get("was_cancelled"))
            )
            result.loc[index, f"present_{prefix}"] = bool(len(profile_group))
    return result


def build_pair_table(frame: Any, *, systems: Sequence[str] | None = None) -> Any:
    """Collapse repeated source-key measurements before pairwise comparisons.

    ``systems`` may be e.g. ``("gpu_resident_c8", "hisparse_c8")``.  If it
    is absent, the frame's numeric concurrency values are compared.  The
    returned unit is a source-key median, never a naively independent request.
    """

    import pandas as pd

    if frame.empty or "exact_source_key" not in frame:
        return pd.DataFrame()
    work = frame.loc[frame["exact_source_key"].notna()].copy()
    if systems is None:
        work["comparison_group"] = "conc" + work["concurrency"].astype("Int64").astype(str)
        order = sorted(work["comparison_group"].dropna().unique(), key=lambda v: int(str(v)[4:]))
    else:
        order = list(systems)
        if "comparison_group" not in work:
            raise ValueError("systems requested but comparison_group is absent")
    rows: list[dict[str, Any]] = []
    numeric_fields = ["ttft_ms", "itl_ms", "e2e_ms", "output_tokens", "input_sequence_length"]
    collapsed: list[dict[str, Any]] = []
    for (key, group_name), group in work.groupby(["exact_source_key", "comparison_group"], dropna=False):
        entry: dict[str, Any] = {
            "exact_source_key": key,
            "comparison_group": group_name,
            "root_trace_id": _first_text(group.get("root_trace_id")),
            "record_count": int(len(group)),
        }
        for field in numeric_fields:
            entry[field] = percentile(group.get(field), 0.5)
        collapsed.append(entry)
    collapsed_frame = pd.DataFrame(collapsed)
    for _, group in collapsed_frame.groupby("exact_source_key", dropna=False):
        present = {str(row["comparison_group"]): row for _, row in group.iterrows()}
        for left_index, left_name in enumerate(order):
            for right_name in order[left_index + 1 :]:
                left = present.get(left_name)
                right = present.get(right_name)
                if left is None or right is None:
                    continue
                same_output = _number(left["output_tokens"]) == _number(right["output_tokens"])
                left_itl = _number(left["itl_ms"])
                right_itl = _number(right["itl_ms"])
                rows.append(
                    {
                        "exact_source_key": left["exact_source_key"],
                        "root_trace_id": left["root_trace_id"],
                        "left_group": left_name,
                        "right_group": right_name,
                        "left_record_count": left["record_count"],
                        "right_record_count": right["record_count"],
                        "left_ttft_ms": left["ttft_ms"],
                        "right_ttft_ms": right["ttft_ms"],
                        "ttft_ratio_right_over_left": _ratio(right["ttft_ms"], left["ttft_ms"]),
                        "left_itl_ms": left_itl,
                        "right_itl_ms": right_itl,
                        "itl_ratio_right_over_left": _ratio(right_itl, left_itl),
                        "left_e2e_ms": left["e2e_ms"],
                        "right_e2e_ms": right["e2e_ms"],
                        "e2e_ratio_right_over_left": _ratio(right["e2e_ms"], left["e2e_ms"]),
                        "left_output_tokens": left["output_tokens"],
                        "right_output_tokens": right["output_tokens"],
                        "same_output_length": same_output,
                        "strict_ttft_subset": _number(left["ttft_ms"]) is not None
                        and _number(right["ttft_ms"]) is not None,
                        "strict_decode_subset": same_output
                        and left_itl is not None
                        and right_itl is not None
                        and left_itl > 0
                        and right_itl > 0,
                        "matching_method": "source_trace_id+source_outer_idx+source_inner_idx",
                    }
                )
    return pd.DataFrame(rows)


def _index_key(series: Any, *, missing: int) -> Any:
    import pandas as pd

    value = pd.to_numeric(series, errors="coerce")
    return value.fillna(missing).astype("int64")


def _number(value: Any) -> float | None:
    number = _as_number_or_none(value)
    return float(number) if number is not None else None


def _sum(series: Any) -> float | None:
    import pandas as pd

    numeric = pd.to_numeric(series, errors="coerce").dropna()
    return float(numeric.sum()) if not numeric.empty else None


def _mean(series: Any) -> float | None:
    import pandas as pd

    numeric = pd.to_numeric(series, errors="coerce").dropna()
    return float(numeric.mean()) if not numeric.empty else None


def _max(series: Any) -> float | None:
    import pandas as pd

    numeric = pd.to_numeric(series, errors="coerce").dropna()
    return float(numeric.max()) if not numeric.empty else None


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return float(numerator / denominator)


def _truthy_count(series: Any) -> int:
    if series is None:
        return 0
    return int(sum(bool(value) for value in series if _text_or_none(value) not in {None, "False", "false", "0"}))


def _text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if bool(value != value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text or None


def _first_text(series: Any) -> str | None:
    if series is None:
        return None
    for value in series:
        text = _text_or_none(value)
        if text:
            return text
    return None


def _metric_unit(flattened: Mapping[str, Any], path: str | None) -> Any | None:
    if not path:
        return None
    pieces = path.split(".")
    if pieces and pieces[-1] in {"value", "val"}:
        return flattened.get(".".join([*pieces[:-1], "unit"]))
    return None
