from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from h200_agentx_analysis.github_acquisition import _safe_extract


def _write_archive(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("nested/profile_export.jsonl", '{"metric": 1}\n')
        archive.writestr("summary/result.json", "{}\n")


def test_safe_extract_reuses_complete_existing_extraction(tmp_path: Path) -> None:
    archive_path = tmp_path / "artifact.zip"
    destination = tmp_path / "extracted"
    _write_archive(archive_path)

    expected = ["nested/profile_export.jsonl", "summary/result.json"]
    assert _safe_extract(archive_path, destination) == expected
    assert (destination / "nested/profile_export.jsonl").is_file()

    # A rerun validates the archive and complete member set before reuse.
    assert _safe_extract(archive_path, destination) == expected


def test_safe_extract_rejects_incomplete_existing_extraction(tmp_path: Path) -> None:
    archive_path = tmp_path / "artifact.zip"
    destination = tmp_path / "extracted"
    _write_archive(archive_path)
    _safe_extract(archive_path, destination)
    (destination / "summary/result.json").unlink()

    with pytest.raises(ValueError, match="existing extraction is incomplete"):
        _safe_extract(archive_path, destination)
