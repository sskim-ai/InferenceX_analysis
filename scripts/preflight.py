#!/usr/bin/env python3
"""Record tool availability without exposing authentication details."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
VENV_HF = ROOT / ".venv" / "bin" / "hf"


def command_version(command: list[str]) -> tuple[str, str]:
    if shutil.which(command[0]) is None:
        return "missing", ""
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    output = (completed.stdout or completed.stderr).strip().splitlines()
    return ("available" if completed.returncode == 0 else f"exit_{completed.returncode}", output[0] if output else "")


def main() -> int:
    analysis_python = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable
    tools = {
        "git": ["git", "--version"],
        "python3": ["python3", "--version"],
        "gh": ["gh", "--version"],
        # Keep the shell PATH result distinct from the reproducible project
        # environment.  In particular, a missing global CLI must not obscure
        # a usable `.venv/bin/hf` installed by `make bootstrap`.
        "hf (PATH)": ["hf", "--version"],
        "hf (project .venv)": [str(VENV_HF), "--version"],
        "huggingface_hub": [analysis_python, "-c", "import huggingface_hub; print(huggingface_hub.__version__)"],
        "unzip": ["unzip", "-v"],
        "jq": ["jq", "--version"],
        "sha256sum": ["sha256sum", "--version"],
        "shasum": ["shasum", "--version"],
        "pytest": [analysis_python, "-m", "pytest", "--version"],
        "ruff": [analysis_python, "-m", "ruff", "--version"],
    }
    rows = [(name, *command_version(command)) for name, command in tools.items()]
    git_status = subprocess.run(
        ["git", "status", "--short", "--branch"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    git_name = subprocess.run(["git", "config", "--get", "user.name"], cwd=ROOT, capture_output=True, text=True, check=False)
    git_email = subprocess.run(["git", "config", "--get", "user.email"], cwd=ROOT, capture_output=True, text=True, check=False)
    identity_state = "configured" if git_name.returncode == 0 and git_email.returncode == 0 else "not configured"
    gh_auth = subprocess.run(["gh", "auth", "status"], cwd=ROOT, capture_output=True, text=True, check=False)
    downloads_path = ROOT / "manifests" / "downloads.json"
    verified_archives = 0
    if downloads_path.exists():
        try:
            downloads = json.loads(downloads_path.read_text(encoding="utf-8"))
            verified_archives = sum(
                row.get("download_status") in {"downloaded_and_verified", "reused_verified_archive"}
                and row.get("zip_validation") == "digest_match"
                for row in downloads.get("artifacts", [])
                if isinstance(row, dict)
            )
        except (OSError, ValueError, json.JSONDecodeError):
            verified_archives = 0
    if gh_auth.returncode == 0:
        auth_state = "authenticated"
    elif verified_archives:
        auth_state = (
            "not verifiable from this sandboxed preflight; prior authenticated acquisition "
            f"verified {verified_archives} artifact ZIP(s)"
        )
    else:
        auth_state = "not authenticated or unavailable"
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    report = [
        "# 00. 사전 점검",
        "",
        f"- 실행 시각(UTC): `{timestamp}`",
        f"- 플랫폼: `{platform.platform()}`",
        f"- Python executable: `{analysis_python}`",
        "- 자격 증명 값·토큰·쿠키는 의도적으로 출력하지 않았다.",
        "",
        "## 도구",
        "",
        "| 도구 | 상태 | 버전/첫 줄 |",
        "|---|---|---|",
    ]
    report.extend(f"| `{name}` | {state} | {value or '-'} |" for name, state, value in rows)
    report += [
        "",
        "## Git",
        "",
        f"- Commit identity: **{identity_state}** (values intentionally not printed).",
        "```text",
        (git_status.stdout or git_status.stderr).strip() or "(no output)",
        "```",
        "",
        "## GitHub CLI 인증",
        "",
        f"- 상태: **{auth_state}**",
        "- 필요 시 실행: `gh auth login --web --git-protocol ssh` (토큰을 이 저장소나 채팅에 붙여 넣지 말 것).",
    ]
    destination = ROOT / "reports" / "00_preflight.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
