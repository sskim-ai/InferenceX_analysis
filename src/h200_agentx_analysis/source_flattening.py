"""Build streaming Parquet tables from public Claude Code workload traces.

The resulting tables describe source workload provenance.  They deliberately
do not identify the source model as the H200 target model and retain source
``api_time`` only as historical source-side metadata.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .hf_trace_parser import TraceAccumulator, iter_source_requests, iter_trace_objects

SOURCE_TRACE_SUMMARY_COLUMNS = (
    "root_trace_id",
    "source_models",
    "source_request_count_total",
    "source_root_request_count",
    "source_subagent_count",
    "source_subagent_request_count",
    "source_total_input_tokens",
    "source_total_output_tokens",
    "source_first_t",
    "source_last_t",
    "source_recorded_span_s",
    "source_max_input_tokens",
    "source_max_output_tokens",
    "block_size",
    "hash_id_scope",
    "source_missing_input_token_count",
    "source_missing_output_token_count",
    "source_malformed_nested_entry_count",
)

SOURCE_REQUEST_COLUMNS = (
    "root_trace_id",
    "source_conversation_path",
    "source_parent_conversation_path",
    "source_branch_type",
    "source_subagent_type",
    "source_agent_id",
    "source_branch_depth",
    "source_outer_request_index",
    "source_inner_request_index",
    "source_branch_request_index",
    "source_request_index",
    "source_model",
    "source_request_type",
    "source_t_s",
    "source_input_tokens",
    "source_output_tokens",
    "source_api_time_s",
    "source_ttft_s",
    "source_think_time_s",
    "hash_block_count",
    "hash_ids_fingerprint",
    "lcp_block_count",
    "theoretical_cached_tokens",
    "theoretical_new_tokens",
    "theoretical_cache_ratio",
    "rollback_blocks",
    "branch_fork_indicator",
    "is_first_request_in_branch",
    "theoretical_prefix_basis",
    "source_record_parse_status",
)


class ParquetDependencyError(RuntimeError):
    """Raised when a caller asks to build Parquet without an engine."""


class DuplicateRootTraceIdError(ValueError):
    """Raised when the input violates the expected one-line-per-root invariant."""


@dataclass(frozen=True)
class SourceBuildResult:
    input_path: str
    summary_path: str
    requests_path: str
    source_available: bool
    trace_count: int
    request_count: int
    duplicate_root_trace_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["duplicate_root_trace_ids"] = list(self.duplicate_root_trace_ids)
        return result


def _require_pyarrow() -> tuple[Any, Any]:
    try:
        import pyarrow as pa  # type: ignore[import-not-found]
        import pyarrow.parquet as pq  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ParquetDependencyError(
            "Building source tables requires pyarrow. Run `make bootstrap` or "
            "install the project dependencies, then rerun `make build-source`."
        ) from exc
    return pa, pq


def _schemas() -> tuple[Any, Any]:
    pa, _ = _require_pyarrow()
    summary_schema = pa.schema(
        [
            pa.field("root_trace_id", pa.string()),
            pa.field("source_models", pa.string()),
            pa.field("source_request_count_total", pa.int64()),
            pa.field("source_root_request_count", pa.int64()),
            pa.field("source_subagent_count", pa.int64()),
            pa.field("source_subagent_request_count", pa.int64()),
            pa.field("source_total_input_tokens", pa.int64()),
            pa.field("source_total_output_tokens", pa.int64()),
            pa.field("source_first_t", pa.float64()),
            pa.field("source_last_t", pa.float64()),
            pa.field("source_recorded_span_s", pa.float64()),
            pa.field("source_max_input_tokens", pa.int64()),
            pa.field("source_max_output_tokens", pa.int64()),
            pa.field("block_size", pa.int64()),
            pa.field("hash_id_scope", pa.string()),
            pa.field("source_missing_input_token_count", pa.int64()),
            pa.field("source_missing_output_token_count", pa.int64()),
            pa.field("source_malformed_nested_entry_count", pa.int64()),
        ]
    )
    request_schema = pa.schema(
        [
            pa.field("root_trace_id", pa.string()),
            pa.field("source_conversation_path", pa.string()),
            pa.field("source_parent_conversation_path", pa.string()),
            pa.field("source_branch_type", pa.string()),
            pa.field("source_subagent_type", pa.string()),
            pa.field("source_agent_id", pa.string()),
            pa.field("source_branch_depth", pa.int64()),
            pa.field("source_outer_request_index", pa.int64()),
            pa.field("source_inner_request_index", pa.int64()),
            pa.field("source_branch_request_index", pa.int64()),
            pa.field("source_request_index", pa.int64()),
            pa.field("source_model", pa.string()),
            pa.field("source_request_type", pa.string()),
            pa.field("source_t_s", pa.float64()),
            pa.field("source_input_tokens", pa.int64()),
            pa.field("source_output_tokens", pa.int64()),
            pa.field("source_api_time_s", pa.float64()),
            pa.field("source_ttft_s", pa.float64()),
            pa.field("source_think_time_s", pa.float64()),
            pa.field("hash_block_count", pa.int64()),
            pa.field("hash_ids_fingerprint", pa.string()),
            pa.field("lcp_block_count", pa.int64()),
            pa.field("theoretical_cached_tokens", pa.int64()),
            pa.field("theoretical_new_tokens", pa.int64()),
            pa.field("theoretical_cache_ratio", pa.float64()),
            pa.field("rollback_blocks", pa.int64()),
            pa.field("branch_fork_indicator", pa.bool_()),
            pa.field("is_first_request_in_branch", pa.bool_()),
            pa.field("theoretical_prefix_basis", pa.string()),
            pa.field("source_record_parse_status", pa.string()),
        ]
    )
    return summary_schema, request_schema


class _ParquetBatchWriter:
    """Small bounded row buffer around a pyarrow ParquetWriter."""

    def __init__(self, path: Path, schema: Any, *, batch_size: int) -> None:
        pa, pq = _require_pyarrow()
        self._pa = pa
        self._schema = schema
        self._batch_size = max(1, batch_size)
        self._rows: list[Mapping[str, Any]] = []
        path.parent.mkdir(parents=True, exist_ok=True)
        self._writer = pq.ParquetWriter(path, schema=schema, compression="zstd")

    def write(self, row: Mapping[str, Any]) -> None:
        self._rows.append(row)
        if len(self._rows) >= self._batch_size:
            self.flush()

    def flush(self) -> None:
        if not self._rows:
            return
        table = self._pa.Table.from_pylist(self._rows, schema=self._schema)
        self._writer.write_table(table)
        self._rows.clear()

    def close(self) -> None:
        self.flush()
        self._writer.close()


def _empty_outputs(summary_path: Path, requests_path: Path, *, batch_size: int) -> None:
    """Atomically replace both empty outputs for an explicit missing-input state."""
    summary_schema, request_schema = _schemas()
    summary_tmp, requests_tmp = _temporary_output_paths(summary_path, requests_path)
    summary_writer = _ParquetBatchWriter(summary_tmp, summary_schema, batch_size=batch_size)
    request_writer = _ParquetBatchWriter(requests_tmp, request_schema, batch_size=batch_size)
    try:
        summary_writer.close()
        request_writer.close()
        summary_tmp.replace(summary_path)
        requests_tmp.replace(requests_path)
    except Exception:
        summary_tmp.unlink(missing_ok=True)
        requests_tmp.unlink(missing_ok=True)
        raise


def _temporary_output_paths(summary_path: Path, requests_path: Path) -> tuple[Path, Path]:
    """Return same-directory temporary paths so ``replace`` remains atomic."""
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    requests_path.parent.mkdir(parents=True, exist_ok=True)
    return (
        summary_path.with_name(f".{summary_path.name}.building"),
        requests_path.with_name(f".{requests_path.name}.building"),
    )


def build_source_trace_tables(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    batch_size: int = 10_000,
    missing_policy: str = "error",
    allow_duplicate_root_ids: bool = False,
) -> SourceBuildResult:
    """Create source summary and request Parquet tables without full-file loading.

    ``missing_policy='empty'`` writes valid zero-row Parquet files so later
    pipeline stages can report an explicit unavailable-source condition.  It
    never claims that source traces were acquired.
    """

    if missing_policy not in {"error", "empty"}:
        raise ValueError("missing_policy must be either 'error' or 'empty'")
    raw_path = Path(input_path)
    processed_dir = Path(output_dir)
    summary_path = processed_dir / "source_trace_summary.parquet"
    requests_path = processed_dir / "source_requests.parquet"

    if not raw_path.is_file():
        if missing_policy == "error":
            raise FileNotFoundError(
                f"Source trace file not found: {raw_path}. Acquire it with `make acquire-traces` "
                "before running `make build-source`, or pass --missing-policy empty to create "
                "explicit zero-row placeholders."
            )
        _empty_outputs(summary_path, requests_path, batch_size=batch_size)
        return SourceBuildResult(
            input_path=str(raw_path),
            summary_path=str(summary_path),
            requests_path=str(requests_path),
            source_available=False,
            trace_count=0,
            request_count=0,
            duplicate_root_trace_ids=(),
        )

    summary_schema, request_schema = _schemas()
    summary_tmp, requests_tmp = _temporary_output_paths(summary_path, requests_path)
    summary_tmp.unlink(missing_ok=True)
    requests_tmp.unlink(missing_ok=True)
    summary_writer = _ParquetBatchWriter(summary_tmp, summary_schema, batch_size=batch_size)
    request_writer = _ParquetBatchWriter(requests_tmp, request_schema, batch_size=batch_size)
    seen_root_ids: set[str] = set()
    duplicates: list[str] = []
    trace_count = 0
    request_count = 0
    try:
        for trace in iter_trace_objects(raw_path):
            state = TraceAccumulator.from_trace(trace)
            if state.root_id in seen_root_ids:
                duplicates.append(state.root_id)
                if not allow_duplicate_root_ids:
                    raise DuplicateRootTraceIdError(
                        f"Duplicate root trace id {state.root_id!r}; source coverage denominators require "
                        "unique root IDs. Use --allow-duplicate-root-ids only for forensic inspection."
                    )
            seen_root_ids.add(state.root_id)
            for row in iter_source_requests(trace, accumulator=state):
                request_writer.write(row)
                request_count += 1
            summary_writer.write(state.summary_row())
            trace_count += 1
    except Exception:
        summary_writer.close()
        request_writer.close()
        summary_tmp.unlink(missing_ok=True)
        requests_tmp.unlink(missing_ok=True)
        raise
    else:
        summary_writer.close()
        request_writer.close()
        summary_tmp.replace(summary_path)
        requests_tmp.replace(requests_path)

    return SourceBuildResult(
        input_path=str(raw_path),
        summary_path=str(summary_path),
        requests_path=str(requests_path),
        source_available=True,
        trace_count=trace_count,
        request_count=request_count,
        duplicate_root_trace_ids=tuple(duplicates),
    )
