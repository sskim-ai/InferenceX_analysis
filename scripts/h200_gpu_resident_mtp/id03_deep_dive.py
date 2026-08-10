#!/usr/bin/env python3
"""Create the local-ready public H200 reference package for canonical ID03.

This script consumes the local-only full public request Parquet produced by
``make mtp-analyze`` and writes compact, versioned CSVs and figures.  It never
creates a local-server result: cpy1..cpy8 remain an evidence contract only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from h200_agentx_analysis.id03_deep_dive import (  # noqa: E402
    ID03_CANONICAL_ID,
    build_reference_table,
    c8_latency_distribution,
    c8_source_input_buckets,
    collapse_source_key_profiles,
    context_202752_status,
    cross_concurrency_summary,
    exact_all_table,
    exact_pair_table,
    h200_scaling_curve,
    source_coverage_by_concurrency,
)

STUDY_ROOT_DEFAULT = REPOSITORY_ROOT / "studies/h200_gpu_resident_mtp"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-root", type=Path, default=STUDY_ROOT_DEFAULT)
    parser.add_argument(
        "--h200-requests",
        type=Path,
        default=STUDY_ROOT_DEFAULT / "processed/h200_requests_all.parquet",
    )
    parser.add_argument(
        "--source-requests",
        type=Path,
        default=REPOSITORY_ROOT / "data/processed/source_requests.parquet",
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=REPOSITORY_ROOT / "data/raw/h200_gpu_resident_mtp",
        help="Local ignored artifact root used only to cite replay-scheduling evidence.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    processed = args.study_root / "processed"
    figures = args.study_root / "figures"
    processed.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    _assert_canonical_resolution(processed / "requested_id_resolution.csv")
    if not args.h200_requests.exists():
        raise SystemExit(
            f"missing {args.h200_requests}; run `make mtp-analyze` before `make mtp-id03`"
        )
    if not args.source_requests.exists():
        raise SystemExit(
            f"missing {args.source_requests}; build source trace tables before `make mtp-id03`"
        )

    all_requests = pd.read_parquet(args.h200_requests)
    source_requests = pd.read_parquet(args.source_requests)
    source_rows = source_requests.loc[
        source_requests.get("root_trace_id", pd.Series(dtype="string")).astype("string")
        == ID03_CANONICAL_ID
    ]
    source_request_count = int(
        source_rows[["source_outer_request_index", "source_inner_request_index"]]
        .drop_duplicates()
        .shape[0]
    )
    if source_request_count == 0:
        raise SystemExit("canonical ID03 has no flattened source requests")

    reference = build_reference_table(all_requests)
    reference.to_csv(processed / "id03_h200_reference_requests.csv", index=False)
    coverage = source_coverage_by_concurrency(reference, source_request_count=source_request_count)
    coverage.to_csv(processed / "id03_source_coverage_by_concurrency.csv", index=False)
    collapsed = collapse_source_key_profiles(reference)
    pairs = {
        "c8_c12": exact_pair_table(collapsed, 8, 12),
        "c8_c16": exact_pair_table(collapsed, 8, 16),
        "c12_c16": exact_pair_table(collapsed, 12, 16),
    }
    for name, table in pairs.items():
        table.to_csv(processed / f"id03_exact_match_{name}.csv", index=False)
    exact_all_table(collapsed).to_csv(processed / "id03_exact_match_all.csv", index=False)
    cross_concurrency_summary(collapsed, pairs).to_csv(
        processed / "id03_cross_concurrency_summary.csv", index=False
    )
    scaling = h200_scaling_curve(reference, source_request_count=source_request_count)
    scaling.to_csv(processed / "id03_h200_scaling_curve.csv", index=False)
    c8_latency_distribution(reference).to_csv(
        processed / "id03_c8_latency_distribution.csv", index=False
    )
    c8_source_input_buckets(reference).to_csv(
        processed / "id03_c8_source_input_buckets.csv", index=False
    )
    compatible, context_status = context_202752_status(reference)
    compatible.to_csv(processed / "id03_context_202752_compatible_requests.csv", index=False)
    context_status.to_csv(processed / "id03_context_202752_subset_status.csv", index=False)
    _replay_scheduling_evidence(args.raw_root).to_csv(
        processed / "id03_replay_scheduling_evidence.csv", index=False
    )
    _build_figures(reference, scaling, figures)
    print(
        json.dumps(
            {
                "status": "completed",
                "canonical_id": ID03_CANONICAL_ID,
                "source_request_count": source_request_count,
                "h200_reference_rows": int(len(reference)),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _assert_canonical_resolution(path: Path) -> None:
    if not path.exists():
        raise SystemExit("missing requested_id_resolution.csv; run `make mtp-analyze`")
    resolution = pd.read_csv(path)
    row = resolution.loc[resolution.get("id_label", pd.Series(dtype="string")) == "ID03"]
    if len(row) != 1:
        raise SystemExit("ID03 resolution row is missing or ambiguous")
    item = row.iloc[0]
    if (
        str(item.get("resolution_status")) != "unique"
        or str(item.get("resolved_full_source_trace_id")) != ID03_CANONICAL_ID
    ):
        raise SystemExit("source ID universe changed; do not silently change canonical ID03")


def _replay_scheduling_evidence(raw_root: Path) -> pd.DataFrame:
    """Cite raw command/log lines that explain non-identical coverage.

    The raw inputs remain ignored; this compact table preserves only short,
    reviewable evidence values plus the artifact-relative origin and line.
    """

    rows: list[dict[str, object]] = []
    for concurrency in (8, 12, 16):
        result_root = raw_root / f"conc{concurrency}" / "result"
        command_paths = list(result_root.glob("*/conc_*/benchmark_command.txt"))
        log_paths = list(result_root.glob("*/conc_*/aiperf_artifacts/logs/aiperf.log"))
        if command_paths:
            command_path = command_paths[0]
            command = command_path.read_text(encoding="utf-8", errors="replace").strip()
            _append_command_evidence(rows, concurrency, command_path, command)
        else:
            rows.append(_unavailable_evidence(concurrency, "benchmark_command"))
        if log_paths:
            _append_log_evidence(rows, concurrency, log_paths[0])
        else:
            rows.append(_unavailable_evidence(concurrency, "aiperf_log"))
    return pd.DataFrame(rows)


def _append_command_evidence(
    rows: list[dict[str, object]], concurrency: int, path: Path, command: str
) -> None:
    rel = str(path.relative_to(REPOSITORY_ROOT))
    values = {
        "benchmark_duration_s": "3600" if "--benchmark-duration 3600" in command else None,
        "trajectory_start_ratio": "0.25_to_0.75"
        if "--trajectory-start-min-ratio 0.25" in command
        and "--trajectory-start-max-ratio 0.75" in command
        else None,
        "warmup_requests_per_lane": "10" if "--warmup-requests-per-lane 10" in command else None,
        "dataset_entries": "393" if "--num-dataset-entries 393" in command else None,
    }
    for evidence_type, value in values.items():
        rows.append(
            {
                "concurrency": concurrency,
                "evidence_type": evidence_type,
                "value": value or "not_found_in_command",
                "classification": "Evidence" if value else "Unknown",
                "source_file": rel,
                "source_line": 1,
                "scope_note": "AIPerf command setting; not a per-ID measurement",
            }
        )


def _append_log_evidence(rows: list[dict[str, object]], concurrency: int, path: Path) -> None:
    rel = str(path.relative_to(REPOSITORY_ROOT))
    patterns = {
        "warmup_profile_handoff": "preserving paused DAG work for profiling handoff",
        "profiling_recycling": "recycle draws roots from the dataset sampler",
    }
    if concurrency == 16:
        patterns["id03_initial_trajectory_state"] = ID03_CANONICAL_ID
    found = {key: False for key in patterns}
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            for evidence_type, pattern in patterns.items():
                if not found[evidence_type] and pattern in line:
                    value = line.strip()
                    rows.append(
                        {
                            "concurrency": concurrency,
                            "evidence_type": evidence_type,
                            "value": value,
                            "classification": "Evidence",
                            "source_file": rel,
                            "source_line": line_number,
                            "scope_note": "Raw AIPerf runtime-log line; raw log remains Git-ignored",
                        }
                    )
                    found[evidence_type] = True
    for evidence_type, is_found in found.items():
        if not is_found:
            rows.append(
                {
                    "concurrency": concurrency,
                    "evidence_type": evidence_type,
                    "value": "not_found_in_log",
                    "classification": "Unknown",
                    "source_file": rel,
                    "source_line": None,
                    "scope_note": "Raw AIPerf runtime-log search",
                }
            )


def _unavailable_evidence(concurrency: int, source_type: str) -> dict[str, object]:
    return {
        "concurrency": concurrency,
        "evidence_type": source_type,
        "value": "raw_input_unavailable",
        "classification": "Unknown",
        "source_file": None,
        "source_line": None,
        "scope_note": "Run acquisition is required to reproduce this evidence",
    }


def _build_figures(reference: pd.DataFrame, scaling: pd.DataFrame, figures: Path) -> None:
    profile = reference.loc[reference.get("is_profiled_valid", False).fillna(False).astype(bool)].copy()
    _ordinal_plot(
        profile,
        "source_input_tokens",
        "Source-workload input tokens (not target logical context)",
        figures / "id03_source_input_vs_ordinal.png",
    )
    _ordinal_plot(profile, "ttft_ms", "Observed H200 replay TTFT (ms)", figures / "id03_ttft_vs_ordinal.png")
    _ordinal_plot(profile, "itl_ms", "Request-level ITL (ms)", figures / "id03_itl_vs_ordinal.png")
    _ordinal_plot(profile, "output_tokens", "Observed output tokens", figures / "id03_output_tokens_vs_ordinal.png")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    if not scaling.empty:
        axes[0].plot(scaling["concurrency"], scaling["ttft_median_ms"], marker="o")
        axes[0].set_ylabel("Median TTFT (ms)")
        axes[1].plot(scaling["concurrency"], scaling["weighted_decode_tps"], marker="o")
        axes[1].set_ylabel("Weighted decode TPS (tok/s)")
        for _, row in scaling.iterrows():
            label = (
                f"n={int(row['profile_request_count'])}\n"
                f"coverage={float(row['coverage_ratio']):.0%}"
            )
            axes[0].annotate(
                label,
                (row["concurrency"], row["ttft_median_ms"]),
                xytext=(4, 7),
                textcoords="offset points",
                fontsize=8,
            )
            axes[1].annotate(
                f"n={int(row['itl_sample_count'])}",
                (row["concurrency"], row["weighted_decode_tps"]),
                xytext=(4, 7),
                textcoords="offset points",
                fontsize=8,
            )
    for axis in axes:
        axis.set_xlabel("Public mixed-workload concurrency")
        axis.grid(alpha=0.25)
    fig.suptitle(
        "ID03 public H200 scaling; TTFT request median / TPS output-transition-ITL weighted"
    )
    fig.tight_layout()
    fig.savefig(figures / "id03_h200_scaling_curve.png", dpi=160)
    plt.close(fig)


def _ordinal_plot(frame: pd.DataFrame, field: str, ylabel: str, path: Path) -> None:
    fig, axis = plt.subplots(figsize=(8, 4.6))
    required = {"concurrency", "source_request_index", field}
    if required.issubset(frame.columns):
        for concurrency, group in frame.groupby("concurrency", dropna=False):
            data = group[["source_request_index", field]].dropna().sort_values("source_request_index")
            if not data.empty:
                axis.scatter(
                    data["source_request_index"],
                    data[field],
                    s=18,
                    label=f"c{concurrency} (n={len(data)})",
                )
        if axis.collections:
            axis.legend(title="public sweep")
        else:
            axis.text(0.5, 0.5, "No comparable profiling rows", ha="center", va="center", transform=axis.transAxes)
    else:
        axis.text(0.5, 0.5, "No comparable profiling rows", ha="center", va="center", transform=axis.transAxes)
    axis.set_xlabel("Source request index")
    axis.set_ylabel(ylabel)
    axis.set_title("ID03 public replay trajectory")
    axis.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())
