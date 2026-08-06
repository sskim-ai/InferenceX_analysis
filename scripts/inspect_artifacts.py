#!/usr/bin/env python3
"""Inventory every available H200 profile_export.jsonl schema in streaming mode."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from h200_agentx_analysis.artifact_parser import (  # noqa: E402
    find_profile_exports,
    infer_profile_context,
    iter_jsonl_records,
    load_artifact_inventory,
    normalize_profile_record,
    profile_schema_inventory,
)
from h200_agentx_analysis.config import configured_path, load_run_config  # noqa: E402
from h200_agentx_analysis.h200_io import write_json  # noqa: E402

SCHEMA_COLUMNS = [
    "concurrency",
    "artifact_id",
    "artifact_name",
    "source_file_path",
    "total_records",
    "field",
    "field_name",
    "canonical_field",
    "present_count",
    "presence_rate",
    "null_count",
    "null_rate",
    "null_rate_among_present",
    "dtype",
    "python_types",
    "min",
    "max",
    "numeric_min",
    "numeric_max",
    "observed_unit",
    "observed_unit_values",
    "unit_value_present_count",
    "inferred_unit",
]
METRIC_COLUMNS = [*SCHEMA_COLUMNS, "metric_key"]
COUNT_COLUMNS = [
    "concurrency",
    "artifact_id",
    "artifact_name",
    "source_file_path",
    "record_count",
    "profiling_phase_count",
    "warmup_count",
    "missing_phase_count",
    "error_count",
    "cancelled_count",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Streaming schema inventory for raw H200 profile exports."
    )
    parser.add_argument(
        "--config", type=Path, default=REPOSITORY_ROOT / "configs/run_29820102138.yaml"
    )
    parser.add_argument("--raw-root", type=Path, help="override analysis.raw_github_dir")
    parser.add_argument("--output-dir", type=Path, help="override analysis.processed_dir")
    parser.add_argument(
        "--artifact-inventory",
        type=Path,
        default=REPOSITORY_ROOT / "manifests/github_artifacts.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_run_config(args.config)
        raw_root = args.raw_root or configured_path(config, "raw_github_dir")
        output_dir = args.output_dir or configured_path(config, "processed_dir")
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"inspect blocked: {exc}", file=sys.stderr)
        return 2
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = load_artifact_inventory(args.artifact_inventory)
    profiles = find_profile_exports(raw_root)
    if not profiles:
        _write_empty(output_dir)
        status = {
            "status": "blocked_no_profile_export",
            "raw_root": str(raw_root),
            "profile_export_count": 0,
            "next_command": "make acquire-run",
        }
        write_json(output_dir / "artifact_schema_status.json", status)
        print(json.dumps(status, ensure_ascii=False, sort_keys=True))
        return 0

    field_rows, metric_rows, issues = profile_schema_inventory(profiles)
    contexts = {str(path): infer_profile_context(path, artifacts) for path in profiles}
    schema = _attach_context(field_rows, contexts)
    metrics = _attach_context(metric_rows, contexts, metric=True)
    counts = _profile_counts(profiles, contexts)
    schema.to_csv(output_dir / "artifact_schema.csv", index=False)
    metrics.to_csv(output_dir / "metric_key_inventory.csv", index=False)
    counts.to_csv(output_dir / "artifact_profile_counts.csv", index=False)
    status = {
        "status": "completed_with_malformed_lines" if issues else "completed",
        "raw_root": str(raw_root),
        "profile_export_count": len(profiles),
        "schema_field_rows": int(len(schema)),
        "metric_key_rows": int(len(metrics)),
        "malformed_jsonl_line_count": len(issues),
        "malformed_jsonl_issues": [issue.__dict__ for issue in issues],
    }
    write_json(output_dir / "artifact_schema_status.json", status)
    print(json.dumps(status, ensure_ascii=False, sort_keys=True))
    return 0


def _attach_context(
    rows: list[dict], contexts: dict[str, object], *, metric: bool = False
) -> pd.DataFrame:
    output: list[dict] = []
    for row in rows:
        item = dict(row)
        artifact = contexts.get(str(item.get("source_file_path")))
        item["concurrency"] = getattr(artifact, "concurrency", None)
        item["artifact_id"] = getattr(artifact, "artifact_id", None)
        item["artifact_name"] = getattr(artifact, "name", None)
        item["field"] = item.get("field_name")
        item["dtype"] = item.get("python_types")
        item["null_rate"] = (
            item.get("null_count", 0) / item.get("total_records", 1)
            if item.get("total_records", 0)
            else 0.0
        )
        item["min"] = item.get("numeric_min")
        item["max"] = item.get("numeric_max")
        if metric:
            field = str(item.get("field_name") or "")
            parts = field.split(".")
            item["metric_key"] = (
                parts[-2] if len(parts) >= 2 and parts[-1] in {"value", "unit"} else parts[-1]
            )
        output.append(item)
    columns = METRIC_COLUMNS if metric else SCHEMA_COLUMNS
    frame = pd.DataFrame(output)
    for column in columns:
        if column not in frame:
            frame[column] = None
    return frame[columns]


def _profile_counts(profiles: list[Path], contexts: dict[str, object]) -> pd.DataFrame:
    rows: list[dict] = []
    for path in profiles:
        counters: Counter[str] = Counter()
        for _, record in iter_jsonl_records(path):
            counters["record_count"] += 1
            row = normalize_profile_record(record)
            phase = (row.get("benchmark_phase") or "").strip().lower()
            if phase in {"profiling", "profile"}:
                counters["profiling_phase_count"] += 1
            elif not phase:
                counters["missing_phase_count"] += 1
            else:
                counters["warmup_count"] += 1
            counters["error_count"] += int(bool(row.get("error_present")))
            counters["cancelled_count"] += int(bool(row.get("was_cancelled")))
        artifact = contexts.get(str(path))
        rows.append(
            {
                "concurrency": getattr(artifact, "concurrency", None),
                "artifact_id": getattr(artifact, "artifact_id", None),
                "artifact_name": getattr(artifact, "name", None),
                "source_file_path": str(path),
                **{column: int(counters[column]) for column in COUNT_COLUMNS[4:]},
            }
        )
    frame = pd.DataFrame(rows)
    for column in COUNT_COLUMNS:
        if column not in frame:
            frame[column] = None
    return frame[COUNT_COLUMNS]


def _write_empty(output_dir: Path) -> None:
    pd.DataFrame(columns=SCHEMA_COLUMNS).to_csv(output_dir / "artifact_schema.csv", index=False)
    pd.DataFrame(columns=METRIC_COLUMNS).to_csv(
        output_dir / "metric_key_inventory.csv", index=False
    )
    pd.DataFrame(columns=COUNT_COLUMNS).to_csv(
        output_dir / "artifact_profile_counts.csv", index=False
    )


if __name__ == "__main__":
    raise SystemExit(main())
