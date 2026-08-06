"""Utilities for inventorying GitHub benchmark artifacts and profile exports.

The raw Action artifacts are deliberately treated as untrusted input.  The
functions in this module do not make assumptions about a particular archive
layout and only use fields which are present in a profile record.  This makes
the acquisition and parsing stages useful both for the public run and for a
future re-run of the workflow.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from numbers import Integral
from pathlib import Path
from typing import Any

RAW_CATEGORY = "raw_agentic"
AGGREGATE_CATEGORY = "aggregated_agentic"
SERVER_LOG_CATEGORY = "server_log"
RUN_SUMMARY_CATEGORY = "run_summary"
OTHER_CATEGORY = "other"


@dataclass(frozen=True)
class ArtifactInfo:
    """The small, stable subset of GitHub artifact metadata used downstream."""

    artifact_id: str
    name: str
    category: str
    concurrency: int | None
    size_in_bytes: int | None = None
    digest: str | None = None
    expired: bool | None = None
    created_at: str | None = None
    expires_at: str | None = None
    head_sha: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class JsonlIssue:
    """A malformed JSONL line discovered while streaming a profile export."""

    path: str
    line_number: int
    message: str


_CONCURRENCY_PATTERNS = (
    # Most workflow artifact names use e.g. ``..._conc1_...``.
    re.compile(r"(?<![a-z0-9])(?:conc(?:urrency)?|concurrent)[_.-]?(\d+)(?!\d)", re.I),
    # Also accept ``..._1conc...`` / ``..._1_concurrency...``.
    re.compile(r"(?<![a-z0-9])(\d+)[_.-]?(?:conc(?:urrency)?|concurrent)(?![a-z0-9])", re.I),
    # A short ``c8`` is accepted only where it is a standalone name token.
    re.compile(r"(?:^|[_.-])c[_.-]?(\d+)(?:$|[_.-])", re.I),
)


def artifact_category(name: str | None) -> str:
    """Classify an artifact name without relying on its expected ID.

    ``bmk_agentic`` must be tested before ``agentic``: otherwise aggregate
    artifacts would accidentally be treated as raw request records.
    """

    normalized = (name or "").strip().lower().replace("-", "_")
    if re.search(r"(?:^|_)bmk_?agentic(?:_|$)", normalized):
        return AGGREGATE_CATEGORY
    if re.search(r"(?:^|_)agentic(?:_|$)", normalized):
        return RAW_CATEGORY
    if "server" in normalized and ("log" in normalized or "logs" in normalized):
        return SERVER_LOG_CATEGORY
    if (
        normalized in {"results_bmk", "run_stats", "run-stats"}
        or "results_bmk" in normalized
        or "run_stats" in normalized
        or "run-stats" in normalized
    ):
        return RUN_SUMMARY_CATEGORY
    return OTHER_CATEGORY


def parse_concurrency(name: str | None) -> int | None:
    """Return the explicit concurrency encoded in an artifact name, if any."""

    if not name:
        return None
    text = str(name).strip()
    values: set[int] = set()
    for pattern in _CONCURRENCY_PATTERNS:
        for match in pattern.finditer(text):
            value = int(match.group(1))
            if value > 0:
                values.add(value)
    # Conflicting numbers are ambiguous.  It is safer to leave it unparsed
    # than assign an artifact to a wrong benchmark column.
    if len(values) != 1:
        return None
    return next(iter(values))


def parse_artifact(item: Mapping[str, Any]) -> ArtifactInfo:
    """Convert a GitHub REST artifact object to :class:`ArtifactInfo`."""

    workflow_run = item.get("workflow_run") or {}
    artifact_id = item.get("id", item.get("artifact_id", ""))
    name = str(item.get("name", ""))
    return ArtifactInfo(
        artifact_id=str(artifact_id),
        name=name,
        category=artifact_category(name),
        concurrency=parse_concurrency(name),
        size_in_bytes=_as_int_or_none(item.get("size_in_bytes")),
        digest=_as_str_or_none(item.get("digest")),
        expired=_as_bool_or_none(item.get("expired")),
        created_at=_as_str_or_none(item.get("created_at")),
        expires_at=_as_str_or_none(item.get("expires_at")),
        head_sha=_as_str_or_none(workflow_run.get("head_sha") or item.get("head_sha")),
    )


def parse_artifact_inventory(
    payload: Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> list[ArtifactInfo]:
    """Parse either GitHub's paginated response object or its ``artifacts`` list."""

    if isinstance(payload, Mapping):
        artifacts = payload.get("artifacts", [])
    else:
        artifacts = payload
    if not isinstance(artifacts, Sequence):
        raise ValueError("GitHub artifact inventory has no list-valued 'artifacts' field")
    return [parse_artifact(item) for item in artifacts if isinstance(item, Mapping)]


