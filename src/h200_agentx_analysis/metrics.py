"""Filtering, duplicate handling, and clearly named request-level metrics."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

PROFILE_PHASES = {"profiling", "profile"}


def add_request_identity_key(frame: Any) -> Any:
    """Add the non-lossy request identity specified for replayed requests.

    ``conversation_id + turn_index`` is deliberately not sufficient: the same
    turn may appear in multiple replay sessions or be recorded repeatedly.
    """

    result = frame.copy()
    columns = [
        "github_run_id",
        "concurrency",
        "artifact_id",
        "session_num",
        "conversation_id",
        "turn_index",
        "request_start_ns",
        "record_ordinal",
    ]
    _ensure_columns(result, columns)
    result["request_identity_key"] = (
        result[columns].astype("string").fillna("<null>").agg("|".join, axis=1)
    )
    return result


def exact_duplicate_mask(frame: Any) -> Any:
    """Return a boolean mask only for fully identical measurement duplicates.

    Replay instances, sessions, artifact IDs, request start times, and distinct
    metric values participate in the comparison.  We intentionally ignore only
    the local record ordinal and parser bookkeeping fields, because a duplicate
    line naturally has a different ordinal.
    """

    if frame.empty:
        return frame.index.to_series().astype(bool)
    columns = _duplicate_columns(frame)
    if not columns:
        return frame.index.to_series().astype(bool)
    return frame.duplicated(subset=columns, keep="first")


def exact_duplicate_fingerprints(frame: Any) -> Any:
    """Create stable full-record fingerprints for duplicate checks across batches.

    The same comparisons as :func:`exact_duplicate_mask` are used, but a hash
    allows the streaming profile builder to recognize a duplicate split across
    two Parquet row groups without retaining request objects in memory.
    """

    import pandas as pd

    columns = _duplicate_columns(frame)
    if not columns:
        return pd.Series([None] * len(frame), index=frame.index, dtype="object")
    values: list[str] = []
    for row in frame[columns].itertuples(index=False, name=None):
        canonical = [None if _is_missing(value) else _scalar_for_hash(value) for value in row]
        encoded = json.dumps(canonical, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
        values.append(hashlib.sha256(encoded.encode("utf-8")).hexdigest())
    return pd.Series(values, index=frame.index, dtype="object")


def filter_profile_records(
    frame: Any,
    *,
    require_phase: bool = True,
    missing_phase_is_profiling: bool = True,
    require_itl: bool = False,
    exclude_exact_duplicates: bool = False,
) -> tuple[Any, Any]:
    """Apply the explicit main-analysis profiling filter.

    Included records must be profiling records, successful, not cancelled, have
    non-negative token counts, and have positive TTFT and E2E latency.  For
    compatibility with the pinned InferenceX aggregation source, a missing
    phase is treated as a legacy profiling row by default; callers that need a
    strict ``benchmark_phase == profiling`` denominator can disable this with
    ``missing_phase_is_profiling=False``. ITL is not required for a one-token
    response because an inter-token interval is undefined there. The returned
    exclusion table retains every rejected row and its first applicable reason.
    """

    import pandas as pd

    result = frame.copy()
    required = [
        "benchmark_phase",
        "error_present",
        "was_cancelled",
        "input_tokens",
        "output_tokens",
        "ttft_ms",
        "e2e_ms",
        "itl_ms",
    ]
    _ensure_columns(result, required)
    for column in ("input_tokens", "output_tokens", "ttft_ms", "e2e_ms", "itl_ms"):
        result[column] = pd.to_numeric(result[column], errors="coerce")

    phase = result["benchmark_phase"].astype("string").str.strip().str.lower()
    error = _coerce_bool_series(result["error_present"])
    cancelled = _coerce_bool_series(result["was_cancelled"])
    reasons = pd.Series(pd.NA, index=result.index, dtype="string")
    if require_phase:
        phase_missing = result["benchmark_phase"].isna() | (phase == "")
        if not missing_phase_is_profiling:
            reasons = reasons.mask(phase_missing, "missing_benchmark_phase")
        nonprofiling = ~phase.isin(PROFILE_PHASES)
        if missing_phase_is_profiling:
            nonprofiling = nonprofiling & ~phase_missing
        reasons = reasons.mask(reasons.isna() & nonprofiling, "not_profiling_phase")
    reasons = reasons.mask(reasons.isna() & error.fillna(False), "error_present")
    reasons = reasons.mask(reasons.isna() & cancelled.fillna(False), "was_cancelled")
    reasons = reasons.mask(
        reasons.isna() & (result["input_tokens"].isna() | result["output_tokens"].isna()),
        "missing_token_count",
    )
    reasons = reasons.mask(
        reasons.isna() & ((result["input_tokens"] < 0) | (result["output_tokens"] < 0)),
        "negative_token_count",
    )
    reasons = reasons.mask(reasons.isna() & result["ttft_ms"].isna(), "missing_ttft")
    reasons = reasons.mask(reasons.isna() & (result["ttft_ms"] <= 0), "nonpositive_ttft")
    reasons = reasons.mask(reasons.isna() & result["e2e_ms"].isna(), "missing_e2e")
    reasons = reasons.mask(reasons.isna() & (result["e2e_ms"] <= 0), "nonpositive_e2e")
    if require_itl:
        needs_itl = result["output_tokens"] > 1
        reasons = reasons.mask(reasons.isna() & needs_itl & result["itl_ms"].isna(), "missing_itl")
        reasons = reasons.mask(
            reasons.isna() & needs_itl & (result["itl_ms"] <= 0), "nonpositive_itl"
        )

    duplicate = exact_duplicate_mask(result)
    if exclude_exact_duplicates:
        reasons = reasons.mask(reasons.isna() & duplicate, "exact_duplicate")
    result["is_exact_duplicate"] = duplicate.astype(bool)
    result["exclusion_reason"] = reasons
    result["is_profiled_valid"] = reasons.isna()
    included = result.loc[result["is_profiled_valid"]].copy()
    excluded = result.loc[~result["is_profiled_valid"]].copy()
    return included, excluded


def add_derived_metrics(frame: Any) -> Any:
    """Add only request-level derived metrics whose units and caveats are explicit."""

    import numpy as np
    import pandas as pd

    result = frame.copy()
    _ensure_columns(result, ["input_tokens", "output_tokens", "ttft_ms", "e2e_ms", "itl_ms"])
    for column in ("input_tokens", "output_tokens", "ttft_ms", "e2e_ms", "itl_ms"):
        result[column] = pd.to_numeric(result[column], errors="coerce")

    result["ttft_s"] = result["ttft_ms"] / 1000.0
    result["e2e_s"] = result["e2e_ms"] / 1000.0
    raw_post_ttft_ms = result["e2e_ms"] - result["ttft_ms"]
    result["post_ttft_s"] = raw_post_ttft_ms.clip(lower=0) / 1000.0
    result["ttft_exceeds_e2e"] = (raw_post_ttft_ms < 0).fillna(False)

    valid_itl = (result["itl_ms"] > 0) & (result["output_tokens"] > 1)
    result["observed_itl_implied_tps"] = np.where(valid_itl, 1000.0 / result["itl_ms"], np.nan)
    valid_post = (result["output_tokens"] > 1) & (result["post_ttft_s"] > 0)
    result["post_ttft_tps"] = np.where(
        valid_post,
        (result["output_tokens"] - 1) / result["post_ttft_s"],
        np.nan,
    )
    valid_e2e = (result["output_tokens"] >= 0) & (result["e2e_s"] > 0)
    result["e2e_output_tps"] = np.where(
        valid_e2e,
        result["output_tokens"] / result["e2e_s"],
        np.nan,
    )
    valid_ttft = (result["input_tokens"] >= 0) & (result["ttft_s"] > 0)
    result["input_tokens_per_observed_ttft_s"] = np.where(
        valid_ttft,
        result["input_tokens"] / result["ttft_s"],
        np.nan,
    )
    return result


def token_weighted_itl_ms(frame: Any) -> float | None:
    """Compute ITL weighted by output-token intervals, not request count."""

    import pandas as pd

    if frame.empty or "itl_ms" not in frame or "output_tokens" not in frame:
        return None
    itl = pd.to_numeric(frame["itl_ms"], errors="coerce")
    intervals = pd.to_numeric(frame["output_tokens"], errors="coerce") - 1
    valid = (itl > 0) & (intervals > 0)
    if not valid.any():
        return None
    weight_sum = intervals[valid].sum()
    if weight_sum <= 0:
        return None
    return float((itl[valid] * intervals[valid]).sum() / weight_sum)


def percentile(series: Any, q: float) -> float | None:
    """Pandas linear percentile with an explicit empty/null result."""

    import pandas as pd

    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return None
    return float(values.quantile(q, interpolation="linear"))


def wall_clock_span(frame: Any) -> tuple[float | None, float | None]:
    """Return wall span seconds and wall-clock output rate for a request group."""

    import pandas as pd

    if frame.empty or "request_start_ns" not in frame or "request_end_ns" not in frame:
        return None, None
    starts = pd.to_numeric(frame["request_start_ns"], errors="coerce").dropna()
    ends = pd.to_numeric(frame["request_end_ns"], errors="coerce").dropna()
    if starts.empty or ends.empty:
        return None, None
    span = (ends.max() - starts.min()) / 1_000_000_000.0
    if span <= 0:
        return float(span), None
    output_series = frame["output_tokens"] if "output_tokens" in frame else pd.Series(dtype=float)
    total_output = pd.to_numeric(output_series, errors="coerce").fillna(0).sum()
    return float(span), float(total_output / span)


def _coerce_bool_series(series: Any) -> Any:
    import pandas as pd

    if str(series.dtype) == "boolean":
        return series
    normalized = series.astype("string").str.strip().str.lower()
    result = pd.Series(pd.NA, index=series.index, dtype="boolean")
    result = result.mask(normalized.isin(["true", "1", "yes", "y"]), True)
    result = result.mask(normalized.isin(["false", "0", "no", "n", "", "none", "null"]), False)
    numeric = pd.to_numeric(series, errors="coerce")
    result = result.mask(result.isna() & numeric.notna(), numeric.astype("boolean"))
    return result


def _ensure_columns(frame: Any, columns: Sequence[str]) -> None:
    for column in columns:
        if column not in frame.columns:
            frame[column] = None


def _duplicate_columns(frame: Any) -> list[str]:
    ignored_prefixes = ("raw_",)
    ignored_exact = {
        "record_ordinal",
        "source_file_path",
        "request_identity_key",
        "exclusion_reason",
        "is_profiled_valid",
        "is_exact_duplicate",
    }
    return [
        column
        for column in frame.columns
        if column not in ignored_exact and not column.startswith(ignored_prefixes)
    ]


def _is_missing(value: Any) -> bool:
    if value is None or type(value).__name__ == "NAType":
        return True
    try:
        return bool(value != value)
    except (TypeError, ValueError):
        return False


def _scalar_for_hash(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            return str(value)
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
