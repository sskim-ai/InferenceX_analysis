"""Configuration and repository-path helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def repository_root(start: Path | None = None) -> Path:
    """Return the repository root by locating pyproject.toml."""
    path = (start or Path.cwd()).resolve()
    for candidate in (path, *path.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise FileNotFoundError("Could not locate repository root (pyproject.toml)")


def load_run_config(path: str | Path | None = None) -> dict[str, Any]:
    root = repository_root()
    config_path = Path(path) if path else root / "configs" / "run_29820102138.yaml"
    if not config_path.is_absolute():
        config_path = root / config_path
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {config_path}")
    return data


def configured_path(config: dict[str, Any], name: str) -> Path:
    root = repository_root()
    value = config["analysis"][name]
    path = Path(value)
    return path if path.is_absolute() else root / path
