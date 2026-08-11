"""Conservative reconstruction helpers for public HTTP offered load.

The functions in this module reconstruct overlap in *client-observed request
intervals*.  They deliberately do not turn request overlap into an SGLang
scheduler, GPU, or queue-time measurement.  Scheduler counters must come from
explicit runtime log evidence and are represented separately.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

_TIMELINE_COLUMNS = [
    "timestamp_ns",
    "event_type",
    "event_order_at_timestamp",
    "row_position",
    "delta",
    "root_delta",
    "subagent_delta",
    "unknown_branch_delta",
    "inflight_after_event",
    "root_inflight",
    "subagent_inflight",
    "unknown_branch_inflight",
    "profiling_inflight",
]

_CONTEXT_COLUMNS = [
    "_concurrency_row_position",
    "interval_valid",
    "interval_invalid_reason",
    "branch_concurrency_group",
    "system_inflight_before_start",
    "system_inflight_at_start",
    "root_inflight_at_start",
    "subagent_inflight_at_start",
    "unknown_branch_inflight_at_start",
    "system_inflight_before_end",
    "system_inflight_after_end",
]

_STATE_COLUMNS = [
    "timestamp_ns",
    "next_timestamp_ns",
    "duration_ns",
    "inflight",
    "root_inflight",
    "subagent_inflight",
    "unknown_branch_inflight",
]


@dataclass(frozen=True)
class InflightReconstruction:
    """Output of an interval sweep.

    ``requests`` retains all input rows and adds offered-load context only for
    valid ``[request_start_ns, request_end_ns)`` intervals.  ``timeline`` is
    event-level; ``state_intervals`` is the non-overlapping representation used
    for time-weighted statistics.
    """

    requests: pd.DataFrame
    timeline: pd.DataFrame
    state_intervals: pd.DataFrame
    invalid_requests: pd.DataFrame


def reconstruct_http_inflight(
    frame: pd.DataFrame,
    *,
    start_column: str = "request_start_ns",
    end_column: str = "request_end_ns",
    branch_column: str = "source_branch_type",
) -> InflightReconstruction:
    """Reconstruct public HTTP in-flight overlap with ``[start, end)`` semantics.

    At an identical timestamp, all end events are applied before start events.
    A request's ``*_at_start`` fields are the state **after all starts at that
    timestamp**, so they include the request itself and every simultaneously
    starting request.  ``*_before_start`` is retained to make that convention
    explicit.  Neither value is an admission, queue, backend-worker, or GPU
    running-request counter.
    """

    # Preserve every source column while giving the sweep an unambiguous,
    # positional identity.  The original DataFrame index is not a stable
    # request key and may itself be named ``index``.
    requests = frame.copy().drop(columns=["_concurrency_row_position"], errors="ignore")
    requests = requests.reset_index(drop=True)
    requests.insert(0, "_concurrency_row_position", np.arange(len(requests), dtype=int))
    for column in _CONTEXT_COLUMNS[1:]:
        if column == "interval_valid":
            requests[column] = False
        elif column == "interval_invalid_reason":
            requests[column] = pd.Series(pd.NA, index=requests.index, dtype="string")
        elif column == "branch_concurrency_group":
            requests[column] = "unknown"
        else:
            requests[column] = pd.Series(pd.NA, index=requests.index, dtype="Int64")

    starts = _numeric_column(requests, start_column)
    ends = _numeric_column(requests, end_column)
    valid = starts.notna() & ends.notna() & (ends > starts)
    requests.loc[valid, "interval_valid"] = True
    requests.loc[~valid, "interval_invalid_reason"] = _interval_invalid_reason(starts, ends).loc[
        ~valid
    ]
    groups = _branch_groups(requests, branch_column)
    requests["branch_concurrency_group"] = groups

    if not valid.any():
        return InflightReconstruction(
            requests=requests,
            timeline=pd.DataFrame(columns=_TIMELINE_COLUMNS),
            state_intervals=pd.DataFrame(columns=_STATE_COLUMNS),
            invalid_requests=requests.loc[~valid].copy(),
        )

    valid_requests = requests.loc[valid].copy()
    valid_requests["_start_ns"] = starts.loc[valid].astype("int64")
    valid_requests["_end_ns"] = ends.loc[valid].astype("int64")
    events = _event_frame(valid_requests)
    timeline_rows: list[dict[str, Any]] = []
    state_rows: list[dict[str, Any]] = []
    counts = {"all": 0, "root": 0, "subagent": 0, "unknown": 0}

    for timestamp, event_group in events.groupby("timestamp_ns", sort=True):
        ends_at_timestamp = event_group.loc[event_group["event_type"] == "end"].sort_values(
            "row_position"
        )
        starts_at_timestamp = event_group.loc[event_group["event_type"] == "start"].sort_values(
            "row_position"
        )

        end_after_by_position: dict[int, int] = {}
        for event_order, event in enumerate(ends_at_timestamp.itertuples(index=False)):
            _apply_event(counts, event)
            end_after_by_position[int(event.row_position)] = counts["all"]
            timeline_rows.append(_timeline_row(timestamp, "end", event_order, event, counts))

        start_state_before = counts.copy()
        start_event_offset = len(ends_at_timestamp)
        for offset, event in enumerate(starts_at_timestamp.itertuples(index=False)):
            _apply_event(counts, event)
            timeline_rows.append(
                _timeline_row(timestamp, "start", start_event_offset + offset, event, counts)
            )

        # Assign one deterministic context to every request that starts at this
        # timestamp.  This avoids arbitrary results from order within a burst
        # of exactly simultaneous starts.
        for event in starts_at_timestamp.itertuples(index=False):
            position = int(event.row_position)
            requests.loc[position, "system_inflight_before_start"] = start_state_before["all"]
            requests.loc[position, "system_inflight_at_start"] = counts["all"]
            requests.loc[position, "root_inflight_at_start"] = counts["root"]
            requests.loc[position, "subagent_inflight_at_start"] = counts["subagent"]
            requests.loc[position, "unknown_branch_inflight_at_start"] = counts["unknown"]

        # End context is intentionally event-local because same-timestamp end
        # events are ordered deterministically.  It is not used as a scheduler
        # sample, but gives downstream consumers an explicit endpoint meaning.
        for event in ends_at_timestamp.itertuples(index=False):
            position = int(event.row_position)
            after = end_after_by_position.get(position, pd.NA)
            requests.loc[position, "system_inflight_after_end"] = after
            requests.loc[position, "system_inflight_before_end"] = (
                int(after) + 1 if pd.notna(after) else pd.NA
            )

        state_rows.append(
            {
                "timestamp_ns": int(timestamp),
                "inflight": counts["all"],
                "root_inflight": counts["root"],
                "subagent_inflight": counts["subagent"],
                "unknown_branch_inflight": counts["unknown"],
            }
        )

    timeline = pd.DataFrame(timeline_rows, columns=_TIMELINE_COLUMNS)
    states = pd.DataFrame(state_rows)
    state_intervals = _state_intervals(states)
    return InflightReconstruction(
        requests=requests,
        timeline=timeline,
        state_intervals=state_intervals,
        invalid_requests=requests.loc[~valid].copy(),
    )


def summarize_http_inflight(reconstruction: InflightReconstruction) -> dict[str, Any]:
    """Return explicitly time-weighted and request-start-sampled HTTP overlap metrics."""

    intervals = reconstruction.state_intervals.copy()
    requests = reconstruction.requests
    valid_count = int(requests["interval_valid"].sum())
    invalid_count = int((~requests["interval_valid"]).sum())
    summary: dict[str, Any] = {
        "valid_interval_request_count": valid_count,
        "invalid_interval_request_count": invalid_count,
        "http_inflight_metric_scope": "HTTP request interval overlap; not scheduler running",
    }
    if intervals.empty or valid_count == 0:
        summary.update(_unknown_time_weighted_summary())
        return summary

    durations = pd.to_numeric(intervals["duration_ns"], errors="coerce")
    positive = durations > 0
    intervals = intervals.loc[positive].copy()
    if intervals.empty:
        summary.update(_unknown_time_weighted_summary())
        return summary

    total_duration = float(intervals["duration_ns"].sum())
    summary["observation_span_s"] = total_duration / 1e9
    for prefix, column in (
        ("", "inflight"),
        ("root_", "root_inflight"),
        ("subagent_", "subagent_inflight"),
        ("unknown_branch_", "unknown_branch_inflight"),
    ):
        values = pd.to_numeric(intervals[column], errors="coerce")
        summary[f"max_{prefix}inflight"] = int(values.max())
        summary[f"time_weighted_mean_{prefix}inflight"] = _time_weighted_mean(
            values, intervals["duration_ns"]
        )
        for quantile, suffix in ((0.50, "p50"), (0.75, "p75"), (0.90, "p90"), (0.95, "p95"), (0.99, "p99")):
            summary[f"time_weighted_{suffix}_{prefix}inflight"] = time_weighted_quantile(
                values, intervals["duration_ns"], quantile
            )

    values = pd.to_numeric(intervals["inflight"], errors="coerce")
    for threshold in (8, 12, 16, 24, 32):
        summary[f"fraction_time_inflight_ge_{threshold}"] = float(
            intervals.loc[values >= threshold, "duration_ns"].sum() / total_duration
        )

    start_samples = pd.to_numeric(
        requests.loc[requests["interval_valid"], "system_inflight_at_start"], errors="coerce"
    ).dropna()
    if not start_samples.empty:
        summary["request_start_sampled_mean_inflight"] = float(start_samples.mean())
        for quantile, suffix in ((0.50, "p50"), (0.75, "p75"), (0.90, "p90"), (0.95, "p95")):
            summary[f"request_start_sampled_{suffix}_inflight"] = float(
                start_samples.quantile(quantile)
            )
    return summary


def time_weighted_quantile(
    values: Sequence[float] | pd.Series,
    durations: Sequence[float] | pd.Series,
    quantile: float,
) -> float | None:
    """Return the lower weighted quantile over piecewise-constant intervals.

    The result is the first value whose cumulative positive duration reaches
    ``quantile * total_duration``.  This definition is deterministic and does
    not interpolate a concurrency count that was never observed.
    """

    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be between 0 and 1")
    work = pd.DataFrame(
        {
            "value": pd.to_numeric(pd.Series(values), errors="coerce"),
            "duration": pd.to_numeric(pd.Series(durations), errors="coerce"),
        }
    ).dropna()
    work = work.loc[work["duration"] > 0].sort_values("value")
    if work.empty:
        return None
    total = float(work["duration"].sum())
    target = total * quantile
    cumulative = work["duration"].cumsum().to_numpy(dtype=float)
    position = int(np.searchsorted(cumulative, target, side="left"))
    position = min(position, len(work) - 1)
    return float(work.iloc[position]["value"])


def parse_scheduler_counter_line(line: str) -> list[dict[str, Any]]:
    """Extract explicit numeric scheduler-looking fields from one log line.

    A ``max_*`` field is evidence for a configured capacity, not evidence that
    the corresponding runtime count was observed.  Returned rows make that
    distinction machine-readable through ``is_observed_runtime_counter``.
    The caller still needs to establish worker/component and timestamp scope.
    """

    normalized = line.strip()
    if not normalized:
        return []
    candidates: list[dict[str, Any]] = []
    for pattern, name, scope, observed in _SCHEDULER_COUNTER_PATTERNS:
        for match in pattern.finditer(normalized):
            value = _parse_number(match.group("value"))
            if value is None:
                continue
            candidates.append(
                {
                    "candidate_metric_name": name,
                    "value": value,
                    "metric_scope_interpretation": scope,
                    "is_observed_runtime_counter": observed,
                    "classification": "Evidence",
                }
            )
    return _deduplicate_candidates(candidates)


def observed_scheduler_counter_summary(
    candidates: pd.DataFrame | Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Summarize only explicit runtime counters, leaving missing values Unknown.

    Configured limits intentionally do not fill the observed fields.  This is
    used by reports to avoid a common error: treating ``max_running_requests``
    as an observed runtime scheduler count.
    """

    frame = pd.DataFrame(candidates)
    result: dict[str, Any] = {}
    for metric, prefix in (("running_requests", "running"), ("waiting_requests", "waiting")):
        matched = frame.loc[
            (frame.get("candidate_metric_name", pd.Series(dtype="string")) == metric)
            & frame.get(
                "is_observed_runtime_counter", pd.Series(False, index=frame.index)
            ).fillna(False)
        ]
        values = pd.to_numeric(matched.get("value", pd.Series(dtype=float)), errors="coerce").dropna()
        if values.empty:
            result[f"observed_{prefix}_metric_available"] = "no"
            result[f"max_observed_{prefix}"] = None
            result[f"observed_{prefix}_status"] = "Unknown"
        else:
            result[f"observed_{prefix}_metric_available"] = "yes"
            result[f"max_observed_{prefix}"] = float(values.max())
            result[f"observed_{prefix}_status"] = "Evidence"
    return result


