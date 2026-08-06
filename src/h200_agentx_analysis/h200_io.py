"""Bounded Parquet I/O helpers for H200 profile-processing stages."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .artifact_parser import (
    ArtifactInfo,
    JsonlIssue,
    find_profile_exports,
    infer_profile_context,
    iter_jsonl_records,
    load_artifact_inventory,
    normalize_profile_record,
    parse_concurrency,
)
from .id_normalization import normalize_conversation_id

H200_REQUEST_COLUMNS = (
    "github_run_id",
    "artifact_id",
    "artifact_name",
    "concurrency",
    "target_model",
    "target_precision",
    "target_hardware",
    "target_gpu_count",
    "framework",
    "conversation_id",
    "source_trace_id",
    "source_outer_idx",
    "source_inner_idx",
    "root_trace_id",
    "root_trace_id_provenance",
    "branch_suffix",
    "branch_type",
    "normalization_rule",
    "source_id_matched",
    "session_num",
    "turn_index",
    "request_start_ns",
    "request_ack_ns",
    "request_end_ns",
    "benchmark_phase",
    "worker_id",
    "correlation_id",
    "was_cancelled",
    "cancellation_time_ns",
    "error_present",
    "error_category",
    "input_tokens",
    "output_tokens",
    "ttft_ms",
    "e2e_ms",
    "itl_ms",
    "theoretical_prefix_cache_hit",
    "source_metric_name",
    "itl_interpretation",
    "record_ordinal",
    "source_file_path",
    "raw_ttft_field",
    "raw_e2e_field",
    "raw_itl_field",
    "raw_status",
    "request_identity_key",
    "is_exact_duplicate",
    "exclusion_reason",
    "is_profiled_valid",
    "ttft_s",
    "e2e_s",
    "post_ttft_s",
    "ttft_exceeds_e2e",
    "observed_itl_implied_tps",
    "post_ttft_tps",
    "e2e_output_tps",
    "input_tokens_per_observed_ttft_s",
)

EXCLUSION_COLUMNS = (
    "github_run_id",
    "artifact_id",
    "artifact_name",
    "concurrency",
    "conversation_id",
    "source_trace_id",
    "source_outer_idx",
    "source_inner_idx",
    "root_trace_id",
    "root_trace_id_provenance",
    "session_num",
    "turn_index",
    "record_ordinal",
    "source_file_path",
    "benchmark_phase",
    "error_present",
    "was_cancelled",
    "input_tokens",
    "output_tokens",
    "ttft_ms",
    "e2e_ms",
    "itl_ms",
    "is_exact_duplicate",
    "exclusion_reason",
)


class ParquetDependencyError(RuntimeError):
    """Raised when PyArrow is unavailable for a requested Parquet operation."""


@dataclass(frozen=True)
class H200BuildResult:
    raw_root: str
    output_dir: str
    profile_export_count: int
    all_record_count: int
    profiled_record_count: int
    excluded_record_count: int
    exact_duplicate_count: int
    malformed_jsonl_line_count: int
    h200_available: bool
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _require_pyarrow() -> tuple[Any, Any]:
    try:
        import pyarrow as pa  # type: ignore[import-not-found]
        import pyarrow.parquet as pq  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ParquetDependencyError(
            "H200 table generation requires pyarrow. Run `make bootstrap` and retry."
        ) from exc
    return pa, pq


def h200_request_schema() -> Any:
    """Define an explicit nullable schema independent of pandas inference."""

    pa, _ = _require_pyarrow()
    strings = {
        "github_run_id",
        "artifact_id",
        "artifact_name",
        "target_model",
        "target_precision",
        "target_hardware",
        "framework",
        "conversation_id",
        "source_trace_id",
        "root_trace_id",
        "root_trace_id_provenance",
        "branch_suffix",
        "branch_type",
        "normalization_rule",
        "benchmark_phase",
        "worker_id",
        "correlation_id",
        "error_category",
        "source_metric_name",
        "itl_interpretation",
        "source_file_path",
        "raw_ttft_field",
        "raw_e2e_field",
        "raw_itl_field",
        "raw_status",
        "request_identity_key",
        "exclusion_reason",
    }
    integers = {
        "concurrency",
        "target_gpu_count",
        "source_outer_idx",
        "source_inner_idx",
        "session_num",
        "turn_index",
        "request_start_ns",
        "request_ack_ns",
        "request_end_ns",
        "cancellation_time_ns",
        "record_ordinal",
    }
    booleans = {
        "source_id_matched",
        "was_cancelled",
        "error_present",
        "is_exact_duplicate",
        "is_profiled_valid",
        "ttft_exceeds_e2e",
    }
    fields = []
    for column in H200_REQUEST_COLUMNS:
        if column in strings:
            dtype = pa.string()
        elif column in integers:
            dtype = pa.int64()
        elif column in booleans:
            dtype = pa.bool_()
        else:
            dtype = pa.float64()
        fields.append(pa.field(column, dtype, nullable=True))
    return pa.schema(fields)


class H200ParquetWriter:
    """A bounded row buffer that writes canonical H200 request tables."""

    def __init__(self, path: str | Path, *, batch_size: int = 10_000) -> None:
        pa, pq = _require_pyarrow()
        self._pa = pa
        self._schema = h200_request_schema()
        self._batch_size = max(1, batch_size)
        self._rows: list[dict[str, Any]] = []
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._writer = pq.ParquetWriter(self.path, self._schema, compression="zstd")

    def write_rows(self, rows: Iterable[Mapping[str, Any]]) -> None:
        for row in rows:
            self._rows.append(_sanitize_row(row, H200_REQUEST_COLUMNS))
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


def write_empty_h200_outputs(output_dir: str | Path, *, batch_size: int = 10_000) -> None:
    """Write valid zero-row Parquet placeholders and a CSV exclusion header."""

    import pandas as pd

    destination = Path(output_dir)
    for name in ("h200_requests_all.parquet", "h200_requests_profiled.parquet"):
        writer = H200ParquetWriter(destination / name, batch_size=batch_size)
        writer.close()
    pd.DataFrame(columns=EXCLUSION_COLUMNS).to_csv(
        destination / "h200_request_exclusions.csv", index=False
    )


def build_h200_request_tables(
    raw_root: str | Path,
    output_dir: str | Path,
    *,
    github_run_id: int | str | None = None,
    expected_environment: Mapping[str, Any] | None = None,
    artifact_inventory_path: str | Path | None = None,
    batch_size: int = 10_000,
    missing_policy: str = "empty",
) -> H200BuildResult:
    """Stream raw profile exports into canonical all/profiled request Parquet tables.

    No profile export is a normal blocked-acquisition state, not a fabricated
    zero-observation benchmark.  Valid empty Parquet outputs are written so
    downstream stages can produce explicit unavailable tables and reports.
    """

    if missing_policy not in {"empty", "error"}:
        raise ValueError("missing_policy must be either 'empty' or 'error'")
    source_root = Path(raw_root)
    destination = Path(output_dir)
    profiles = find_profile_exports(source_root)
    if not profiles:
        if missing_policy == "error":
            raise FileNotFoundError(
                f"No profile_export.jsonl was found under {source_root}. "
                "Run `make acquire-run` after GitHub authentication, then retry."
            )
        write_empty_h200_outputs(destination, batch_size=batch_size)
        result = H200BuildResult(
            raw_root=str(source_root),
            output_dir=str(destination),
            profile_export_count=0,
            all_record_count=0,
            profiled_record_count=0,
            excluded_record_count=0,
            exact_duplicate_count=0,
            malformed_jsonl_line_count=0,
            h200_available=False,
            status="blocked_no_profile_export",
        )
        write_json(destination / "h200_build_status.json", result.to_dict())
        return result

    artifacts = load_artifact_inventory(artifact_inventory_path) if artifact_inventory_path else []
    environment = dict(expected_environment or {})
    all_writer = H200ParquetWriter(destination / "h200_requests_all.parquet", batch_size=batch_size)
    profiled_writer = H200ParquetWriter(
        destination / "h200_requests_profiled.parquet", batch_size=batch_size
    )
    exclusions_path = destination / "h200_request_exclusions.csv"
    # Ensure the header exists even when every record passes.
    write_empty_exclusions = True
    all_count = profiled_count = excluded_count = duplicate_count = 0
    seen_duplicate_fingerprints: set[str] = set()
    issues: list[JsonlIssue] = []
    try:
        for profile_path in profiles:
            artifact = infer_profile_context(profile_path, artifacts)
            context = _profile_context(
                profile_path,
                artifact,
                github_run_id=github_run_id,
                environment=environment,
            )
            rows: list[dict[str, Any]] = []
            for line_number, record in iter_jsonl_records(profile_path, issues=issues):
                row = normalize_profile_record(
                    record,
                    context=context,
                    source_file=str(profile_path),
                    record_ordinal=line_number,
                )
                normalized = normalize_conversation_id(row.get("conversation_id"))
                row.update(normalized.to_dict())
                source_trace_id = str(row.get("source_trace_id") or "").strip()
                if source_trace_id:
                    row["source_trace_id"] = source_trace_id
                    row["root_trace_id"] = source_trace_id
                    row["root_trace_id_provenance"] = "metadata.source_trace_id"
                    row["normalization_rule"] = "explicit_metadata_source_trace_id"
                else:
                    row["root_trace_id_provenance"] = "conversation_id_normalization"
                # This becomes true only in join_trace_ids.py after the source
                # ID universe has been loaded.
                row["source_id_matched"] = False
                rows.append(row)
                if len(rows) >= batch_size:
                    counts, write_empty_exclusions = _write_normalized_batch(
                        rows,
                        all_writer,
                        profiled_writer,
                        exclusions_path,
                        header=write_empty_exclusions,
                        seen_fingerprints=seen_duplicate_fingerprints,
                    )
                    all_count += counts[0]
                    profiled_count += counts[1]
                    excluded_count += counts[2]
                    duplicate_count += counts[3]
                    rows.clear()
            if rows:
                counts, write_empty_exclusions = _write_normalized_batch(
                    rows,
                    all_writer,
                    profiled_writer,
                    exclusions_path,
                    header=write_empty_exclusions,
                    seen_fingerprints=seen_duplicate_fingerprints,
                )
                all_count += counts[0]
                profiled_count += counts[1]
                excluded_count += counts[2]
                duplicate_count += counts[3]
    finally:
        all_writer.close()
        profiled_writer.close()
    if write_empty_exclusions:
        # No rejected rows were appended, so produce the requested readable
        # header without special-casing downstream CSV readers.
        import pandas as pd

        pd.DataFrame(columns=EXCLUSION_COLUMNS).to_csv(exclusions_path, index=False)
    result = H200BuildResult(
        raw_root=str(source_root),
        output_dir=str(destination),
        profile_export_count=len(profiles),
        all_record_count=all_count,
        profiled_record_count=profiled_count,
        excluded_record_count=excluded_count,
        exact_duplicate_count=duplicate_count,
        malformed_jsonl_line_count=len(issues),
        h200_available=True,
        status="completed_with_malformed_lines" if issues else "completed",
    )
    write_json(
        destination / "h200_build_status.json",
        {
            **result.to_dict(),
            "malformed_jsonl_issues": [asdict(issue) for issue in issues],
        },
    )
    return result


def append_exclusions_csv(path: str | Path, frame: Any, *, header: bool) -> None:
    """Append a bounded DataFrame batch to the human-readable exclusion log."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    copy = frame.copy()
    for column in EXCLUSION_COLUMNS:
        if column not in copy.columns:
            copy[column] = None
    copy.loc[:, EXCLUSION_COLUMNS].to_csv(destination, mode="a", header=header, index=False)


