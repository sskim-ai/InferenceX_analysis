#!/usr/bin/env python3
"""Join normalized H200 request records to public source trace IDs and turns."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from h200_agentx_analysis.config import configured_path, load_run_config  # noqa: E402
from h200_agentx_analysis.h200_io import read_processed_table, write_json  # noqa: E402
from h200_agentx_analysis.id_normalization import (  # noqa: E402
    normalize_dataframe,
    source_branch_path,
)

MAPPING_COLUMNS = [
    "concurrency",
    "source_trace_count",
    "h200_request_count",
    "h200_root_ids",
    "h200_distinct_root_ids",
    "matched_root_ids",
    "unmatched_h200_ids",
    "unmatched_root_ids",
    "root_match_rate",
    "never_observed_source_ids",
    "root_only_match_count",
    "branch_match_unverified_count",
    "exact_turn_match_count",
    "unmatched_request_count",
    "exact_turn_match_rate",
    "loader_metadata_turn_match_count",
    "loader_metadata_turn_match_rate",
    "loader_metadata_input_compatible_count",
    "root_only_match_rate",
    "normalization_rule_count",
    "normalization_matched_request_count",
    "normalization_request_match_rate",
    "explicit_source_trace_id_request_count",
    "explicit_source_trace_id_match_rate",
]

NORMALIZATION_RULE_COLUMNS = [
    "concurrency",
    "normalization_rule",
    "h200_request_count",
    "distinct_conversation_ids",
    "distinct_root_trace_ids",
    "source_matched_request_count",
    "source_request_match_rate",
]
UNMATCHED_EXAMPLE_COLUMNS = [
    "concurrency",
    "root_trace_id",
    "normalization_rule",
    "example_conversation_id",
    "unmatched_request_count",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Join H200 rows to source root IDs and conservative turn keys."
    )
    parser.add_argument(
        "--config", type=Path, default=REPOSITORY_ROOT / "configs/run_29820102138.yaml"
    )
    parser.add_argument("--processed-dir", type=Path, help="override analysis.processed_dir")
    parser.add_argument("--h200-all", type=Path, help="override h200_requests_all.parquet")
    parser.add_argument(
        "--h200-profiled", type=Path, help="override h200_requests_profiled.parquet"
    )
    parser.add_argument("--source-summary", type=Path, help="override source_trace_summary.parquet")
    parser.add_argument("--source-requests", type=Path, help="override source_requests.parquet")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_run_config(args.config)
        processed = args.processed_dir or configured_path(config, "processed_dir")
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"join blocked: {exc}", file=sys.stderr)
        return 2
    processed.mkdir(parents=True, exist_ok=True)
    h200_all_path = args.h200_all or processed / "h200_requests_all.parquet"
    h200_profiled_path = args.h200_profiled or processed / "h200_requests_profiled.parquet"
    source_summary_path = args.source_summary or processed / "source_trace_summary.parquet"
    source_requests_path = args.source_requests or processed / "source_requests.parquet"
    h200_all = read_processed_table(h200_all_path)
    h200_profiled = read_processed_table(h200_profiled_path)
    source_summary = read_processed_table(source_summary_path)
    source_requests = read_processed_table(source_requests_path)
    source_ids = _source_ids(source_summary, source_requests)
    joined_all = _join(h200_all, source_ids, source_requests)
    joined_profiled = _join(h200_profiled, source_ids, source_requests)
    # The same canonical filenames are intentionally updated so downstream
    # coverage/analysis stages cannot accidentally read pre-join rows.
    joined_all.to_parquet(h200_all_path, index=False)
    joined_profiled.to_parquet(h200_profiled_path, index=False)
    summary = _mapping_summary(joined_profiled, source_ids)
    summary.to_csv(processed / "id_mapping_summary.csv", index=False)
    normalization_rules = _normalization_rule_summary(joined_all)
    unmatched_examples = _unmatched_examples(joined_all, source_ids)
    normalization_rules.to_csv(processed / "id_normalization_rule_summary.csv", index=False)
    unmatched_examples.to_csv(processed / "unmatched_h200_id_examples.csv", index=False)
    h200_build_status = _load_json(processed / "h200_build_status.json")
    h200_available = bool(h200_build_status.get("h200_available", not h200_profiled.empty))
    status = {
        "status": (
            "blocked_no_profile_export"
            if not h200_available
            else ("completed" if source_ids else "blocked_source_tables_unavailable")
        ),
        "h200_available": h200_available,
        "h200_all_rows": int(len(joined_all)),
        "h200_profiled_rows": int(len(joined_profiled)),
        "source_trace_count": len(source_ids),
        "source_request_rows": int(len(source_requests)),
        "exact_turn_match_count": int(
            (joined_profiled.get("match_class") == "exact_turn_match").sum()
        )
        if "match_class" in joined_profiled
        else 0,
        "normalization_rule_rows": int(len(normalization_rules)),
        "unmatched_h200_id_example_rows": int(len(unmatched_examples)),
    }
    write_json(processed / "id_mapping_status.json", status)
    print(json.dumps(status, ensure_ascii=False, sort_keys=True))
    return 0


def _source_ids(source_summary: pd.DataFrame, source_requests: pd.DataFrame) -> set[str]:
    values: set[str] = set()
    for frame in (source_summary, source_requests):
        if "root_trace_id" in frame:
            values.update(
                str(value) for value in frame["root_trace_id"].dropna() if str(value).strip()
            )
    return values


def _join(h200: pd.DataFrame, source_ids: set[str], source_requests: pd.DataFrame) -> pd.DataFrame:
    if h200.empty:
        result = h200.copy()
        for column in _JOIN_COLUMNS:
            if column not in result:
                result[column] = pd.Series(dtype="object")
        return result
    # Re-running the stage should refresh, not merge against, stale source
    # columns from a previous join.
    result = h200.drop(columns=_JOIN_COLUMNS, errors="ignore").copy()
    result = (
        normalize_dataframe(result, source_ids=source_ids)
        if source_ids
        else normalize_dataframe(result)
    )
    result = _prefer_explicit_source_trace_id(result, source_ids)
    result["source_branch_path"] = [
        source_branch_path(conversation_id, root_trace_id=root_trace_id)
        for conversation_id, root_trace_id in zip(
            result.get("conversation_id", pd.Series(index=result.index, dtype="object")),
            result["root_trace_id"],
            strict=True,
        )
    ]
    result["match_class"] = (
        np.where(result["root_trace_id"].isin(source_ids), "root_only_match", "unmatched")
        if source_ids
        else "source_table_unavailable"
    )
    if not source_ids or source_requests.empty or "root_trace_id" not in source_requests:
        for column in _SOURCE_JOIN_FIELDS:
            result[column] = None
        return result

    source = _prepare_source_requests(source_requests)
    if source.empty:
        return result
    branch_keys = source[["root_trace_id", "source_conversation_path"]].drop_duplicates()
    branch_index = pd.MultiIndex.from_frame(branch_keys)
    request_keys = source[
        [
            "root_trace_id",
            "source_conversation_path",
            "source_branch_request_index",
            "source_input_tokens",
        ]
    ].copy()
    key_counts = (
        request_keys.groupby(
            [
                "root_trace_id",
                "source_conversation_path",
                "source_branch_request_index",
                "source_input_tokens",
            ],
            dropna=False,
        )
        .size()
        .rename("source_pair_key_count")
        .reset_index()
    )
    source_unique = source.merge(
        key_counts,
        on=[
            "root_trace_id",
            "source_conversation_path",
            "source_branch_request_index",
            "source_input_tokens",
        ],
        how="left",
    )
    source_unique = source_unique.loc[source_unique["source_pair_key_count"] == 1].copy()
    candidate = result["root_trace_id"].isin(source_ids) & result["source_branch_path"].notna()
    candidate_index = pd.MultiIndex.from_frame(
        result.loc[candidate, ["root_trace_id", "source_branch_path"]]
    )
    branch_match = candidate_index.isin(branch_index)
    result.loc[result.index[candidate][branch_match], "match_class"] = "branch_match_unverified"

    result["_turn_key"] = pd.to_numeric(result.get("turn_index"), errors="coerce")
    result["_input_key"] = _integer_token_key(result.get("input_tokens"))
    left_keys = ["root_trace_id", "source_branch_path", "_turn_key", "_input_key"]
    right_keys = [
        "root_trace_id",
        "source_conversation_path",
        "source_branch_request_index",
        "source_input_tokens",
    ]
    source_columns = list(dict.fromkeys([*right_keys, *_SOURCE_JOIN_FIELDS]))
    source_unique = source_unique[
        [column for column in source_columns if column in source_unique]
    ].copy()
    merged = result.merge(
        source_unique,
        how="left",
        left_on=left_keys,
        right_on=right_keys,
        suffixes=("", "_source"),
    )
    exact = merged["source_conversation_path"].notna()
    merged.loc[exact, "match_class"] = "exact_turn_match"
    # Retain the actual source path/index that justified a high-confidence pair.
    merged["source_conversation_path"] = merged.get("source_conversation_path")
    merged["source_branch_request_index"] = merged.get("source_branch_request_index")
    merged = _apply_loader_metadata_join(merged, source)
    return merged.drop(columns=["_turn_key", "_input_key"], errors="ignore")


def _prepare_source_requests(source: pd.DataFrame) -> pd.DataFrame:
    needed = [
        "root_trace_id",
        "source_conversation_path",
        "source_branch_request_index",
        "source_input_tokens",
    ]
    if any(column not in source for column in needed):
        return pd.DataFrame(columns=needed)
    result = source.copy()
    result["root_trace_id"] = result["root_trace_id"].astype("string")
    result["source_conversation_path"] = result["source_conversation_path"].astype("string")
    result["source_branch_request_index"] = pd.to_numeric(
        result["source_branch_request_index"], errors="coerce"
    )
    result["source_input_tokens"] = _integer_token_key(result["source_input_tokens"])
    return result.dropna(subset=needed)


def _apply_loader_metadata_join(frame: pd.DataFrame, source: pd.DataFrame) -> pd.DataFrame:
    """Attach direct Weka loader turn evidence without overstating exactness.

    ``source_trace_id`` plus ``source_outer_idx`` and optional
    ``source_inner_idx`` identify the source request emitted by the loader.
    The H200 input sequence length can nevertheless differ from its source
    trace representation, so this is labelled ``loader_metadata_turn_match``.
    Only rows with compatible input length are promoted to ``exact_turn_match``.
    """

    result = frame.copy()
    for column in (
        "loader_metadata_turn_match",
        "loader_metadata_input_tokens_match",
        "loader_metadata_output_tokens_match",
    ):
        result[column] = False
    metadata_source = _prepare_loader_metadata_source(source)
    if metadata_source.empty:
        return result
    result["_loader_outer_key"] = _loader_index_key(
        result.get("source_outer_idx", pd.Series(index=result.index, dtype="object")),
        missing_sentinel=None,
    )
    result["_loader_inner_key"] = _loader_index_key(
        result.get("source_inner_idx", pd.Series(index=result.index, dtype="object")),
        missing_sentinel=-1,
    )
    result["root_trace_id"] = result["root_trace_id"].astype("string")
    merged = result.merge(
        metadata_source,
        how="left",
        on=["root_trace_id", "_loader_outer_key", "_loader_inner_key"],
        validate="many_to_one",
    )
    match = merged["_loader_metadata_match"].fillna(False).astype(bool)
    input_match = _numeric_equal(
        merged.get("input_tokens", pd.Series(index=merged.index, dtype="object")),
        merged.get("_loader_source_input_tokens", pd.Series(index=merged.index, dtype="object")),
    )
    output_match = _numeric_equal(
        merged.get("output_tokens", pd.Series(index=merged.index, dtype="object")),
        merged.get("_loader_source_output_tokens", pd.Series(index=merged.index, dtype="object")),
    )
    merged["loader_metadata_turn_match"] = match
    merged["loader_metadata_input_tokens_match"] = match & input_match
    merged["loader_metadata_output_tokens_match"] = match & output_match
    for field in _SOURCE_JOIN_FIELDS:
        loader_field = f"_loader_{field}"
        if loader_field in merged:
            merged.loc[match, field] = merged.loc[match, loader_field]
    merged.loc[match, "match_class"] = "loader_metadata_turn_match"
    merged.loc[match & input_match, "match_class"] = "exact_turn_match"
    loader_columns = [
        column
        for column in merged
        if column.startswith("_loader_")
    ]
    return merged.drop(columns=loader_columns, errors="ignore")


def _prepare_loader_metadata_source(source: pd.DataFrame) -> pd.DataFrame:
    required = [
        "root_trace_id",
        "source_outer_request_index",
        "source_inner_request_index",
    ]
    if any(column not in source for column in required):
        return pd.DataFrame()
    result = source.copy()
    result["root_trace_id"] = result["root_trace_id"].astype("string")
    result["_loader_outer_key"] = _loader_index_key(
        result["source_outer_request_index"], missing_sentinel=None
    )
    result["_loader_inner_key"] = _loader_index_key(
        result["source_inner_request_index"], missing_sentinel=-1
    )
    result = result.dropna(subset=["root_trace_id", "_loader_outer_key"])
    key_columns = ["root_trace_id", "_loader_outer_key", "_loader_inner_key"]
    key_counts = (
        result.groupby(key_columns, dropna=False)
        .size()
        .rename("_loader_pair_key_count")
        .reset_index()
    )
    result = result.merge(key_counts, on=key_columns, how="left")
    result = result.loc[result["_loader_pair_key_count"] == 1].copy()
    fields = [field for field in _SOURCE_JOIN_FIELDS if field in result]
    rename = {field: f"_loader_{field}" for field in fields}
    result = result[[*key_columns, *fields]].rename(columns=rename)
    result["_loader_metadata_match"] = True
    return result


def _loader_index_key(series: pd.Series, *, missing_sentinel: int | None) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    valid = numeric.notna() & (np.abs(numeric - np.round(numeric)) < 1e-9)
    if missing_sentinel is None:
        result = pd.Series(pd.NA, index=series.index, dtype="Int64")
    else:
        result = pd.Series(missing_sentinel, index=series.index, dtype="Int64")
    result.loc[valid] = np.round(numeric.loc[valid]).astype("int64")
    return result


def _numeric_equal(left: pd.Series, right: pd.Series) -> pd.Series:
    left_numeric = pd.to_numeric(left, errors="coerce")
    right_numeric = pd.to_numeric(right, errors="coerce")
    return (
        left_numeric.notna()
        & right_numeric.notna()
        & (np.abs(left_numeric - right_numeric) < 1e-9)
    )


def _integer_token_key(series: object) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    # Token sequence length must be an exact non-negative integer for an exact
    # turn match. A non-integral metric is left unmatched rather than rounded.
    valid = numeric.notna() & (numeric >= 0) & (np.abs(numeric - np.round(numeric)) < 1e-9)
    result = pd.Series(pd.NA, index=numeric.index, dtype="Int64")
    result.loc[valid] = np.round(numeric.loc[valid]).astype("int64")
    return result


def _mapping_summary(frame: pd.DataFrame, source_ids: set[str]) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=MAPPING_COLUMNS)
    copy = frame.copy()
    if "concurrency" not in copy:
        copy["concurrency"] = None
    rows: list[dict] = []
    for concurrency, group in copy.groupby("concurrency", dropna=False):
        roots = {
            str(value) for value in group.get("root_trace_id", pd.Series(dtype="object")).dropna()
        }
        matched = roots.intersection(source_ids)
        classes = group.get("match_class", pd.Series(index=group.index, dtype="object"))
        source_matched = _truthy_series(
            group.get("source_id_matched", pd.Series(index=group.index, dtype="object"))
        )
        loader_matched = _truthy_series(
            group.get("loader_metadata_turn_match", pd.Series(index=group.index, dtype="object"))
        )
        loader_input_compatible = _truthy_series(
            group.get(
                "loader_metadata_input_tokens_match",
                pd.Series(index=group.index, dtype="object"),
            )
        )
        rows.append(
            {
                "concurrency": concurrency,
                "source_trace_count": len(source_ids),
                "h200_request_count": int(len(group)),
                "h200_root_ids": len(roots),
                "h200_distinct_root_ids": len(roots),
                "matched_root_ids": len(matched),
                "unmatched_h200_ids": len(roots - source_ids),
                "unmatched_root_ids": len(roots - source_ids),
                "root_match_rate": len(matched) / len(roots) if roots else None,
                "never_observed_source_ids": len(source_ids - matched),
                "root_only_match_count": int((classes == "root_only_match").sum()),
                "branch_match_unverified_count": int((classes == "branch_match_unverified").sum()),
                "exact_turn_match_count": int((classes == "exact_turn_match").sum()),
                "unmatched_request_count": int((classes == "unmatched").sum()),
                "exact_turn_match_rate": int((classes == "exact_turn_match").sum()) / len(group)
                if len(group)
                else None,
                "loader_metadata_turn_match_count": int(loader_matched.sum()),
                "loader_metadata_turn_match_rate": float(loader_matched.mean())
                if len(group)
                else None,
                "loader_metadata_input_compatible_count": int(loader_input_compatible.sum()),
                "root_only_match_rate": int((classes == "root_only_match").sum()) / len(group)
                if len(group)
                else None,
                "normalization_rule_count": int(
                    group.get("normalization_rule", pd.Series(dtype="object")).nunique(dropna=True)
                ),
                "normalization_matched_request_count": int(source_matched.sum()),
                "normalization_request_match_rate": float(source_matched.mean())
                if len(group)
                else None,
                "explicit_source_trace_id_request_count": int(
                    (
                        group.get(
                            "root_trace_id_provenance", pd.Series(index=group.index, dtype="object")
                        )
                        == "metadata.source_trace_id"
                    ).sum()
                ),
                "explicit_source_trace_id_match_rate": float(
                    source_matched.loc[
                        group.get(
                            "root_trace_id_provenance", pd.Series(index=group.index, dtype="object")
                        )
                        == "metadata.source_trace_id"
                    ].mean()
                )
                if (
                    group.get(
                        "root_trace_id_provenance", pd.Series(index=group.index, dtype="object")
                    )
                    == "metadata.source_trace_id"
                ).any()
                else None,
            }
        )
    return pd.DataFrame(rows, columns=MAPPING_COLUMNS)


def _normalization_rule_summary(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=NORMALIZATION_RULE_COLUMNS)
    copy = frame.copy()
    for column in (
        "concurrency",
        "normalization_rule",
        "conversation_id",
        "root_trace_id",
        "source_id_matched",
    ):
        if column not in copy:
            copy[column] = None
    copy["normalization_rule"] = copy["normalization_rule"].fillna("missing_rule")
    rows: list[dict] = []
    for (concurrency, rule), group in copy.groupby(["concurrency", "normalization_rule"], dropna=False):
        matched = _truthy_series(group["source_id_matched"])
        rows.append(
            {
                "concurrency": concurrency,
                "normalization_rule": rule,
                "h200_request_count": int(len(group)),
                "distinct_conversation_ids": int(group["conversation_id"].nunique(dropna=True)),
                "distinct_root_trace_ids": int(group["root_trace_id"].nunique(dropna=True)),
                "source_matched_request_count": int(matched.sum()),
                "source_request_match_rate": float(matched.mean()) if len(group) else None,
            }
        )
    return pd.DataFrame(rows, columns=NORMALIZATION_RULE_COLUMNS)


def _unmatched_examples(
    frame: pd.DataFrame, source_ids: set[str], *, limit: int = 100
) -> pd.DataFrame:
    if frame.empty or "root_trace_id" not in frame:
        return pd.DataFrame(columns=UNMATCHED_EXAMPLE_COLUMNS)
    copy = frame.copy()
    for column in ("concurrency", "normalization_rule", "conversation_id"):
        if column not in copy:
            copy[column] = None
    unmatched = copy.loc[
        ~copy["root_trace_id"].isin(source_ids) & copy["root_trace_id"].notna()
    ].copy()
    if unmatched.empty:
        return pd.DataFrame(columns=UNMATCHED_EXAMPLE_COLUMNS)
    rows: list[dict] = []
    for (concurrency, root_trace_id, rule), group in unmatched.groupby(
        ["concurrency", "root_trace_id", "normalization_rule"], dropna=False
    ):
        examples = group["conversation_id"].dropna()
        rows.append(
            {
                "concurrency": concurrency,
                "root_trace_id": root_trace_id,
                "normalization_rule": rule,
                "example_conversation_id": examples.iloc[0] if not examples.empty else None,
                "unmatched_request_count": int(len(group)),
            }
        )
    return (
        pd.DataFrame(rows, columns=UNMATCHED_EXAMPLE_COLUMNS)
        .sort_values("unmatched_request_count", ascending=False)
        .head(limit)
    )


def _truthy_series(series: pd.Series) -> pd.Series:
    normalized = series.astype("string").str.strip().str.lower()
    return normalized.isin(["true", "1", "yes", "y"])


def _prefer_explicit_source_trace_id(frame: pd.DataFrame, source_ids: set[str]) -> pd.DataFrame:
    """Use loader-supplied source roots ahead of rendered conversation parsing.

    The Weka loader writes ``metadata.source_trace_id`` for each raw request.
    That field directly identifies the source trace, whereas ``conversation_id``
    includes runtime fan-out/auxiliary decorations and is only a fallback.
    """

    result = frame.copy()
    if "source_trace_id" not in result:
        result["root_trace_id_provenance"] = "conversation_id_normalization"
        return result
    explicit = result["source_trace_id"].astype("string").str.strip()
    valid = explicit.notna() & explicit.ne("")
    result["root_trace_id_provenance"] = result.get(
        "root_trace_id_provenance", pd.Series(index=result.index, dtype="object")
    ).fillna("conversation_id_normalization")
    result.loc[valid, "root_trace_id"] = explicit.loc[valid].astype("object")
    result.loc[valid, "normalization_rule"] = "explicit_metadata_source_trace_id"
    result.loc[valid, "root_trace_id_provenance"] = "metadata.source_trace_id"
    result.loc[valid, "source_id_matched"] = explicit.loc[valid].isin(source_ids)
    return result


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


_SOURCE_JOIN_FIELDS = [
    "source_conversation_path",
    "source_outer_request_index",
    "source_inner_request_index",
    "source_branch_request_index",
    "source_request_index",
    "source_branch_type",
    "source_model",
    "source_input_tokens",
    "source_output_tokens",
    "source_t_s",
    "hash_block_count",
    "lcp_block_count",
    "theoretical_cached_tokens",
    "theoretical_new_tokens",
    "theoretical_cache_ratio",
    "rollback_blocks",
    "branch_fork_indicator",
]
_JOIN_COLUMNS = [
    "root_trace_id_provenance",
    "source_branch_path",
    "match_class",
    "loader_metadata_turn_match",
    "loader_metadata_input_tokens_match",
    "loader_metadata_output_tokens_match",
    *_SOURCE_JOIN_FIELDS,
]


if __name__ == "__main__":
    raise SystemExit(main())
