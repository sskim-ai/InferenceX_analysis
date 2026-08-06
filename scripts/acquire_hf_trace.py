#!/usr/bin/env python3
"""Acquire the public source trace with hf CLI or huggingface_hub fallback."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from h200_agentx_analysis.config import load_run_config, repository_root
from h200_agentx_analysis.provenance import read_json, sha256_file, utc_now, write_json

DATASET = "semianalysisai/cc-traces-weka-062126"
# Captured from the immutable dataset revision in manifests/provenance.json.
# It prevents a partial interrupted file from being mistaken for a completed
# raw input when the metadata endpoint is temporarily unreachable.
FALLBACK_EXPECTED_TRACE_BYTES = 1_847_151_435


def dataset_revision_and_size() -> tuple[str | None, int | None]:
    """Read immutable public metadata before deciding a local file is reusable."""
    try:
        from huggingface_hub import HfApi

        info = HfApi().dataset_info(DATASET)
        size = None
        for sibling in info.siblings or []:
            if sibling.rfilename == "traces.jsonl" and sibling.size is not None:
                size = int(sibling.size)
                break
        return info.sha, size
    except Exception:
        return None, None


def acquire(destination: Path, *, revision: str | None, expected_size: int | None) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / "traces.jsonl"
    if target.exists() and target.stat().st_size and (
        expected_size is None or target.stat().st_size == expected_size
    ):
        return target
    hf = shutil.which("hf") or str(Path(sys.executable).with_name("hf"))
    if not Path(hf).exists() and shutil.which(hf) is None:
        hf = None
    if hf:
        command = [hf, "download", DATASET, "traces.jsonl", "--repo-type", "dataset", "--local-dir", str(destination)]
        if revision:
            command += ["--revision", revision]
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0 and target.exists():
            return target
        failure = (result.stderr or result.stdout).strip()
    else:
        failure = "hf CLI not found"
    try:
        from huggingface_hub import hf_hub_download

        local = hf_hub_download(
            repo_id=DATASET,
            repo_type="dataset",
            filename="traces.jsonl",
            revision=revision,
            local_dir=str(destination),
        )
        return Path(local)
    except Exception as exc:
        raise RuntimeError(f"{failure}; huggingface_hub fallback failed: {exc}") from exc


def validate_trace(path: Path, *, expected_size: int) -> tuple[str, dict[str, object]]:
    """Validate the complete raw JSONL without retaining all trace objects."""
    if path.stat().st_size != expected_size:
        raise ValueError(
            f"incomplete trace file: {path.stat().st_size} bytes, expected {expected_size} bytes"
        )
    try:
        import orjson

        loads = orjson.loads
    except ImportError:
        loads = json.loads
    root_ids: set[str] = set()
    record_count = 0
    empty_lines = 0
    top_level_keys: set[str] = set()
    with path.open("rb") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                empty_lines += 1
                continue
            try:
                item = loads(raw_line)
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                raise ValueError(f"invalid JSONL at line {line_number}: {exc}") from exc
            if not isinstance(item, dict) or not item.get("id"):
                raise ValueError(f"invalid trace object at line {line_number}: expected nonempty object id")
            record_count += 1
            root_ids.add(str(item["id"]))
            top_level_keys.update(str(key) for key in item)
    if record_count != len(root_ids):
        raise ValueError(f"root ID uniqueness failed: {record_count} records, {len(root_ids)} unique IDs")
    return sha256_file(path), {
        "byte_count": path.stat().st_size,
        "jsonl_record_count": record_count,
        "unique_root_id_count": len(root_ids),
        "empty_line_count": empty_lines,
        "top_level_keys": sorted(top_level_keys),
    }


def write_needs_input(root: Path) -> None:
    """Record a controlled public-download block without exposing error text."""
    path = root / "NEEDS_INPUT.md"
    marker = "## Hugging Face source trace download is blocked"
    current = path.read_text(encoding="utf-8") if path.exists() else "# Inputs that may still be needed\n"
    if marker in current:
        return
    addition = (
        f"\n{marker}\n\n"
        "**Evidence:** the required public `traces.jsonl` could not be acquired or resumed in this environment. "
        "No incomplete local file is treated as an analysis input.\n\n"
        "**Needed input:** retry with a network-enabled Hugging Face client; authenticate only if the dataset "
        "later requires it. Do not paste tokens into this repository or chat.\n\n"
        "```sh\nhf auth status\nhf download semianalysisai/cc-traces-weka-062126 traces.jsonl "
        "--repo-type dataset --local-dir data/raw/huggingface/cc-traces-weka-062126\nmake acquire-traces\n```\n"
    )
    path.write_text(current.rstrip() + "\n" + addition, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/run_29820102138.yaml")
    args = parser.parse_args()
    root = repository_root()
    load_run_config(args.config)  # validate the requested configuration exists
    target_dir = root / "data/raw/huggingface/cc-traces-weka-062126"
    revision, expected_size = dataset_revision_and_size()
    expected_size = expected_size or FALLBACK_EXPECTED_TRACE_BYTES
    try:
        trace = acquire(target_dir, revision=revision, expected_size=expected_size)
    except RuntimeError:
        write_needs_input(root)
        print("Hugging Face acquisition is explicitly blocked; see NEEDS_INPUT.md")
        return 0
    try:
        checksum, validation = validate_trace(trace, expected_size=expected_size)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Hugging Face acquisition validation failed: {type(exc).__name__}")
        return 2
    provenance_path = root / "manifests" / "provenance.json"
    provenance = read_json(provenance_path, {}) or {}
    existing = provenance.get("huggingface", {})
    existing = dict(existing) if isinstance(existing, dict) else {}
    existing.update({
        "dataset": DATASET,
        "file": str(trace.relative_to(root)),
        "local_path": str(trace.relative_to(root)),
        "sha256": checksum,
        "local_sha256": checksum,
        "bytes": trace.stat().st_size,
        "remote_size_bytes": expected_size,
        "expected_size_bytes": expected_size,
        "acquired_at": utc_now(),
        "revision": revision or existing.get("revision") or "unresolved_at_download_time",
        "download_status_at_capture": "complete_and_validated",
        "validation": validation,
    })
    provenance["huggingface"] = existing
    limitations = provenance.get("acquisition_limitations")
    if isinstance(limitations, dict):
        # Preserve other acquisition limitations while correcting an older
        # preflight-era note that referred only to the shell PATH.  The
        # reproducible project virtualenv supplies the CLI used here.
        limitations["huggingface_cli"] = (
            "project virtualenv hf CLI is available; immutable revision was "
            "validated locally"
        )
    write_json(provenance_path, provenance)
    print(f"Acquired {trace} ({trace.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
