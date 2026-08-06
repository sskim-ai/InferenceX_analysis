#!/usr/bin/env python3
"""Conservative tracked-file secret-pattern scan without echoing matched content."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSIGNMENT_PATTERN = re.compile(
    r"\b(?:github_token|gh_token|authorization|bearer|cookie|api[_-]?key|password|secret)\b"
    r"\s*(?:=|:)\s*(?:['\"])?[^\s#`'\"]{8,}",
    re.IGNORECASE,
)
PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN(?: [A-Z]+)? PRIVATE KEY-----")
HEADER_BEARER_PATTERN = re.compile(
    r"\bauthorization\s*:\s*bearer\s+[a-z0-9._~+/-]{8,}", re.IGNORECASE
)
URL_TOKEN_PATTERN = re.compile(
    r"[?&](?:access_token|token|api[_-]?key)=[^&\s]{8,}", re.IGNORECASE
)


def candidates() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return [ROOT / line for line in result.stdout.splitlines() if line]


def main() -> int:
    findings: list[str] = []
    for path in candidates():
        relative = str(path.relative_to(ROOT))
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if (
                ASSIGNMENT_PATTERN.search(line)
                or PRIVATE_KEY_PATTERN.search(line)
                or HEADER_BEARER_PATTERN.search(line)
                or URL_TOKEN_PATTERN.search(line)
            ):
                findings.append(f"{relative}:{number}")
    if findings:
        print("Potential secret-bearing lines (content withheld):")
        print("\n".join(findings))
        return 1
    print("Secret scan passed: no assignment-like sensitive patterns in tracked/unignored text files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