def read_processed_table(path: str | Path) -> Any:
    """Read a Parquet or CSV table into pandas, returning an empty frame if absent."""

    import pandas as pd

    source = Path(path)
    if source.exists():
        if source.suffix == ".parquet":
            return pd.read_parquet(source)
        return pd.read_csv(source)
    alternative = (
        source.with_suffix(".csv")
        if source.suffix == ".parquet"
        else source.with_suffix(".parquet")
    )
    if alternative.exists():
        return read_processed_table(alternative)
    return pd.DataFrame()


def write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        json.dump(dict(payload), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _sanitize_row(row: Mapping[str, Any], columns: Iterable[str]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for column in columns:
        value = row.get(column)
        if _is_missing(value):
            clean[column] = None
        elif hasattr(value, "item"):
            try:
                clean[column] = value.item()
            except (TypeError, ValueError):
                clean[column] = value
        else:
            clean[column] = value
    return clean


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if type(value).__name__ == "NAType":
        return True
    try:
        # Handles pandas.NA and NumPy NaN without importing either dependency.
        return bool(value != value)
    except (TypeError, ValueError):
        return False


def _profile_context(
    profile_path: Path,
    artifact: ArtifactInfo | None,
    *,
    github_run_id: int | str | None,
    environment: Mapping[str, Any],
) -> dict[str, Any]:
    concurrency = (
        artifact.concurrency if artifact is not None else _concurrency_from_path(profile_path)
    )
    return {
        "github_run_id": github_run_id,
        "artifact_id": artifact.artifact_id if artifact is not None else None,
        "artifact_name": artifact.name if artifact is not None else None,
        "concurrency": concurrency,
        "target_model": environment.get("target_model"),
        "target_precision": _target_precision(artifact, environment),
        "target_hardware": environment.get("hardware"),
        "target_gpu_count": environment.get("total_gpus"),
        "framework": environment.get("framework"),
    }


def _concurrency_from_path(path: Path) -> int | None:
    for component in reversed(path.parts):
        parsed = parse_concurrency(component)
        if parsed is not None:
            return parsed
    return None


def _target_precision(artifact: ArtifactInfo | None, environment: Mapping[str, Any]) -> str | None:
    configured = environment.get("precision")
    if configured:
        return str(configured).upper()
    evidence = " ".join(
        str(value)
        for value in (
            artifact.name if artifact is not None else "",
            environment.get("target_model", ""),
        )
    ).lower()
    if "fp8" in evidence:
        return "FP8"
    if "bf16" in evidence:
        return "BF16"
    if "fp16" in evidence:
        return "FP16"
    return None


def _write_normalized_batch(
    rows: list[dict[str, Any]],
    all_writer: H200ParquetWriter,
    profiled_writer: H200ParquetWriter,
    exclusions_path: Path,
    *,
    header: bool,
    seen_fingerprints: set[str],
) -> tuple[tuple[int, int, int, int], bool]:
    import pandas as pd

    from .metrics import (
        add_derived_metrics,
        add_request_identity_key,
        exact_duplicate_fingerprints,
        filter_profile_records,
    )

    frame = pd.DataFrame(rows)
    fingerprints = exact_duplicate_fingerprints(frame)
    global_duplicate = fingerprints.isin(seen_fingerprints) | fingerprints.duplicated(keep="first")
    seen_fingerprints.update(value for value in fingerprints.dropna() if value)
    included, excluded = filter_profile_records(
        frame,
        # Source-compatible missing phase behavior is explicit in the output.
        missing_phase_is_profiling=True,
        require_itl=False,
        exclude_exact_duplicates=False,
    )
    classified = pd.concat([included, excluded], axis=0).sort_index()
    classified["is_exact_duplicate"] = (
        global_duplicate.reindex(classified.index).fillna(False).astype(bool)
    )
    classified = add_request_identity_key(add_derived_metrics(classified))
    included = classified.loc[classified["is_profiled_valid"].fillna(False)].copy()
    excluded = classified.loc[~classified["is_profiled_valid"].fillna(False)].copy()
    all_writer.write_rows(classified.to_dict(orient="records"))
    profiled_writer.write_rows(included.to_dict(orient="records"))
    if not excluded.empty:
        append_exclusions_csv(exclusions_path, excluded, header=header)
        header = False
    return (len(classified), len(included), len(excluded), int(global_duplicate.sum())), header
