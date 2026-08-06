"""Streaming parser for the ``cc-traces-weka-062126`` source trace format.

The public dataset stores one root conversation per JSONL line.  A root has a
``requests`` list containing ordinary model requests and (occasionally)
``type: subagent`` containers whose own ``requests`` list represents another
conversation branch.  This module deliberately keeps the source workload
metadata separate from target-model benchmark data.

Only a deterministic fingerprint of ``hash_ids`` is emitted.  The full hash
sequence can be very large and is not needed in processed tables.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO

TRACE_ID_KEYS = ("id", "trace_id", "root_trace_id")
REQUEST_LIST_KEYS = ("requests", "events")
INPUT_TOKEN_KEYS = ("in", "input_tokens", "input_sequence_length", "input_length")
OUTPUT_TOKEN_KEYS = ("out", "output_tokens", "output_sequence_length", "output_length")
TIME_KEYS = ("t", "time_s", "timestamp_s", "timestamp")
API_TIME_KEYS = ("api_time", "api_time_s", "duration_s")
TTFT_KEYS = ("ttft", "ttft_s", "time_to_first_token_s")
THINK_TIME_KEYS = ("think_time", "think_time_s")
HASH_ID_KEYS = ("hash_ids", "hash_id_list", "prefix_hash_ids")


class TraceParseError(ValueError):
    """Base exception for source-trace parse failures."""


class TraceJSONLError(TraceParseError):
    """A JSONL line could not be decoded."""

    def __init__(self, path: Path, line_number: int, reason: str) -> None:
        self.path = path
        self.line_number = line_number
        self.reason = reason
        super().__init__(f"Invalid JSON object in {path} at line {line_number}: {reason}")


class TraceSchemaError(TraceParseError):
    """A decoded trace does not have the minimum expected structure."""


def _json_loads(payload: str) -> Any:
    """Use orjson when installed while retaining a standard-library fallback."""

    try:
        import orjson  # type: ignore[import-not-found]
    except ImportError:
        return json.loads(payload)
    return orjson.loads(payload)


def _open_text(path: Path) -> TextIO:
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def iter_trace_objects(path: str | Path) -> Iterator[dict[str, Any]]:
    """Yield JSON objects one line at a time.

    Blank lines are ignored.  A malformed non-blank line is an error rather
    than silently dropped, because dropping a root trace would corrupt
    coverage denominators.
    """

    trace_path = Path(path)
    with _open_text(trace_path) as handle:
        for line_number, line in enumerate(handle, start=1):
            payload = line.strip()
            if not payload:
                continue
            try:
                decoded = _json_loads(payload)
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise TraceJSONLError(trace_path, line_number, str(exc)) from exc
            if not isinstance(decoded, Mapping):
                raise TraceJSONLError(trace_path, line_number, "line must contain a JSON object")
            yield dict(decoded)


def root_trace_id(trace: Mapping[str, Any]) -> str:
    """Return the public root trace identifier or raise a precise schema error."""

    value = _first_present(trace, TRACE_ID_KEYS)
    if value is None or not str(value).strip():
        raise TraceSchemaError(
            "Source trace is missing a non-empty root id (accepted keys: "
            f"{', '.join(TRACE_ID_KEYS)})."
        )
    return str(value)


def _first_present(mapping: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def _as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        try:
            numeric = float(value.strip())
        except ValueError:
            return None
        return int(numeric) if numeric.is_integer() else None
    return None


def _as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def _request_list(value: Mapping[str, Any]) -> list[Mapping[str, Any]] | None:
    nested = _first_present(value, REQUEST_LIST_KEYS)
    if nested is None:
        return None
    if not isinstance(nested, list):
        return None
    return [item for item in nested if isinstance(item, Mapping)]


def _is_subagent_container(item: Mapping[str, Any]) -> bool:
    """Identify a branch container without treating it as a model request."""

    if _request_list(item) is None:
        return False
    record_type = _as_str(item.get("type"))
    return (
        (record_type is not None and record_type.lower() in {"subagent", "agent", "branch"})
        or "agent_id" in item
        or "subagent_type" in item
        or _first_present(item, INPUT_TOKEN_KEYS) is None
    )


def _hash_ids(value: Any) -> tuple[Any, ...] | None:
    if value is None:
        return None
    if isinstance(value, (str, bytes, bytearray, Mapping)) or not isinstance(value, Sequence):
        return None
    return tuple(value)


def _hash_fingerprint(values: tuple[Any, ...] | None) -> str | None:
    if values is None:
        return None
    canonical = json.dumps(list(values), ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def longest_common_prefix(left: Sequence[Any], right: Sequence[Any]) -> int:
    """Return the count of equal leading hash blocks in two sequences."""

    count = 0
    for first, second in zip(left, right, strict=False):
        if first != second:
            break
        count += 1
    return count


def _normalise_models(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value else ()
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return tuple(item for item in (_as_str(item) for item in value) if item is not None)
    normalized = _as_str(value)
    return (normalized,) if normalized is not None else ()


def _branch_type(subagent_type: str | None) -> str:
    """Use conservative source-side labels for a nested branch."""

    text = (subagent_type or "").lower()
    if "fan" in text or "fork" in text:
        return "fanout"
    if "aux" in text:
        return "auxiliary"
    if "worker" in text or "group" in text:
        return "worker_group"
    return "subagent"


@dataclass
class TraceAccumulator:
    """Per-root state used while rows are emitted in streaming order."""

    trace: Mapping[str, Any]
    root_id: str
    block_size: int | None
    hash_id_scope: str | None
    declared_models: tuple[str, ...]
    request_count_total: int = 0
    root_request_count: int = 0
    subagent_request_count: int = 0
    subagent_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    first_t: float | None = None
    last_t: float | None = None
    missing_input_token_count: int = 0
    missing_output_token_count: int = 0
    malformed_nested_entry_count: int = 0
    _models_seen: set[str] = field(default_factory=set)
    _previous_hashes: dict[str, tuple[Any, ...] | None] = field(default_factory=dict)
    _branch_request_counts: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_trace(cls, trace: Mapping[str, Any]) -> TraceAccumulator:
        block_size = _as_int(trace.get("block_size"))
        return cls(
            trace=trace,
            root_id=root_trace_id(trace),
            block_size=block_size if block_size is not None and block_size > 0 else None,
            hash_id_scope=_as_str(trace.get("hash_id_scope")),
            declared_models=_normalise_models(trace.get("models")),
        )

    def record_request(
        self,
        request: Mapping[str, Any],
        *,
        conversation_path: str,
        parent_conversation_path: str | None,
        branch_type: str,
        agent_id: str | None,
        branch_subagent_type: str | None,
        outer_index: int,
        inner_index: int | None,
        branch_depth: int,
    ) -> dict[str, Any]:
        """Normalise one source request and update per-root aggregate state."""

        input_tokens = _as_int(_first_present(request, INPUT_TOKEN_KEYS))
        output_tokens = _as_int(_first_present(request, OUTPUT_TOKEN_KEYS))
        request_time = _as_float(_first_present(request, TIME_KEYS))
        model = _as_str(request.get("model"))
        hash_values = _hash_ids(_first_present(request, HASH_ID_KEYS))

        branch_request_index = self._branch_request_counts.get(conversation_path, 0)
        is_first_in_branch = branch_request_index == 0
        self._branch_request_counts[conversation_path] = branch_request_index + 1

        has_previous = conversation_path in self._previous_hashes
        previous_hashes = self._previous_hashes.get(conversation_path)
        if has_previous and previous_hashes is not None and hash_values is not None:
            lcp_blocks: int | None = longest_common_prefix(previous_hashes, hash_values)
            rollback_blocks: int | None = max(len(previous_hashes) - lcp_blocks, 0)
        else:
            lcp_blocks = None
            rollback_blocks = None

        if lcp_blocks is not None and self.block_size is not None and input_tokens is not None:
            cached_tokens: int | None = min(input_tokens, lcp_blocks * self.block_size)
            new_tokens: int | None = max(input_tokens - cached_tokens, 0)
            cache_ratio: float | None = cached_tokens / input_tokens if input_tokens > 0 else None
        else:
            cached_tokens = None
            new_tokens = None
            cache_ratio = None
        self._previous_hashes[conversation_path] = hash_values

        self.request_count_total += 1
        if branch_type == "root":
            self.root_request_count += 1
        else:
            self.subagent_request_count += 1
        if input_tokens is None:
            self.missing_input_token_count += 1
        else:
            self.total_input_tokens += input_tokens
            self.max_input_tokens = (
                input_tokens if self.max_input_tokens is None else max(self.max_input_tokens, input_tokens)
            )
        if output_tokens is None:
            self.missing_output_token_count += 1
        else:
            self.total_output_tokens += output_tokens
            self.max_output_tokens = (
                output_tokens if self.max_output_tokens is None else max(self.max_output_tokens, output_tokens)
            )
        if request_time is not None:
            self.first_t = request_time if self.first_t is None else min(self.first_t, request_time)
            self.last_t = request_time if self.last_t is None else max(self.last_t, request_time)
        if model is not None:
            self._models_seen.add(model)

        parse_status = "ok"
        missing_fields = []
        if model is None:
            missing_fields.append("model")
        if input_tokens is None:
            missing_fields.append("input_tokens")
        if output_tokens is None:
            missing_fields.append("output_tokens")
        if missing_fields:
            parse_status = "partial:" + ",".join(missing_fields)

        return {
            "root_trace_id": self.root_id,
            "source_conversation_path": conversation_path,
            "source_parent_conversation_path": parent_conversation_path,
            "source_branch_type": branch_type,
            "source_subagent_type": branch_subagent_type,
            "source_agent_id": agent_id,
            "source_branch_depth": branch_depth,
            "source_outer_request_index": outer_index,
            "source_inner_request_index": inner_index,
            "source_branch_request_index": branch_request_index,
            "source_request_index": self.request_count_total - 1,
            "source_model": model,
            "source_request_type": _as_str(request.get("type")),
            "source_t_s": request_time,
            "source_input_tokens": input_tokens,
            "source_output_tokens": output_tokens,
            "source_api_time_s": _as_float(_first_present(request, API_TIME_KEYS)),
            "source_ttft_s": _as_float(_first_present(request, TTFT_KEYS)),
            "source_think_time_s": _as_float(_first_present(request, THINK_TIME_KEYS)),
            "hash_block_count": len(hash_values) if hash_values is not None else None,
            "hash_ids_fingerprint": _hash_fingerprint(hash_values),
            "lcp_block_count": lcp_blocks,
            "theoretical_cached_tokens": cached_tokens,
            "theoretical_new_tokens": new_tokens,
            "theoretical_cache_ratio": cache_ratio,
            "rollback_blocks": rollback_blocks,
            "branch_fork_indicator": branch_type != "root" and is_first_in_branch,
            "is_first_request_in_branch": is_first_in_branch,
            "theoretical_prefix_basis": "previous_request_same_source_branch",
            "source_record_parse_status": parse_status,
        }

    def record_subagent(self) -> None:
        self.subagent_count += 1

    def record_malformed_nested_entry(self) -> None:
        self.malformed_nested_entry_count += 1

    def summary_row(self) -> dict[str, Any]:
        models = list(self.declared_models)
        for model in sorted(self._models_seen):
            if model not in models:
                models.append(model)
        span = self.last_t - self.first_t if self.first_t is not None and self.last_t is not None else None
        return {
            "root_trace_id": self.root_id,
            "source_models": json.dumps(models, ensure_ascii=False, separators=(",", ":")),
            "source_request_count_total": self.request_count_total,
            "source_root_request_count": self.root_request_count,
            "source_subagent_count": self.subagent_count,
            "source_subagent_request_count": self.subagent_request_count,
            "source_total_input_tokens": self.total_input_tokens,
            "source_total_output_tokens": self.total_output_tokens,
            "source_first_t": self.first_t,
            "source_last_t": self.last_t,
            "source_recorded_span_s": span,
            "source_max_input_tokens": self.max_input_tokens,
            "source_max_output_tokens": self.max_output_tokens,
            "block_size": self.block_size,
            "hash_id_scope": self.hash_id_scope,
            "source_missing_input_token_count": self.missing_input_token_count,
            "source_missing_output_token_count": self.missing_output_token_count,
            "source_malformed_nested_entry_count": self.malformed_nested_entry_count,
        }


def iter_source_requests(
    trace: Mapping[str, Any], *, accumulator: TraceAccumulator | None = None
) -> Iterator[dict[str, Any]]:
    """Flatten root and recursively nested subagent requests.

    ``accumulator`` enables callers to write request rows immediately and emit
    the root summary only after the generator is exhausted.  Cache-shape
    columns compare each request only with the prior request in the same
    source branch; they are theoretical workload properties, not observed
    server cache hits.
    """

    state = accumulator or TraceAccumulator.from_trace(trace)
    root_requests = _request_list(trace)
    if root_requests is None:
        raise TraceSchemaError(
            f"Source trace {state.root_id!r} has no list-valued requests field "
            f"(accepted keys: {', '.join(REQUEST_LIST_KEYS)})."
        )

    def walk(
        items: Sequence[Mapping[str, Any]],
        *,
        conversation_path: str,
        parent_conversation_path: str | None,
        branch_type: str,
        agent_id: str | None,
        branch_subagent_type: str | None,
        outer_index: int | None,
        branch_depth: int,
    ) -> Iterator[dict[str, Any]]:
        for local_index, item in enumerate(items):
            if not isinstance(item, Mapping):
                state.record_malformed_nested_entry()
                continue
            nested = _request_list(item)
            if _is_subagent_container(item):
                state.record_subagent()
                child_agent_id = _as_str(item.get("agent_id")) or f"unknown_{branch_depth}_{local_index}"
                child_path = f"{conversation_path}::sa:{child_agent_id}"
                child_subagent_type = _as_str(item.get("subagent_type"))
                child_type = _branch_type(child_subagent_type)
                child_outer_index = local_index if outer_index is None else outer_index
                # Empty subagents are meaningful branch metadata, even though
                # they produce no request rows.
                yield from walk(
                    nested or [],
                    conversation_path=child_path,
                    parent_conversation_path=conversation_path,
                    branch_type=child_type,
                    agent_id=child_agent_id,
                    branch_subagent_type=child_subagent_type,
                    outer_index=child_outer_index,
                    branch_depth=branch_depth + 1,
                )
                continue

            current_outer_index = local_index if outer_index is None else outer_index
            current_inner_index = None if outer_index is None else local_index
            yield state.record_request(
                item,
                conversation_path=conversation_path,
                parent_conversation_path=parent_conversation_path,
                branch_type=branch_type,
                agent_id=agent_id,
                branch_subagent_type=branch_subagent_type,
                outer_index=current_outer_index,
                inner_index=current_inner_index,
                branch_depth=branch_depth,
            )

            # A non-agent wrapper is unusual, but recurse instead of silently
            # losing child requests.  The wrapper itself remains a partial row
            # if it includes request-like fields.
            if nested is not None:
                yield from walk(
                    nested,
                    conversation_path=conversation_path,
                    parent_conversation_path=parent_conversation_path,
                    branch_type=branch_type,
                    agent_id=agent_id,
                    branch_subagent_type=branch_subagent_type,
                    outer_index=current_outer_index,
                    branch_depth=branch_depth,
                )

    yield from walk(
        root_requests,
        conversation_path=state.root_id,
        parent_conversation_path=None,
        branch_type="root",
        agent_id=None,
        branch_subagent_type=None,
        outer_index=None,
        branch_depth=0,
    )


def flatten_trace(trace: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Convenience helper for fixtures and small traces.

    Production code should prefer :func:`iter_source_requests` so that it can
    write rows incrementally rather than collecting the complete dataset.
    """

    accumulator = TraceAccumulator.from_trace(trace)
    rows = list(iter_source_requests(trace, accumulator=accumulator))
    return rows, accumulator.summary_row()