def duplicate_artifacts(
    artifacts: Iterable[ArtifactInfo],
) -> dict[tuple[str, int], list[ArtifactInfo]]:
    """Return duplicate raw/aggregate artifacts keyed by category and concurrency."""

    grouped: dict[tuple[str, int], list[ArtifactInfo]] = defaultdict(list)
    for artifact in artifacts:
        if (
            artifact.category in {RAW_CATEGORY, AGGREGATE_CATEGORY}
            and artifact.concurrency is not None
        ):
            grouped[(artifact.category, artifact.concurrency)].append(artifact)
    return {key: values for key, values in grouped.items() if len(values) > 1}


def artifact_index(artifacts: Iterable[ArtifactInfo]) -> dict[str, ArtifactInfo]:
    """Create an ID index and fail loudly on contradictory inventory data."""

    index: dict[str, ArtifactInfo] = {}
    for artifact in artifacts:
        previous = index.get(artifact.artifact_id)
        if previous is not None and previous != artifact:
            raise ValueError(f"conflicting metadata for artifact ID {artifact.artifact_id}")
        index[artifact.artifact_id] = artifact
    return index


def load_artifact_inventory(path: str | Path) -> list[ArtifactInfo]:
    """Load a saved GitHub inventory; a missing file simply means no inventory."""

    source = Path(path)
    if not source.exists():
        return []
    with source.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return parse_artifact_inventory(payload)


def find_profile_exports(raw_root: str | Path) -> list[Path]:
    """Find profile exports below a raw download root in deterministic order."""

    root = Path(raw_root)
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("profile_export.jsonl")
        if path.is_file() and not path.name.startswith(".")
    )


def iter_jsonl_records(
    path: str | Path,
    *,
    issues: list[JsonlIssue] | None = None,
    strict: bool = False,
) -> Iterator[tuple[int, Mapping[str, Any]]]:
    """Stream JSON objects from a JSONL file.

    A single malformed line does not invalidate a large public artifact.  In
    normal mode it is recorded in ``issues`` and skipped.  ``strict=True`` is
    useful for tests or forensic inspection.
    """

    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                issue = JsonlIssue(str(source), line_number, f"invalid JSON: {exc.msg}")
                if strict:
                    raise ValueError(f"{issue.path}:{issue.line_number}: {issue.message}") from exc
                if issues is not None:
                    issues.append(issue)
                continue
            if not isinstance(value, Mapping):
                issue = JsonlIssue(str(source), line_number, "record is not a JSON object")
                if strict:
                    raise ValueError(f"{issue.path}:{issue.line_number}: {issue.message}")
                if issues is not None:
                    issues.append(issue)
                continue
            yield line_number, value


