"""Inventory and safely acquire the public GitHub Actions artifacts.

Authentication is intentionally delegated to the local ``gh`` credential
store.  No token is read, emitted, or written by this module.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import zipfile
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .artifact_parser import parse_artifact_inventory
from .provenance import read_json, sha256_file, utc_now, write_json

TARGET_CATEGORIES = {"raw_agentic", "aggregated_agentic", "run_summary"}


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


def _download_archive(command: list[str], *, cwd: Path, destination: Path) -> bool:
    """Stream a GitHub CLI binary response to an archive without exposing stderr.

    Modern ``gh api`` deliberately has no ``--output`` flag.  Passing an open
    binary handle avoids shell redirection, keeps archive bytes out of memory,
    and leaves terminal error text out of reproducibility manifests (where it
    could inadvertently contain credential-bearing URLs).
    """

    with destination.open("wb") as handle:
        result = subprocess.run(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=handle,
            stderr=subprocess.PIPE,
            check=False,
        )
    return result.returncode == 0


def _gh_json(endpoint: str, root: Path, *, paginate: bool = False) -> dict[str, Any]:
    command = ["gh", "api", endpoint]
    if paginate:
        command += ["--paginate", "--slurp"]
    result = _run(command, cwd=root)
    if result.returncode:
        return _public_json(endpoint, paginate=paginate)
    parsed = json.loads(result.stdout)
    if paginate and isinstance(parsed, list):
        merged: list[Any] = []
        total_count: int | None = None
        for page in parsed:
            if not isinstance(page, dict):
                raise ValueError(f"Unexpected paginated JSON page from {endpoint}")
            total_count = page.get("total_count", total_count)
            merged.extend(page.get("artifacts", []))
        return {"total_count": total_count if total_count is not None else len(merged), "artifacts": merged}
    if not isinstance(parsed, dict):
        raise ValueError(f"Unexpected JSON payload from {endpoint}")
    return parsed


def _public_json(endpoint: str, *, paginate: bool) -> dict[str, Any]:
    """Use unauthenticated GitHub REST metadata as a safe fallback for public runs."""
    base = f"https://api.github.com/{endpoint.lstrip('/')}"
    pages: list[dict[str, Any]] = []
    page = 1
    try:
        while True:
            query = urlencode({"per_page": 100, "page": page}) if paginate else ""
            request = Request(
                f"{base}?{query}" if query else base,
                headers={"Accept": "application/vnd.github+json", "User-Agent": "h200-agentx-analysis"},
            )
            with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed public GitHub API origin
                decoded = json.loads(response.read().decode("utf-8"))
            if not isinstance(decoded, dict):
                raise ValueError("GitHub API response was not an object")
            pages.append(decoded)
            artifacts = decoded.get("artifacts")
            if not paginate or not isinstance(artifacts, list) or len(artifacts) < 100:
                break
            page += 1
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"public GitHub metadata request failed for {endpoint}: {type(exc).__name__}") from exc
    if not paginate:
        return pages[0]
    combined = [artifact for payload in pages for artifact in payload.get("artifacts", [])]
    return {"total_count": pages[0].get("total_count", len(combined)), "artifacts": combined}


def _auth_available(root: Path) -> bool:
    return _run(["gh", "auth", "status"], cwd=root).returncode == 0


def _clean_name(value: object) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "artifact"))


def _artifact_directory(base: Path, row: dict[str, Any]) -> Path:
    concurrency = row.get("concurrency")
    category = str(row.get("category") or "other")
    parent = base / (f"conc{concurrency}" if concurrency else "summary") / category
    return parent / f"{row['artifact_id']}_{_clean_name(row['name'])}"


def _safe_extract(zip_path: Path, destination: Path) -> list[str]:
    """Validate and extract an archive, or safely reuse its existing extraction.

    A rerun should reuse a digest-verified archive rather than fail merely
    because its already-validated files are present.  The reuse branch still
    checks ZIP CRCs, member paths, and the full expected file list so a partial
    extraction cannot be silently trusted.
    """

    if destination.is_symlink():
        raise ValueError(f"destination must not be a symlink: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        corrupt_member = archive.testzip()
        if corrupt_member is not None:
            raise zipfile.BadZipFile(f"CRC check failed for ZIP member: {corrupt_member}")
        members = archive.infolist()
        files: list[str] = []
        for member in members:
            target = (destination / member.filename).resolve()
            if target != root and root not in target.parents:
                raise ValueError(f"unsafe ZIP member path: {member.filename!r}")
            if not member.is_dir():
                files.append(member.filename)
        if any(destination.iterdir()):
            missing = [name for name in files if not (destination / name).is_file()]
            if missing:
                raise ValueError(
                    "existing extraction is incomplete; missing ZIP member(s): "
                    + ", ".join(missing[:3])
                )
        else:
            archive.extractall(destination)
    return sorted(files)


def _expected_target_ids(config: dict[str, Any]) -> set[int]:
    expected = config.get("github", {}).get("expected_artifacts", {})
    return {
        int(artifact_id)
        for category in ("raw_agentic", "aggregated_agentic", "run_summary")
        for artifact_id in (expected.get(category) or {}).values()
    }


def _inventory_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for artifact in parse_artifact_inventory(payload):
        rows.append(
            {
                "artifact_id": int(artifact.artifact_id),
                "name": artifact.name,
                "category": artifact.category,
                "concurrency": artifact.concurrency,
                "size_in_bytes": artifact.size_in_bytes,
                "expected_digest": artifact.digest,
                "expired": artifact.expired,
                "created_at": artifact.created_at,
                "expires_at": artifact.expires_at,
                "workflow_run_head_sha": artifact.head_sha,
            }
        )
    return rows


def _inventory_validation(run: dict[str, Any], rows: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    github = config["github"]
    by_id = {int(row["artifact_id"]): row for row in rows}
    expected_raw: dict[int, int] = {
        int(artifact_id): int(concurrency)
        for concurrency, artifact_id in github["expected_artifacts"]["raw_agentic"].items()
    }
    expected_aggregate: dict[int, int] = {
        int(artifact_id): int(concurrency)
        for concurrency, artifact_id in github["expected_artifacts"]["aggregated_agentic"].items()
    }
    expected_summary = {int(value) for value in github["expected_artifacts"]["run_summary"].values()}
    missing = sorted((set(expected_raw) | set(expected_aggregate) | expected_summary) - set(by_id))
    category_mismatches: list[int] = []
    concurrency_mismatches: list[int] = []
    for artifact_id, concurrency in expected_raw.items():
        row = by_id.get(artifact_id)
        if row and row["category"] != "raw_agentic":
            category_mismatches.append(artifact_id)
        if row and row["concurrency"] != concurrency:
            concurrency_mismatches.append(artifact_id)
    for artifact_id, concurrency in expected_aggregate.items():
        row = by_id.get(artifact_id)
        if row and row["category"] != "aggregated_agentic":
            category_mismatches.append(artifact_id)
        if row and row["concurrency"] != concurrency:
            concurrency_mismatches.append(artifact_id)
    for artifact_id in expected_summary:
        row = by_id.get(artifact_id)
        if row and row["category"] != "run_summary":
            category_mismatches.append(artifact_id)
    target_rows = [row for row in rows if int(row["artifact_id"]) in set(expected_raw) | set(expected_aggregate) | expected_summary]
    return {
        "run_head_sha_matches_expected": run.get("head_sha") == github.get("expected_head_sha"),
        "run_branch_matches_expected": run.get("head_branch") == github.get("expected_branch"),
        "expected_target_artifact_count": len(expected_raw) + len(expected_aggregate) + len(expected_summary),
        "found_target_artifact_count": len(target_rows),
        "missing_expected_artifact_ids": missing,
        "category_mismatch_artifact_ids": sorted(set(category_mismatches)),
        "concurrency_mismatch_artifact_ids": sorted(set(concurrency_mismatches)),
        "target_artifacts_expired": sorted(int(row["artifact_id"]) for row in target_rows if row["expired"] is True),
        "raw_concurrency_1_to_8_present": sorted(
            row["concurrency"] for row in target_rows if row["category"] == "raw_agentic"
        ),
        "aggregate_concurrency_1_to_8_present": sorted(
            row["concurrency"] for row in target_rows if row["category"] == "aggregated_agentic"
        ),
    }


def _download_one(
    root: Path,
    repository: str,
    row: dict[str, Any],
    output_dir: Path,
    *,
    auth_available: bool,
) -> dict[str, Any]:
    destination = _artifact_directory(output_dir, row)
    archive_path = destination.with_suffix(".zip")
    record: dict[str, Any] = {
        **row,
        "download_timestamp": utc_now(),
        "local_path": str(destination.relative_to(root)),
        "archive_path": str(archive_path.relative_to(root)),
        "local_sha256": None,
        "extracted_files": [],
        "download_status": "not_attempted",
        "zip_validation": "not_attempted",
        "profile_export_found": False,
        "aggregate_json_found": False,
    }
    if row["expired"] is True:
        record.update(download_status="blocked_expired", zip_validation="not_attempted")
        return record
    expected_digest = str(row.get("expected_digest") or "")
    if archive_path.exists() and zipfile.is_zipfile(archive_path):
        local_digest = sha256_file(archive_path)
        record["local_sha256"] = f"sha256:{local_digest}"
        record["zip_validation"] = "digest_match" if not expected_digest or record["local_sha256"] == expected_digest else "digest_mismatch"
        if record["zip_validation"] == "digest_mismatch":
            record["download_status"] = "integrity_failed"
            return record
        try:
            record["extracted_files"] = _safe_extract(archive_path, destination)
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            record.update(download_status="extract_failed", error=f"{type(exc).__name__}: {exc}")
            return record
        record["download_status"] = "reused_verified_archive"
    elif not auth_available:
        record["download_status"] = "blocked_gh_auth"
        return record
    else:
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        endpoint = f"repos/{repository}/actions/artifacts/{row['artifact_id']}/zip"
        command = ["gh", "api", endpoint]
        if not _download_archive(command, cwd=root, destination=archive_path):
            archive_path.unlink(missing_ok=True)
            record.update(
                download_status="download_failed",
                error="GitHub CLI artifact download failed; terminal output intentionally not persisted",
            )
            return record
        if not zipfile.is_zipfile(archive_path):
            archive_path.unlink(missing_ok=True)
            record["download_status"] = "download_not_zip"
            return record
        local_digest = sha256_file(archive_path)
        record["local_sha256"] = f"sha256:{local_digest}"
        record["zip_validation"] = "digest_match" if not expected_digest or record["local_sha256"] == expected_digest else "digest_mismatch"
        if record["zip_validation"] == "digest_mismatch":
            record["download_status"] = "integrity_failed"
            return record
        try:
            record["extracted_files"] = _safe_extract(archive_path, destination)
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            record.update(download_status="extract_failed", error=f"{type(exc).__name__}: {exc}")
            return record
        record["download_status"] = "downloaded_and_verified"
    files = set(record["extracted_files"])
    record["profile_export_found"] = any(Path(name).name == "profile_export.jsonl" for name in files)
    record["aggregate_json_found"] = any(name.endswith(".json") for name in files)
    if row["category"] == "raw_agentic" and not record["profile_export_found"]:
        record["download_status"] = "validation_failed_missing_profile_export"
    if row["category"] == "aggregated_agentic" and not record["aggregate_json_found"]:
        record["download_status"] = "validation_failed_missing_aggregate_json"
    return record


def _write_needs_input(root: Path, records: list[dict[str, Any]]) -> None:
    if not any(row["download_status"] == "blocked_gh_auth" for row in records):
        return
    path = root / "NEEDS_INPUT.md"
    marker = "## GitHub Actions artifact downloads are blocked"
    current = path.read_text(encoding="utf-8") if path.exists() else "# Inputs that may still be needed\n"
    if marker in current:
        return
    ids = ", ".join(str(row["artifact_id"]) for row in records if row["download_status"] == "blocked_gh_auth")
    addition = (
        f"\n{marker}\n\n"
        "**Evidence:** public run and artifact inventory metadata was retrieved, but the local GitHub CLI "
        "is not authenticated to download Actions artifact ZIPs.\n\n"
        "**Needed input:** authenticate outside this repository; do not paste a token into chat or source files.\n\n"
        "```sh\ngh auth login --web --git-protocol ssh\ngh auth status\nmake acquire-run\n```\n\n"
        f"Target artifact IDs: `{ids}`.\n"
    )
    path.write_text(current.rstrip() + "\n" + addition, encoding="utf-8")


def _record_download_provenance(
    root: Path,
    *,
    repository: str,
    run_id: int,
    metadata_source: str,
    records: list[dict[str, Any]],
) -> None:
    """Record a compact, credential-free acquisition outcome alongside the ledger.

    ``downloads.json`` remains the authoritative per-artifact ledger.  This
    summary lets the stable provenance record distinguish a completed,
    digest-verified acquisition from an intentionally blocked fresh checkout.
    """

    provenance_path = root / "manifests" / "provenance.json"
    provenance = read_json(provenance_path, {}) or {}
    if not isinstance(provenance, dict):
        provenance = {}
    verified_statuses = {"downloaded_and_verified", "reused_verified_archive"}
    verified = [
        row
        for row in records
        if row.get("download_status") in verified_statuses and row.get("zip_validation") == "digest_match"
    ]
    raw_profiles = sum(
        row.get("category") == "raw_agentic" and bool(row.get("profile_export_found")) for row in verified
    )
    aggregates = sum(
        row.get("category") == "aggregated_agentic" and bool(row.get("aggregate_json_found")) for row in verified
    )
    failures = [
        row for row in records if str(row.get("download_status", "")).startswith(("download_", "integrity_", "extract_", "validation_"))
    ]
    blocked = [row for row in records if str(row.get("download_status", "")).startswith("blocked_")]
    status = (
        "complete_and_digest_verified"
        if records and len(verified) == len(records)
        else "blocked" if blocked and not failures else "incomplete_or_failed"
    )
    provenance["github_actions_artifact_download"] = {
        "status": status,
        "recorded_at_utc": utc_now(),
        "repository": repository,
        "run_id": run_id,
        "metadata_source": metadata_source,
        "target_artifact_count": len(records),
        "digest_verified_archive_count": len(verified),
        "raw_profile_export_count": raw_profiles,
        "aggregated_json_artifact_count": aggregates,
        "blocked_artifact_count": len(blocked),
        "failed_artifact_count": len(failures),
        "per_artifact_ledger": "manifests/downloads.json",
    }
    limitations = provenance.get("acquisition_limitations")
    if isinstance(limitations, dict) and status == "complete_and_digest_verified":
        limitations["github_actions_artifact_zip_endpoint"] = (
            "resolved: authenticated GitHub CLI acquisition completed; all target ZIP SHA-256 values matched API digests"
        )
        limitations["github_cli_authentication"] = (
            "authenticated acquisition was verified without storing a credential in this repository"
        )
    write_json(provenance_path, provenance)


def _saved_metadata_fallback(root: Path, *, run_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
    """Reuse prior public metadata only when live public metadata is unreachable."""
    run_path = root / "manifests" / "github_run.json"
    artifact_path = root / "manifests" / "github_artifacts.json"
    if not run_path.exists() or not artifact_path.exists():
        raise FileNotFoundError("no saved public GitHub metadata is available for fallback")
    run = json.loads(run_path.read_text(encoding="utf-8"))
    artifacts = json.loads(artifact_path.read_text(encoding="utf-8"))
    if not isinstance(run, dict) or int(run.get("id", -1)) != run_id or not isinstance(artifacts, dict):
        raise ValueError("saved GitHub metadata does not match the requested run")
    return run, artifacts


def acquire(root: Path, config: dict[str, Any], *, download: bool = True) -> dict[str, Any]:
    github = config["github"]
    repository, run_id = str(github["repository"]), int(github["run_id"])
    try:
        run = _gh_json(f"repos/{repository}/actions/runs/{run_id}", root)
        artifacts = _gh_json(f"repos/{repository}/actions/runs/{run_id}/artifacts", root, paginate=True)
        metadata_source = "live_github_api"
        write_json(root / "manifests" / "github_run.json", run)
        write_json(root / "manifests" / "github_artifacts.json", artifacts)
    except RuntimeError:
        run, artifacts = _saved_metadata_fallback(root, run_id=run_id)
        metadata_source = "saved_manifest_fallback_live_api_unavailable"
    rows = _inventory_rows(artifacts)
    validation = _inventory_validation(run, rows, config)
    by_id = {int(row["artifact_id"]): row for row in rows}
    target_ids = _expected_target_ids(config)
    selected = [by_id[artifact_id] for artifact_id in sorted(target_ids) if artifact_id in by_id]
    auth_available = _auth_available(root)
    records = (
        [
            _download_one(
                root,
                repository,
                row,
                root / config["analysis"]["raw_github_dir"],
                auth_available=auth_available,
            )
            for row in selected
        ]
        if download
        else []
    )
    manifest = {
        "generated_at_utc": utc_now(),
        "github_repository": repository,
        "github_run_id": run_id,
        "metadata_source": metadata_source,
        "inventory_validation": validation,
        "artifacts": records,
    }
    write_json(root / "manifests" / "downloads.json", manifest)
    _record_download_provenance(
        root,
        repository=repository,
        run_id=run_id,
        metadata_source=metadata_source,
        records=records,
    )
    _write_needs_input(root, records)
    return {"run": run, "artifact_rows": rows, "downloads": records, "inventory_validation": validation}


def main() -> int:
    from .config import load_run_config, repository_root

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/run_29820102138.yaml")
    parser.add_argument("--inventory-only", action="store_true")
    args = parser.parse_args()
    root = repository_root()
    try:
        outcome = acquire(root, load_run_config(args.config), download=not args.inventory_only)
    except Exception as exc:
        print(f"GitHub acquisition failed before an inventory could be saved: {exc}")
        return 2
    records = outcome["downloads"]
    blocked = sum(row["download_status"].startswith("blocked_") for row in records)
    failures = sum(
        row["download_status"] in {"download_failed", "download_not_zip", "integrity_failed", "extract_failed"}
        or row["download_status"].startswith("validation_failed")
        for row in records
    )
    if failures:
        print(f"Artifact acquisition completed with {failures} validation/download failure(s); see manifests/downloads.json")
        return 2
    if blocked:
        print(f"Artifact acquisition is explicitly blocked for {blocked} target artifact(s); see NEEDS_INPUT.md")
        return 0
    print(f"Stored run metadata and verified {len(records)} target artifact archive(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