def _numeric_column(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    values = pd.to_numeric(frame[column], errors="coerce")
    return values.where(np.isfinite(values))


def _interval_invalid_reason(starts: pd.Series, ends: pd.Series) -> pd.Series:
    reason = pd.Series(pd.NA, index=starts.index, dtype="string")
    reason = reason.mask(starts.isna(), "missing_request_start_ns")
    reason = reason.mask(reason.isna() & ends.isna(), "missing_request_end_ns")
    reason = reason.mask(reason.isna() & (ends <= starts), "nonpositive_request_interval")
    return reason.fillna("invalid_request_interval")


def _branch_groups(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series("unknown", index=frame.index, dtype="string")
    branch = frame[column].astype("string").str.strip().str.lower()
    groups = pd.Series("subagent", index=frame.index, dtype="string")
    groups = groups.mask(branch.isna() | (branch == ""), "unknown")
    groups = groups.mask(branch == "root", "root")
    return groups


def _event_frame(valid_requests: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    # ``itertuples`` sanitizes leading-underscore columns, which would make a
    # request identity field ambiguous.  The input here is tiny relative to
    # raw profile parsing, so record dictionaries are clearer and stable.
    for request in valid_requests.to_dict(orient="records"):
        position = int(request["_concurrency_row_position"])
        group = str(request["branch_concurrency_group"])
        root_delta = 1 if group == "root" else 0
        subagent_delta = 1 if group == "subagent" else 0
        unknown_delta = 1 if group == "unknown" else 0
        for event_type, timestamp, sign in (
            ("start", int(request["_start_ns"]), 1),
            ("end", int(request["_end_ns"]), -1),
        ):
            rows.append(
                {
                    "timestamp_ns": timestamp,
                    "event_type": event_type,
                    "row_position": position,
                    "delta": sign,
                    "root_delta": sign * root_delta,
                    "subagent_delta": sign * subagent_delta,
                    "unknown_branch_delta": sign * unknown_delta,
                }
            )
    return pd.DataFrame(rows)


def _apply_event(counts: dict[str, int], event: Any) -> None:
    counts["all"] += int(event.delta)
    counts["root"] += int(event.root_delta)
    counts["subagent"] += int(event.subagent_delta)
    counts["unknown"] += int(event.unknown_branch_delta)
    if any(value < 0 for value in counts.values()):
        raise ValueError("interval sweep produced a negative in-flight count")


def _timeline_row(
    timestamp: int,
    event_type: str,
    event_order: int,
    event: Any,
    counts: Mapping[str, int],
) -> dict[str, Any]:
    return {
        "timestamp_ns": int(timestamp),
        "event_type": event_type,
        "event_order_at_timestamp": event_order,
        "row_position": int(event.row_position),
        "delta": int(event.delta),
        "root_delta": int(event.root_delta),
        "subagent_delta": int(event.subagent_delta),
        "unknown_branch_delta": int(event.unknown_branch_delta),
        "inflight_after_event": counts["all"],
        "root_inflight": counts["root"],
        "subagent_inflight": counts["subagent"],
        "unknown_branch_inflight": counts["unknown"],
        "profiling_inflight": counts["all"],
    }


def _state_intervals(states: pd.DataFrame) -> pd.DataFrame:
    if states.empty:
        return pd.DataFrame(columns=_STATE_COLUMNS)
    result = states.copy()
    result["next_timestamp_ns"] = result["timestamp_ns"].shift(-1)
    result["duration_ns"] = result["next_timestamp_ns"] - result["timestamp_ns"]
    result = result.loc[result["duration_ns"].notna()].copy()
    result["duration_ns"] = result["duration_ns"].astype("int64")
    return result[_STATE_COLUMNS]


def _time_weighted_mean(values: pd.Series, durations: pd.Series) -> float | None:
    value_array = pd.to_numeric(values, errors="coerce")
    duration_array = pd.to_numeric(durations, errors="coerce")
    valid = value_array.notna() & duration_array.notna() & (duration_array > 0)
    if not valid.any():
        return None
    return float(np.average(value_array.loc[valid], weights=duration_array.loc[valid]))


def _unknown_time_weighted_summary() -> dict[str, Any]:
    return {
        "observation_span_s": None,
        "max_inflight": None,
        "time_weighted_mean_inflight": None,
        "time_weighted_p50_inflight": None,
        "time_weighted_p75_inflight": None,
        "time_weighted_p90_inflight": None,
        "time_weighted_p95_inflight": None,
        "time_weighted_p99_inflight": None,
    }


def _parse_number(value: str) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _deduplicate_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for candidate in candidates:
        key = (
            candidate["candidate_metric_name"],
            candidate["value"],
            candidate["is_observed_runtime_counter"],
        )
        if key not in seen:
            unique.append(candidate)
            seen.add(key)
    return unique


def _regex(expression: str) -> re.Pattern[str]:
    return re.compile(expression, flags=re.IGNORECASE)


_SCHEDULER_COUNTER_PATTERNS: tuple[tuple[re.Pattern[str], str, str, bool], ...] = (
    (
        _regex(r"\bmax[_ -]?running[_ -]?(?:reqs|requests)\s*[:=]\s*(?P<value>[-+]?\d+(?:\.\d+)?)"),
        "configured_max_running_requests",
        "configured capacity; not an observed runtime scheduler count",
        False,
    ),
    (
        _regex(r"\bmax[_ -]?waiting[_ -]?(?:reqs|requests)\s*[:=]\s*(?P<value>[-+]?\d+(?:\.\d+)?)"),
        "configured_max_waiting_requests",
        "configured capacity; not an observed runtime scheduler count",
        False,
    ),
    (
        _regex(r"(?<!max_)(?<!max-)(?<!max )\b(?:num[_ -]?)?running[_ -]?(?:reqs|requests)\s*[:=]\s*(?P<value>[-+]?\d+(?:\.\d+)?)"),
        "running_requests",
        "explicit runtime log counter; component/timestamp scope must be retained",
        True,
    ),
    (
        _regex(r"(?<!max_)(?<!max-)(?<!max )\b(?:num[_ -]?)?waiting[_ -]?(?:reqs|requests)\s*[:=]\s*(?P<value>[-+]?\d+(?:\.\d+)?)"),
        "waiting_requests",
        "explicit runtime log counter; component/timestamp scope must be retained",
        True,
    ),
    (
        _regex(r"\bbatch[_ -]?size\s*[:=]\s*(?P<value>[-+]?\d+(?:\.\d+)?)"),
        "batch_size",
        "explicit runtime log batch-size field; not necessarily scheduler request count",
        True,
    ),
    (
        _regex(r"\b(?:num[_ -]?)?tokens?\s*[:=]\s*(?P<value>[-+]?\d+(?:\.\d+)?)"),
        "token_load",
        "explicit runtime log token field; semantic scope requires source inspection",
        True,
    ),
    (
        _regex(r"\btoken[_ -]?usage\s*[:=]\s*(?P<value>[-+]?\d+(?:\.\d+)?)"),
        "token_usage",
        "explicit runtime log token-usage field; semantic scope requires source inspection",
        True,
    ),
)
