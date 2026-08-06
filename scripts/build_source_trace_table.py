#!/usr/bin/env python3
"""Flatten the public source workload JSONL into streaming Parquet tables."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from h200_agentx_analysis.config import configured_path, load_run_config  # noqa: E402
from h200_agentx_analysis.hf_trace_parser import TraceParseError  # noqa: E402
from h200_agentx_analysis.source_flattening import (  # noqa: E402
    DuplicateRootTraceIdError,
    ParquetDependencyError,
    build_source_trace_tables,
)

DEFAULT_INPUT = (
    REPOSITORY_ROOT
    / "data/raw/huggingface/cc-traces-weka-062126/traces.jsonl"
)
DEFAULT_OUTPUT_DIR = REPOSITORY_ROOT / "data/processed"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create source_trace_summary.parquet and source_requests.parquet from "
            "cc-traces-weka-062126 traces.jsonl."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="optional run YAML; its analysis.source_trace_file and analysis.processed_dir are used by default",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help=f"source JSONL path (default: {DEFAULT_INPUT}, or analysis.source_trace_file from --config)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help=f"processed table directory (default: {DEFAULT_OUTPUT_DIR}, or analysis.processed_dir from --config)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10_000,
        help="maximum request rows held before a Parquet row-group write (default: 10000)",
    )
    parser.add_argument(
        "--missing-policy",
        choices=("error", "empty"),
        default="error",
        help=(
            "error stops when the raw dataset has not been acquired; empty writes valid zero-row "
            "Parquet placeholders and reports source_available=false"
        ),
    )
    parser.add_argument(
        "--allow-duplicate-root-ids",
        action="store_true",
        help="write duplicate roots only for forensic inspection; default rejects them",
    )
    return parser.parse_args()


def _resolve_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.config is None:
        return args.input or DEFAULT_INPUT, args.output_dir or DEFAULT_OUTPUT_DIR
    config = load_run_config(args.config)
    input_path = args.input or configured_path(config, "source_trace_file")
    output_dir = args.output_dir or configured_path(config, "processed_dir")
    return input_path, output_dir


def main() -> int:
    args = parse_args()
    if args.batch_size < 1:
        print("--batch-size must be a positive integer", file=sys.stderr)
        return 2
    try:
        input_path, output_dir = _resolve_paths(args)
        result = build_source_trace_tables(
            input_path,
            output_dir,
            batch_size=args.batch_size,
            missing_policy=args.missing_policy,
            allow_duplicate_root_ids=args.allow_duplicate_root_ids,
        )
    except (
        FileNotFoundError,
        KeyError,
        ParquetDependencyError,
        DuplicateRootTraceIdError,
        TraceParseError,
        ValueError,
    ) as exc:
        print(f"build-source blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
