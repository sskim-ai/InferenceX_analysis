#!/usr/bin/env python3
"""Inventory and acquire the public GPU-resident MTP Actions artifacts.

The script never emits credentials.  Raw archives and extracted JSONL/logs
remain under ``data/raw/h200_gpu_resident_mtp`` and are ignored by Git; only
the compact artifact ledger and provenance are versioned under the study.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from h200_agentx_analysis.artifact_parser import (  # noqa: E402
    artifact_category,
    parse_artifact_inventory,
)

OWNER_REPO = "SemiAnalysisAI/InferenceX"
RUN_ID = 31235207041
EXPECTED: dict[int, dict[str, int]] = {
    8: {"result": 9017979109, "aggregate": 9017975161, "server_logs": 9017974866},
    12: {"result": 9019209525, "aggregate": 9019205268, "server_logs": 9019204997},
    16: {"result": 9020484364, "aggregate": 9020480067, "server_logs": 9020479786},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-root", type=Path, default=REPOSITORY_ROOT / "data/raw/h200_gpu_resident_mtp"
    )
    parser.add_argument(
        "--study-root", type=Path, default=REPOSITORY_ROOT / "studies/h200_gpu_resident_mtp"
    )
    parser.add_argument("--download", action="store_true", help="download/extract missing expected artifacts")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _gh(["auth", "status"])
    run = _gh_json(["api", f"repos/{OWNER_REPO}/actions/runs/{RUN_ID}"])
    inventory = _gh_json(["api", f"repos/{OWNER_REPO}/actions/runs/{RUN_ID}/artifacts", "--paginate"])
    args.raw_root.mkdir(parents=True, exist_ok=True)
    _write_json(args.raw_root / "run.json", run)
    _write_json(args.raw_root / "run_artifacts.json", inventory)
    items = {str(item.artifact_id): item for item in parse_artifact_inventory(inventory)}
    raw_items = _artifact_payloads(inventory)
    rows: list[dict[str, Any]] = []
    for concurrency, types in EXPECTED.items():
        for destination_type, artifact_id in types.items():
            raw_item = raw_items.get(str(artifact_id), {})
            item = items.get(str(artifact_id))
            destination = args.raw_root / f"conc{concurrency}" / destination_type / str(artifact_id)
            archive = destination.parent / f"{artifact_id}.zip"
            if args.download and not archive.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                _gh(["api", f"repos/{OWNER_REPO}/actions/artifacts/{artifact_id}/zip", "--output", str(archive)])
            extracted_files: list[str] = []
            if archive.exists():
                if not destination.exists() or not any(destination.iterdir()):
                    _safe_extract(archive, destination)
                extracted_files = sorted(
                    str(path.relative_to(args.raw_root))
                    for path in destination.rglob("*")
                    if path.is_file()
                )
            local_sha = _sha256(archive) if archive.exists() else None
            expected_digest = raw_item.get("digest")
            digest_match = _digest_match(expected_digest, local_sha)
            rows.append(
                {
                    "run_id": RUN_ID,
                    "concurrency": concurrency,
                    "destination_type": destination_type,
                    "artifact_id": artifact_id,
                    "artifact_name": getattr(item, "name", raw_item.get("name")),
                    "artifact_category": getattr(item, "category", artifact_category(raw_item.get("name"))),
                    "size_in_bytes": raw_item.get("size_in_bytes"),
                    "github_digest": expected_digest,
                    "expired": raw_item.get("expired"),
                    "created_at": raw_item.get("created_at"),
                    "expires_at": raw_item.get("expires_at"),
                    "workflow_run_head_sha": (raw_item.get("workflow_run") or {}).get("head_sha"),
                    "download_status": "present" if archive.exists() else "not_downloaded",
                    "local_zip_sha256": local_sha,
                    "github_digest_match": digest_match,
                    "local_archive_path": str(archive.relative_to(REPOSITORY_ROOT)) if archive.exists() else None,
                    "extracted_file_count": len(extracted_files),
                    "extracted_files": ";".join(extracted_files),
                }
            )
    manifests = args.study_root / "manifests"
    manifests.mkdir(parents=True, exist_ok=True)
    _write_csv(manifests / "artifact_inventory.csv", rows)
    _write_json(
        manifests / "provenance.json",
        {
            "schema_version": "h200_gpu_resident_mtp.acquisition.v1",
            "retrieved_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "github": {
                "repository": OWNER_REPO,
                "run_id": RUN_ID,
                "run_head_sha": run.get("head_sha"),
                "head_branch": run.get("head_branch"),
                "event": run.get("event"),
                "conclusion": run.get("conclusion"),
            },
            "expected_artifact_ids": EXPECTED,
            "artifact_inventory_path": "studies/h200_gpu_resident_mtp/manifests/artifact_inventory.csv",
            "raw_data_policy": "Raw ZIPs, extracted logs, JSONL, and Parquet remain local and ignored by Git.",
        },
    )
    missing = sum(row["download_status"] != "present" for row in rows)
    print(json.dumps({"artifact_rows": len(rows), "missing": missing}, ensure_ascii=False))
    return 0 if not missing or not args.download else 2


def _gh(arguments: list[str]) -> None:
    completed = subprocess.run(["gh", *arguments], check=False, capture_output=True, text=True)
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip() or "gh command failed"
        raise RuntimeError(detail)


def _gh_json(arguments: list[str]) -> dict[str, Any]:
    completed = subprocess.run(["gh", *arguments], check=False, capture_output=True, text=True)
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip() or "gh API command failed"
        raise RuntimeError(detail)
    value = json.loads(completed.stdout)
    if not isinstance(value, dict):
        raise ValueError("GitHub API returned a non-object payload")
    return value


def _artifact_payloads(inventory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values = inventory.get("artifacts", [])
    return {
        str(item.get("id")): item
        for item in values
        if isinstance(item, dict) and item.get("id") is not None
    }


def _safe_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    base = destination.resolve()
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            target = (destination / member.filename).resolve()
            if target != base and base not in target.parents:
                raise ValueError(f"unsafe ZIP member path: {member.filename}")
        zipped.extractall(destination)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest_match(expected: Any, local_sha: str | None) -> bool | None:
    if not expected or not local_sha:
        return None
    text = str(expected)
    return text.removeprefix("sha256:").lower() == local_sha.lower()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
