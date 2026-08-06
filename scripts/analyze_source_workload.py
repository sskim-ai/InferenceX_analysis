#!/usr/bin/env python3
"""Summarize source workload shape without conflating it with H200 results."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from h200_agentx_analysis.config import configured_path, load_run_config  # noqa: E402


def _quantile(series: pd.Series, q: float) -> float | None:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float(values.quantile(q)) if not values.empty else None


def _model_summary(requests: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "source_model",
        "source_request_count",
        "distinct_root_trace_ids",
        "root_request_count",
        "subagent_request_count",
        "total_input_tokens",
        "median_input_tokens",
        "p90_input_tokens",
        "total_output_tokens",
        "median_output_tokens",
        "p90_output_tokens",
        "api_time_present_rate",
        "median_source_api_time_s",
        "source_ttft_present_rate",
        "median_source_ttft_s",
    ]
    if requests.empty or "source_model" not in requests:
        return pd.DataFrame(columns=columns)
    rows: list[dict[str, object]] = []
    for model, group in requests.groupby("source_model", dropna=False):
        branch = group.get("source_branch_type", pd.Series(index=group.index, dtype="string")).astype("string")
        api = pd.to_numeric(group.get("source_api_time_s"), errors="coerce")
        ttft = pd.to_numeric(group.get("source_ttft_s"), errors="coerce")
        rows.append(
            {
                "source_model": model if pd.notna(model) else "<missing>",
                "source_request_count": int(len(group)),
                "distinct_root_trace_ids": int(group["root_trace_id"].nunique(dropna=True)),
                "root_request_count": int((branch == "root").sum()),
                "subagent_request_count": int((branch != "root").sum()),
                "total_input_tokens": int(pd.to_numeric(group.get("source_input_tokens"), errors="coerce").fillna(0).sum()),
                "median_input_tokens": _quantile(group.get("source_input_tokens"), 0.5),
                "p90_input_tokens": _quantile(group.get("source_input_tokens"), 0.9),
                "total_output_tokens": int(pd.to_numeric(group.get("source_output_tokens"), errors="coerce").fillna(0).sum()),
                "median_output_tokens": _quantile(group.get("source_output_tokens"), 0.5),
                "p90_output_tokens": _quantile(group.get("source_output_tokens"), 0.9),
                "api_time_present_rate": float(api.notna().mean()),
                "median_source_api_time_s": _quantile(api, 0.5),
                "source_ttft_present_rate": float(ttft.notna().mean()),
                "median_source_ttft_s": _quantile(ttft, 0.5),
            }
        )
    return pd.DataFrame(rows, columns=columns).sort_values("source_request_count", ascending=False)


def _cache_shape_summary(requests: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "source_branch_type",
        "source_request_count",
        "hash_ids_present_rate",
        "lcp_available_rate",
        "median_hash_block_count",
        "median_lcp_block_count",
        "median_theoretical_cached_tokens",
        "median_theoretical_new_tokens",
        "median_theoretical_cache_ratio",
        "p90_theoretical_cache_ratio",
    ]
    if requests.empty or "source_branch_type" not in requests:
        return pd.DataFrame(columns=columns)
    rows: list[dict[str, object]] = []
    for kind, group in requests.groupby("source_branch_type", dropna=False):
        hashes = group.get("hash_block_count", pd.Series(index=group.index, dtype=float))
        lcp = group.get("lcp_block_count", pd.Series(index=group.index, dtype=float))
        ratio = group.get("theoretical_cache_ratio", pd.Series(index=group.index, dtype=float))
        rows.append(
            {
                "source_branch_type": kind if pd.notna(kind) else "<missing>",
                "source_request_count": int(len(group)),
                "hash_ids_present_rate": float(pd.to_numeric(hashes, errors="coerce").notna().mean()),
                "lcp_available_rate": float(pd.to_numeric(lcp, errors="coerce").notna().mean()),
                "median_hash_block_count": _quantile(hashes, 0.5),
                "median_lcp_block_count": _quantile(lcp, 0.5),
                "median_theoretical_cached_tokens": _quantile(group.get("theoretical_cached_tokens"), 0.5),
                "median_theoretical_new_tokens": _quantile(group.get("theoretical_new_tokens"), 0.5),
                "median_theoretical_cache_ratio": _quantile(ratio, 0.5),
                "p90_theoretical_cache_ratio": _quantile(ratio, 0.9),
            }
        )
    return pd.DataFrame(rows, columns=columns).sort_values("source_request_count", ascending=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/run_29820102138.yaml")
    args = parser.parse_args()
    config = load_run_config(args.config)
    processed = configured_path(config, "processed_dir")
    source_path = processed / "source_requests.parquet"
    if not source_path.exists():
        print(f"source workload analysis blocked: {source_path} does not exist", file=sys.stderr)
        return 2
    requests = pd.read_parquet(source_path)
    _model_summary(requests).to_csv(processed / "source_model_workload_summary.csv", index=False)
    _cache_shape_summary(requests).to_csv(processed / "source_cache_shape_summary.csv", index=False)
    print(f"source workload summaries written for {len(requests)} source request rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
