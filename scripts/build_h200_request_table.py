#!/usr/bin/env python3
"""Build canonical H200 all/profiled request tables from raw profile exports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from h200_agentx_analysis.config import configured_path, load_run_config  # noqa: E402
from h200_agentx_analysis.h200_io import (  # noqa: E402
    ParquetDependencyError,
    build_h200_request_tables,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stream profile_export.jsonl files into canonical H200 request Parquet tables."
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
        help="saved GitHub artifact inventory used to attach IDs/names",
    )
    parser.add_argument("--batch-size", type=int, default=10_000)
    parser.add_argument(
        "--missing-policy",
        choices=("empty", "error"),
        default="empty",
        help="empty writes explicit zero-row outputs when acquisition is blocked (default)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.batch_size < 1:
        print("--batch-size must be positive", file=sys.stderr)
        return 2
    try:
        config = load_run_config(args.config)
        raw_root = args.raw_root or configured_path(config, "raw_github_dir")
        output_dir = args.output_dir or configured_path(config, "processed_dir")
        result = build_h200_request_tables(
            raw_root,
            output_dir,
            github_run_id=config.get("github", {}).get("run_id"),
            expected_environment=config.get("expected_environment", {}),
            artifact_inventory_path=args.artifact_inventory,
            batch_size=args.batch_size,
            missing_policy=args.missing_policy,
        )
    except (FileNotFoundError, ValueError, ParquetDependencyError) as exc:
        print(f"build-h200 blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