def flatten_record(value: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten scalar fields in a nested profile object using dot-separated paths."""

    flattened: dict[str, Any] = {}
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(flatten_record(child, child_prefix))
    elif isinstance(value, list):
        # Lists are not expected for scalar benchmark metrics.  Preserve them
        # as a compact JSON value instead of exploding a potentially huge row.
        flattened[prefix] = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        flattened[prefix] = value
    return flattened


def canonical_field_name(name: str) -> str:
    """Normalize field names for alias matching (case/punctuation insensitive)."""

    return re.sub(r"[^a-z0-9]+", "", name.lower())


def lookup_flat_value(
    flattened: Mapping[str, Any], aliases: Sequence[str]
) -> tuple[Any | None, str | None]:
    """Find a profile value by an ordered list of aliases.

    Exact paths win, then terminal field names, then common ``.value`` metric
    wrappers.  Returning the matched path is important for unit inference and
    future schema audits.
    """

    entries = list(flattened.items())
    for alias in aliases:
        normalized_alias = canonical_field_name(alias)
        for path, value in entries:
            if canonical_field_name(path) == normalized_alias:
                return value, path
        for path, value in entries:
            terminal = path.rsplit(".", 1)[-1]
            if canonical_field_name(terminal) == normalized_alias:
                return value, path
        for path, value in entries:
            parts = path.split(".")
            if len(parts) >= 2 and canonical_field_name(parts[-1]) in {"value", "val"}:
                if canonical_field_name(parts[-2]) == normalized_alias:
                    return value, path
    return None, None


def infer_profile_context(
    profile_path: str | Path, artifacts: Sequence[ArtifactInfo]
) -> ArtifactInfo | None:
    """Best-effort match from an extracted file path to inventory metadata.

    GitHub's ``gh run download`` changes archive layout across versions.  A
    path can still be reliably associated when an artifact name or its ID is a
    directory component; otherwise this function only returns an unambiguous
    raw artifact with the same encoded concurrency.
    """

    path = Path(profile_path)
    components = [part.lower() for part in path.parts]
    raw_artifacts = [item for item in artifacts if item.category == RAW_CATEGORY]
    for artifact in raw_artifacts:
        artifact_name = artifact.name.lower()
        if artifact_name in components or artifact.artifact_id in components:
            return artifact
        if any(artifact.artifact_id in component for component in components):
            return artifact

    candidate_concurrencies: set[int] = set()
    for component in components:
        parsed = parse_concurrency(component)
        if parsed is not None:
            candidate_concurrencies.add(parsed)
        match = re.fullmatch(r"conc(?:urrency)?[_-]?(\d+)", component, flags=re.I)
        if match:
            candidate_concurrencies.add(int(match.group(1)))
    if len(candidate_concurrencies) != 1:
        return None
    candidates = [
        artifact
        for artifact in raw_artifacts
        if artifact.concurrency == next(iter(candidate_concurrencies))
    ]
    return candidates[0] if len(candidates) == 1 else None


def normalize_profile_record(
    record: Mapping[str, Any],
    *,
    context: Mapping[str, Any] | None = None,
    source_file: str | None = None,
    record_ordinal: int | None = None,
) -> dict[str, Any]:
    """Extract a canonical H200 request row from an arbitrary profile record.

    This intentionally preserves missing values as ``None``.  Filtering and
    metric derivation happen later, so schema differences or failed records
    cannot silently disappear during parsing.
    """

    flattened = flatten_record(record)

    def get(*aliases: str) -> Any | None:
        return lookup_flat_value(flattened, aliases)[0]

    def get_with_path(*aliases: str) -> tuple[Any | None, str | None]:
        return lookup_flat_value(flattened, aliases)

    ttft_value, ttft_path = get_with_path(
        "ttft_ms",
        "time_to_first_token_ms",
        "time_to_first_token",
        "ttft",
    )
    e2e_value, e2e_path = get_with_path(
        "e2e_ms",
        "request_latency_ms",
        "request_latency",
        "end_to_end_latency_ms",
        "end_to_end_latency",
        "latency_ms",
    )
    itl_value, itl_path = get_with_path(
        "itl_ms",
        "inter_token_latency_ms",
        "inter_token_latency",
        "tpot_ms",
        "time_per_output_token_ms",
    )
    error_value = get("error", "error_message", "exception", "failure", "failed")
    # ``error`` is commonly a nested object. ``flatten_record`` retains its
    # leaves for schema inventory, so recover the original object here to keep
    # the pinned source aggregation's truthiness behavior.
    if error_value is None and "error" in record:
        error_value = record.get("error")
    status_value = get("status", "request_status", "result_status")
    error_present = _error_present(error_value, status_value)

    merged_context = dict(context or {})
    row: dict[str, Any] = {
        "github_run_id": _as_str_or_none(merged_context.get("github_run_id")),
        "artifact_id": _as_str_or_none(merged_context.get("artifact_id")),
        "artifact_name": _as_str_or_none(merged_context.get("artifact_name")),
        "concurrency": _as_int_or_none(merged_context.get("concurrency")),
        "target_model": _as_str_or_none(merged_context.get("target_model")),
        "target_precision": _as_str_or_none(merged_context.get("target_precision")),
        "target_hardware": _as_str_or_none(merged_context.get("target_hardware")),
        "target_gpu_count": _as_int_or_none(merged_context.get("target_gpu_count")),
        "framework": _as_str_or_none(merged_context.get("framework")),
        "conversation_id": _as_str_or_none(
            get("conversation_id", "conversationid", "trace_id", "traceid")
        ),
        # The AgentX/Weka loader emits this explicit source-dataset root ID on
        # every observed record.  It is stronger mapping evidence than trying
        # to recover a root from the rendered conversation branch suffix.
        "source_trace_id": _as_str_or_none(
            get("source_trace_id", "source_traceid", "source_root_trace_id")
        ),
        "source_outer_idx": _as_int_or_none(
            get("source_outer_idx", "source_outer_index", "source_request_outer_index")
        ),
        "source_inner_idx": _as_int_or_none(
            get("source_inner_idx", "source_inner_index", "source_request_inner_index")
        ),
        "session_num": _as_int_or_none(
            get("session_num", "session", "session_id", "replay_session")
        ),
        "turn_index": _as_int_or_none(
            get("turn_index", "turn", "request_index", "request_num", "request_number")
        ),
        "request_start_ns": _timestamp_to_ns(
            *get_with_path("request_start_ns", "request_start_time_ns", "start_ns", "start_time_ns")
        ),
        "request_ack_ns": _timestamp_to_ns(
            *get_with_path("request_ack_ns", "request_ack_time_ns", "ack_ns", "ack_time_ns")
        ),
        "request_end_ns": _timestamp_to_ns(
            *get_with_path("request_end_ns", "request_end_time_ns", "end_ns", "end_time_ns")
        ),
        "benchmark_phase": _as_str_or_none(
            get("benchmark_phase", "phase", "request_phase", "benchmarkphase")
        ),
        "worker_id": _as_str_or_none(get("worker_id", "worker", "server_id", "replica_id")),
        "correlation_id": _as_str_or_none(
            get("x_correlation_id", "correlation_id", "request_correlation_id")
        ),
        "was_cancelled": _as_bool_or_none(
            get("was_cancelled", "cancelled", "is_cancelled", "canceled", "is_canceled")
        ),
        "cancellation_time_ns": _timestamp_to_ns(
            *get_with_path("cancellation_time_ns", "cancel_time_ns", "cancelled_at_ns")
        ),
        "error_present": error_present,
        "error_category": _error_category(error_value, status_value),
        "input_tokens": _as_number_or_none(
            get(
                "input_sequence_length",
                "input_tokens",
                "input_token_count",
                "isl",
                "prompt_tokens",
            )
        ),
        "output_tokens": _as_number_or_none(
            get(
                "output_sequence_length",
                "output_tokens",
                "output_token_count",
                "osl",
                "completion_tokens",
            )
        ),
        "ttft_ms": _duration_to_ms(
            ttft_value, ttft_path, unit=_sibling_metric_unit(flattened, ttft_path)
        ),
        "e2e_ms": _duration_to_ms(
            e2e_value, e2e_path, unit=_sibling_metric_unit(flattened, e2e_path)
        ),
        "itl_ms": _duration_to_ms(
            itl_value, itl_path, unit=_sibling_metric_unit(flattened, itl_path)
        ),
        "theoretical_prefix_cache_hit": _as_number_or_none(
            get("theoretical_prefix_cache_hit", "prefix_cache_hit", "cache_hit_rate")
        ),
        "source_metric_name": "inter_token_latency" if itl_value is not None else None,
        "itl_interpretation": "request-level ITL/TPOT metric" if itl_value is not None else None,
        "record_ordinal": record_ordinal,
        "source_file_path": source_file,
        "raw_ttft_field": ttft_path,
        "raw_e2e_field": e2e_path,
        "raw_itl_field": itl_path,
    }
    # Some exporters write a status but no explicit phase.  It is retained as
    # metadata, not converted into an arbitrary profiling classification.
    row["raw_status"] = _as_str_or_none(status_value)
    return row


def profile_schema_inventory(
    profile_paths: Iterable[str | Path],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[JsonlIssue]]:
    """Stream every profile export and calculate field/schema inventory rows.

    Returns ``(field_rows, metric_rows, issues)``.  Each field row is scoped to
    its extracted file.  The caller may safely aggregate by concurrency after
    attaching artifact context; no profile record is retained in memory.
    """

    field_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    issues: list[JsonlIssue] = []
    for profile_path in profile_paths:
        total_records = 0
        values: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "present": 0,
                "null": 0,
                "types": Counter(),
                "numeric_min": None,
                "numeric_max": None,
                # Unit values are observed from the raw sibling
                # ``metrics.<metric>.unit`` leaf when this field is the
                # corresponding ``.value`` leaf. They are not guessed solely
                # from a path-name heuristic.
                "observed_units": Counter(),
                "unit_value_present": 0,
            }
        )
        for _, record in iter_jsonl_records(profile_path, issues=issues):
            total_records += 1
            flattened = flatten_record(record)
            for field_name, value in flattened.items():
                stats = values[field_name]
                stats["present"] += 1
                sibling_unit = _sibling_metric_unit(flattened, field_name)
                if sibling_unit is not None:
                    stats["unit_value_present"] += 1
                    stats["observed_units"][_display_unit_value(sibling_unit)] += 1
                if value is None:
                    stats["null"] += 1
                    stats["types"]["null"] += 1
                    continue
                stats["types"][type(value).__name__] += 1
                number = _as_number_or_none(value)
                if number is not None:
                    stats["numeric_min"] = (
                        number
                        if stats["numeric_min"] is None
                        else min(stats["numeric_min"], number)
                    )
                    stats["numeric_max"] = (
                        number
                        if stats["numeric_max"] is None
                        else max(stats["numeric_max"], number)
                    )
        for field_name, stats in sorted(values.items()):
            present = int(stats["present"])
            observed_unit_values = _format_observed_unit_values(stats["observed_units"])
            observed_unit = (
                next(iter(stats["observed_units"])) if len(stats["observed_units"]) == 1 else None
            )
            row = {
                "source_file_path": str(profile_path),
                "total_records": total_records,
                "field_name": field_name,
                "canonical_field": canonical_field_name(field_name),
                "present_count": present,
                "presence_rate": present / total_records if total_records else 0.0,
                "null_count": int(stats["null"]),
                "null_rate_among_present": stats["null"] / present if present else 0.0,
                "python_types": ",".join(sorted(stats["types"])),
                "numeric_min": stats["numeric_min"],
                "numeric_max": stats["numeric_max"],
                "observed_unit": observed_unit,
                "observed_unit_values": observed_unit_values,
                "unit_value_present_count": int(stats["unit_value_present"]),
                # A directly observed sibling unit supersedes the conservative
                # field-path heuristic. This ensures e.g. TTFT/E2E/ITL report
                # raw ``ms`` and sequence lengths report raw ``tokens``.
                "inferred_unit": observed_unit or _infer_unit_from_path(field_name),
            }
            field_rows.append(row)
            if _looks_like_metric(field_name):
                metric_rows.append(dict(row))
    return field_rows, metric_rows, issues


def _display_unit_value(value: Any) -> str:
    """Return a stable, non-empty raw unit label for schema inventory."""

    if isinstance(value, str):
        return value.strip() or "<empty>"
    return str(value)


def _format_observed_unit_values(counter: Counter[str]) -> str | None:
    """Serialize observed raw unit values with occurrence counts when mixed."""

    if not counter:
        return None
    if len(counter) == 1:
        return next(iter(counter))
    return ";".join(f"{value} ({count})" for value, count in sorted(counter.items()))


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _as_str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    return str(value)


def _as_int_or_none(value: Any) -> int | None:
    number = _as_number_or_none(value)
    if number is None:
        return None
    try:
        return int(number)
    except (TypeError, ValueError, OverflowError):
        return None


def _as_number_or_none(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        result = float(value)
    elif isinstance(value, str):
        try:
            result = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    # NaN/inf do not make meaningful request metrics.
    if result != result or result in {float("inf"), float("-inf")}:
        return None
    return result


def _as_bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n", "", "none", "null"}:
            return False
    return None


def _duration_to_ms(value: Any, path: str | None, *, unit: Any | None = None) -> float | None:
    number = _as_number_or_none(value)
    if number is None:
        return None
    normalized_unit = _unit_name(unit) or _infer_unit_from_path(path or "")
    if normalized_unit == "nanoseconds":
        return number / 1_000_000.0
    if normalized_unit == "microseconds":
        return number / 1_000.0
    if normalized_unit == "seconds":
        return number * 1_000.0
    # Bare AIPerf latency metric names are documented/expected as milliseconds
    # in this analysis.  The original field path remains in the table so this
    # assumption is auditable.
    return number


def _sibling_metric_unit(flattened: Mapping[str, Any], value_path: str | None) -> Any | None:
    if not value_path:
        return None
    if value_path.endswith(".value") or value_path.endswith(".val"):
        parent = value_path.rsplit(".", 1)[0]
        return flattened.get(f"{parent}.unit")
    return None


def _unit_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized in {"ns", "nanosecond", "nanoseconds"}:
        return "nanoseconds"
    if normalized in {"us", "µs", "microsecond", "microseconds"}:
        return "microseconds"
    if normalized in {"ms", "millisecond", "milliseconds"}:
        return "milliseconds"
    if normalized in {"s", "sec", "secs", "second", "seconds"}:
        return "seconds"
    return None


def _timestamp_to_ns(value: Any, path: str | None) -> int | None:
    unit = _infer_unit_from_path(path or "")
    # JSON decoders preserve raw nanosecond timestamps as Python integers.
    # Do not round-trip them through IEEE-754 float: contemporary epoch ns
    # values exceed its exact integer range and lose low-order bits.
    if isinstance(value, Integral) and not isinstance(value, bool):
        integer = int(value)
        if unit == "nanoseconds" or (unit == "unknown" and abs(integer) >= 10**17):
            return integer
    number = _as_number_or_none(value)
    if number is None:
        return None
    if unit == "seconds":
        number *= 1_000_000_000.0
    elif unit == "milliseconds":
        number *= 1_000_000.0
    elif unit == "microseconds":
        number *= 1_000.0
    # A bare timestamp's magnitude can safely disambiguate common units.
    elif unit == "unknown":
        if abs(number) < 1e11:
            number *= 1_000_000_000.0
        elif abs(number) < 1e14:
            number *= 1_000_000.0
        elif abs(number) < 1e17:
            number *= 1_000.0
    try:
        return int(number)
    except (TypeError, ValueError, OverflowError):
        return None


def _infer_unit_from_path(path: str) -> str:
    normalized = path.lower()
    if re.search(r"(?:^|[_\.])(?:ns|nanoseconds?)(?:$|[_\.])", normalized) or normalized.endswith(
        "_ns"
    ):
        return "nanoseconds"
    if re.search(
        r"(?:^|[_\.])(?:us|µs|microseconds?)(?:$|[_\.])", normalized
    ) or normalized.endswith("_us"):
        return "microseconds"
    if re.search(r"(?:^|[_\.])(?:ms|milliseconds?)(?:$|[_\.])", normalized) or normalized.endswith(
        "_ms"
    ):
        return "milliseconds"
    if re.search(
        r"(?:^|[_\.])(?:s|sec|secs|seconds?)(?:$|[_\.])", normalized
    ) or normalized.endswith("_s"):
        return "seconds"
    return "unknown"


def _error_present(error_value: Any, status_value: Any) -> bool:
    if isinstance(error_value, bool):
        if error_value:
            return True
    elif isinstance(error_value, Mapping):
        if error_value:
            return True
    elif error_value not in {None, "", 0, "0", "none", "null", "false", "False"}:
        return True
    status = _as_str_or_none(status_value)
    if status and status.strip().lower() in {"error", "failed", "failure", "cancelled", "canceled"}:
        return True
    return False


def _error_category(error_value: Any, status_value: Any) -> str | None:
    if not _error_present(error_value, status_value):
        return None
    status = _as_str_or_none(status_value)
    if status:
        return status.strip().lower()
    if isinstance(error_value, Mapping):
        for key in ("type", "error_type", "code", "class", "status", "message", "error"):
            value = error_value.get(key)
            if value not in (None, ""):
                return str(value).splitlines()[0][:200]
    if isinstance(error_value, str) and error_value.strip():
        return error_value.strip()[:200]
    return "error_present"


def _looks_like_metric(path: str) -> bool:
    key = canonical_field_name(path)
    metric_markers = (
        "latency",
        "token",
        "ttft",
        "itl",
        "tpot",
        "throughput",
        "sequence",
        "cache",
        "duration",
    )
    return any(marker in key for marker in metric_markers)
