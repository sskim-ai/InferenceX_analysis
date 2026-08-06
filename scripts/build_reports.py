#!/usr/bin/env python3
"""Build evidence-first Markdown reports and optional figures."""

from __future__ import annotations

import argparse

from h200_agentx_analysis.config import repository_root
from h200_agentx_analysis.plotting import generate_figures
from h200_agentx_analysis.reporting import generate_reports


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--figures-only", action="store_true")
    parser.add_argument("--reports-only", action="store_true")
    args = parser.parse_args()
    root = repository_root()
    if not args.figures_only:
        reports = generate_reports(root)
        print(f"Generated {len(reports)} report files.")
    if not args.reports_only:
        figures = generate_figures(root)
        print(f"Generated {len(figures)} figure files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
