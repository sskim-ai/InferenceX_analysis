"""Evidence-first Markdown report construction.

The reporting layer deliberately reads the persisted analysis tables instead
of re-deriving metrics.  That keeps a report re-run reproducible and, more
importantly, makes a missing H200 acquisition visibly different from an H200
run with zero eligible profiling records.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd

from .provenance import read_json, utc_now


def _read_table(root: Path, name: str) -> pd.DataFrame:
    """Read one derived table, treating a missing/corrupt table as unavailable."""

    base = root / "data" / "processed"
    for suffix, reader in ((".parquet", pd.read_parquet), (".csv", pd.read_csv)):
        path = base / f"{name}{suffix}"
        if path.exists():
            try:
                return reader(path)
            except Exception:
                return pd.DataFrame()
    return pd.DataFrame()


def _count(frame: pd.DataFrame, column: str | None = None) -> int | None:
    if frame.empty:
        return None
    if column and column in frame:
        return int(frame[column].nunique(dropna=True))
    return int(len(frame))


def _display_count(value: int | float | None) -> str:
    if value is None or pd.isna(value):
        return "unavailable"
    return f"{int(value):,}"


def _display_rate(numerator: int | float | None, denominator: int | float | None) -> str:
    if numerator is None or denominator is None or pd.isna(numerator) or pd.isna(denominator):
        return "unavailable"
    if float(denominator) == 0:
        return "unavailable"
    return f"{100 * float(numerator) / float(denominator):.1f}%"


def _display_value(value: object, column: str) -> str:
    """Use compact, public-safe Markdown cells without losing CSV precision."""

    try:
        missing = bool(pd.isna(value))
    except (TypeError, ValueError):
        missing = False
    if missing:
        return ""
    text = str(value)
    if column in {"root_trace_id", "source_trace_id"} and len(text) > 12:
        text = f"{text[:12]}…"
    if isinstance(value, float):
        text = f"{value:.6g}"
    return text.replace("|", "\\|").replace("\n", " ")


def _markdown_table(frame: pd.DataFrame, columns: list[str], limit: int = 20) -> str:
    """Render only available columns and truncate public trace IDs for prose."""

    existing = [column for column in columns if column in frame.columns]
    if frame.empty or not existing:
        return "_Unknown — required derived table is unavailable._"
    rows = frame[existing].head(limit)
    header = "| " + " | ".join(existing) + " |"
    divider = "|" + "|".join("---" for _ in existing) + "|"
    body = [
        "| "
        + " | ".join(
            _display_value(value, column) for column, value in zip(existing, row, strict=True)
        )
        + " |"
        for row in rows.itertuples(index=False, name=None)
    ]
    return "\n".join([header, divider, *body])


def _label(label: str, statement: str) -> str:
    stripped = statement.strip()
    prefix = f"**{label}:**"
    if stripped.startswith(prefix):
        return stripped
    return f"{prefix} {stripped}"


def _write(
    path: Path,
    heading: str,
    evidence: Iterable[str],
    inference: Iterable[str],
    unknown: Iterable[str],
) -> None:
    """Write consistently labelled Evidence / Inference / Unknown statements."""

    content = [f"# {heading}", "", "## Evidence", ""]
    content.extend(f"- {_label('Evidence', line)}" for line in evidence)
    content += ["", "## Inference", ""]
    content.extend(f"- {_label('Inference', line)}" for line in inference)
    content += ["", "## Unknown", ""]
    content.extend(f"- {_label('Unknown', line)}" for line in unknown)
    content.append("")
    path.write_text("\n".join(content), encoding="utf-8")


def _truthy_count(frame: pd.DataFrame, column: str) -> int:
    if frame.empty or column not in frame:
        return 0
    values = frame[column].astype("string").str.strip().str.lower()
    return int(values.isin(["true", "1", "yes", "y"]).sum())


def _value_count(frame: pd.DataFrame, column: str, value: str) -> int:
    if frame.empty or column not in frame:
        return 0
    return int((frame[column].astype("string") == value).sum())


def _numeric_equal_count(frame: pd.DataFrame, column: str, value: float) -> int:
    if frame.empty or column not in frame:
        return 0
    numbers = pd.to_numeric(frame[column], errors="coerce")
    return int((numbers == value).sum())


def _status_count(frame: pd.DataFrame, column: str, statuses: set[str]) -> int:
    if frame.empty or column not in frame:
        return 0
    return int(frame[column].astype("string").isin(statuses).sum())


def _present_count(frame: pd.DataFrame, column: str) -> int:
    if frame.empty or column not in frame:
        return 0
    return int(frame[column].astype("string").str.strip().ne("").sum())


def _h200_state(status: dict[str, Any], profiled: pd.DataFrame) -> tuple[bool, bool, str]:
    """Return (available, completed_zero, explanatory reason)."""

    raw_status = str(status.get("status", "")).strip()
    configured_available = status.get("h200_available")
    available = bool(configured_available) if configured_available is not None else not profiled.empty
    if raw_status == "blocked_no_profile_export" or not available:
        return (
            False,
            False,
            "H200 raw `profile_export.jsonl`가 확보되지 않았다. 빈 결과는 0 관측이 아니라 분석 불가 상태다.",
        )
    if profiled.empty:
        return (
            True,
            True,
            "H200 raw artifact는 확보됐지만 주 profiling filter를 통과한 request가 0개다.",
        )
    return True, False, ""


def _source_root_count(source: pd.DataFrame) -> int | None:
    return _count(source, "root_trace_id")


def _root_union(profiled: pd.DataFrame) -> int | None:
    return _count(profiled, "root_trace_id")


def _cross_concurrency_slices(ratios: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Separate baseline rows and coverage-confounded ID-level ratios."""

    if ratios.empty or not {"concurrency", "baseline_concurrency"}.issubset(ratios.columns):
        empty = ratios.iloc[0:0].copy()
        return empty, empty, empty
    current = pd.to_numeric(ratios["concurrency"], errors="coerce")
    baseline = pd.to_numeric(ratios["baseline_concurrency"], errors="coerce")
    cross = ratios.loc[current.notna() & baseline.notna() & (current != baseline)].copy()
    if "coverage_comparable" not in cross:
        return cross, cross.iloc[0:0].copy(), cross
    comparable = cross.loc[
        cross["coverage_comparable"].astype("string").str.strip().str.lower().isin(["true", "1", "yes"])
    ].copy()
    confounded = cross.drop(index=comparable.index).copy()
    return cross, comparable, confounded


def _mapping_evidence(
    profiled: pd.DataFrame,
    mapping: pd.DataFrame,
    source_root_count: int | None,
) -> list[str]:
    """Describe direct loader metadata separately from strict request pairing."""

    profiled_count = len(profiled)
    direct_root = _value_count(profiled, "root_trace_id_provenance", "metadata.source_trace_id")
    if direct_root == 0 and not mapping.empty:
        if "explicit_source_trace_id_request_count" in mapping:
            direct_root = int(
                pd.to_numeric(mapping["explicit_source_trace_id_request_count"], errors="coerce")
                .fillna(0)
                .sum()
            )
    loader_associated = _truthy_count(profiled, "loader_metadata_turn_match")
    strict_exact = _value_count(profiled, "match_class", "exact_turn_match")
    root_ids = _root_union(profiled)
    root_match_rows = _truthy_count(profiled, "source_id_matched")
    if root_match_rows == 0 and not mapping.empty and "h200_request_count" in mapping:
        root_match_rows = int(
            pd.to_numeric(mapping.get("h200_request_count"), errors="coerce").fillna(0).sum()
        )
    evidence = [
        f"source root universe는 `{_display_count(source_root_count)}`개이고, profiling H200 row는 `{_display_count(profiled_count)}`개 / 관측 root trace는 `{_display_count(root_ids)}`개다.",
        (
            "`metadata.source_trace_id`가 root provenance로 기록된 row는 "
            f"`{_display_count(direct_root)}/{_display_count(profiled_count)}` "
            f"({_display_rate(direct_root, profiled_count)})이다. 이는 `::sa:` 문자열 절단 추정이 아니라 loader가 보존한 명시적 source-root metadata다."
        ),
        (
            "source root ID 집합과 일치한 profiling row는 "
            f"`{_display_count(root_match_rows)}/{_display_count(profiled_count)}` "
            f"({_display_rate(root_match_rows, profiled_count)})이다."
        ),
        (
            "loader metadata association (`source_trace_id` + source outer/inner request index)은 "
            f"`{_display_count(loader_associated)}/{_display_count(profiled_count)}` "
            f"({_display_rate(loader_associated, profiled_count)})이고, input length까지 호환되어 strict exact-turn으로 분류된 row는 "
            f"`{_display_count(strict_exact)}/{_display_count(profiled_count)}` "
            f"({_display_rate(strict_exact, profiled_count)})이다."
        ),
    ]
    return evidence


def _empty_or_table(
    frame: pd.DataFrame,
    columns: list[str],
    *,
    empty_text: str,
    limit: int = 20,
) -> str:
    """Render a table or state that an empty table has no rows, not no status."""

    if frame.empty:
        return empty_text
    return _markdown_table(frame, columns, limit)


def _ranked_metric_tables(
    frame: pd.DataFrame,
    metrics: list[str],
    columns: list[str],
    *,
    limit: int,
) -> str:
    """Render top rows per named rank metric instead of an arbitrary file head."""

    if frame.empty or "rank_metric" not in frame:
        return "_Ranked table is unavailable._"
    pieces: list[str] = []
    for metric in metrics:
        ranked = frame.loc[frame["rank_metric"].astype("string") == metric].copy()
        if ranked.empty:
            continue
        if "rank" in ranked:
            ranked = ranked.sort_values("rank", kind="stable")
        pieces.append(
            f"`{metric}` (top {min(limit, len(ranked))} observed root-ID × concurrency rows):\n\n"
            + _markdown_table(ranked, columns, limit)
        )
    return "\n\n".join(pieces) if pieces else "_Requested rank metrics are unavailable._"


def _coverage_evidence(
    coverage: pd.DataFrame,
    profiled: pd.DataFrame,
    source_root_count: int | None,
) -> list[str]:
    observed = _root_union(profiled)
    evidence = [
        (
            "conc1–8 전체에서 한 번 이상 profiling으로 관측된 source root ID는 "
            f"`{_display_count(observed)}/{_display_count(source_root_count)}` "
            f"({_display_rate(observed, source_root_count)})이다."
        ),
        "아래 표의 `root_match_rate`는 해당 concurrency에서 관측된 H200 root ID 중 source ID와 일치한 비율이며, source universe 전체 coverage와는 다른 분모다. `replay_*`는 replay conversation-ID suffix taxonomy, `source_origin_*`는 mapped source trace의 nested-origin taxonomy다.\n\n"
        + _markdown_table(
            coverage,
            [
                "concurrency",
                "profiled_request_count",
                "distinct_root_ids",
                "matched_root_ids",
                "root_match_rate",
                "replay_root_request_count",
                "replay_nonroot_branch_request_count",
                "replay_unknown_branch_request_count",
                "source_origin_root_request_count",
                "source_origin_subagent_request_count",
                "source_origin_unknown_branch_request_count",
                "total_input_tokens",
                "total_output_tokens",
            ],
            20,
        ),
    ]
    return evidence


def _validation_evidence(validation: pd.DataFrame) -> list[str]:
    if validation.empty:
        return ["aggregate validation table이 비어 있어 raw-to-published comparison을 산출하지 못했다."]
    status_column = "validation_status" if "validation_status" in validation else "status"
    statuses = validation[status_column].astype("string").value_counts(dropna=False)
    counts = ", ".join(f"`{name}`={int(count):,}" for name, count in statuses.items())
    passing = _status_count(validation, status_column, {"pass", "pass_alias_equivalent"})
    return [
        (
            f"raw-to-published aggregate comparison은 `{len(validation):,}`개이고 status 분포는 {counts}이다. "
            f"`pass` 또는 `pass_alias_equivalent` row는 `{passing:,}/{len(validation):,}`개다."
        ),
        "`pass_alias_equivalent`는 문서화된 target model label alias의 categorical comparison이며, 수치 metric의 추가 정밀도 검증을 뜻하지 않는다.",
        "검증 표에는 aggregate artifact context와 원본/재계산 값, tolerance, status를 함께 보존한다.\n\n"
        + _markdown_table(
            validation,
            [
                "concurrency",
                "metric",
                "published",
                "recomputed",
                "absolute_delta",
                "relative_delta",
                "status",
            ],
            50,
        ),
    ]


def generate_reports(root: Path) -> list[Path]:
    """Create report files from currently persisted analysis outputs."""

    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    run = read_json(root / "manifests" / "github_run.json", {}) or {}
    artifacts = read_json(root / "manifests" / "github_artifacts.json", {}) or {}
    provenance = read_json(root / "manifests" / "provenance.json", {}) or {}
    source = _read_table(root, "source_trace_summary")
    source_requests = _read_table(root, "source_requests")
    source_models = _read_table(root, "source_model_workload_summary")
    h200_all = _read_table(root, "h200_requests_all")
    h200_profiled = _read_table(root, "h200_requests_profiled")
    artifact_profile_counts = _read_table(root, "artifact_profile_counts")
    schema = _read_table(root, "artifact_schema")
    mapping = _read_table(root, "id_mapping_summary")
    mapping_rules = _read_table(root, "id_normalization_rule_summary")
    mapping_examples = _read_table(root, "unmatched_h200_id_examples")
    coverage = _read_table(root, "concurrency_coverage_summary")
    coverage_bias = _read_table(root, "coverage_bias_summary")
    coverage_model_composition = _read_table(root, "coverage_bias_model_composition")
    summary = _read_table(root, "id_concurrency_summary")
    weighting = _read_table(root, "weighting_summary")
    branch_summary = _read_table(root, "root_subagent_summary")
    replay_branch_summary = _read_table(root, "replay_branch_type_summary")
    source_origin_branch_summary = _read_table(root, "source_origin_branch_summary")
    if source_origin_branch_summary.empty:
        source_origin_branch_summary = _read_table(root, "source_branch_origin_summary")
    session_diagnostics = _read_table(root, "session_num_grouping_diagnostics")
    ratios = _read_table(root, "id_concurrency_ratios")
    paired = _read_table(root, "paired_turn_comparisons")
    paired_bootstrap = _read_table(root, "paired_ratio_cluster_bootstrap")
    exact_cache = _read_table(root, "exact_turn_cache_shape")
    cache_relationship = _read_table(root, "cache_shape_relationship_summary")
    validation = _read_table(root, "aggregate_validation")
    top_workload = _read_table(root, "top_ids_by_workload")
    top_latency = _read_table(root, "top_ids_by_latency")
    h200_build_status = read_json(root / "data" / "processed" / "h200_build_status.json", {}) or {}
    coverage_status = read_json(root / "data" / "processed" / "coverage_status.json", {}) or {}
    outputs: list[Path] = []

    source_root_count = _source_root_count(source)
    source_request_count = len(source_requests)
    source_input_total = (
        int(pd.to_numeric(source_requests["source_input_tokens"], errors="coerce").fillna(0).sum())
        if "source_input_tokens" in source_requests
        else None
    )
    source_output_total = (
        int(pd.to_numeric(source_requests["source_output_tokens"], errors="coerce").fillna(0).sum())
        if "source_output_tokens" in source_requests
        else None
    )
    source_ttft_rate = (
        float(source_requests["source_ttft_s"].notna().mean())
        if "source_ttft_s" in source_requests and not source_requests.empty
        else None
    )
    h200_available, h200_completed_zero, h200_reason = _h200_state(
        h200_build_status, h200_profiled
    )
    coverage_blocked = (
        not h200_available or coverage_status.get("status") == "blocked_no_profile_export"
    )
    coverage_reason = (
        h200_reason
        if not h200_available or h200_completed_zero
        else "coverage stage output이 없으므로 source/H200 coverage를 측정할 수 없다."
    )
    profiled_rows = len(h200_profiled)
    all_rows = len(h200_all)
    excluded_rows = max(all_rows - profiled_rows, 0) if h200_available else None
    profiled_itl_count = int(h200_profiled["itl_ms"].notna().sum()) if "itl_ms" in h200_profiled else 0
    key_metric_fields = {
        "metrics.input_sequence_length.value",
        "metrics.output_sequence_length.value",
        "metrics.time_to_first_token.value",
        "metrics.time_to_first_output_token.value",
        "metrics.request_latency.value",
        "metrics.inter_token_latency.value",
    }
    schema_key_metrics = (
        schema.loc[schema["field"].isin(key_metric_fields)].sort_values(["field", "concurrency"])
        if "field" in schema
        else pd.DataFrame()
    )
    run_metadata_phrase = "GitHub run metadata가 저장됨" if run else "GitHub run metadata를 아직 확보하지 못함"
    cross_ratios, comparable_ratios, confounded_ratios = _cross_concurrency_slices(ratios)
    paired_same_output = _numeric_equal_count(paired, "output_token_delta", 0.0)
    paired_output_present = _present_count(paired, "output_token_delta")
    paired_changed_output = max(paired_output_present - paired_same_output, 0)
    paired_conc1_baseline = _truthy_count(paired, "baseline_available_at_conc1")
    exact_cache_rows = len(exact_cache)

    provenance_path = reports / "01_provenance.md"
    # Acquisition writes a fuller same-SHA source-location report.  Preserve
    # it rather than replacing source citations with a generic template.
    if not provenance_path.exists():
        _write(
            provenance_path,
            "01. Provenance and expected-environment verification",
            [
                (
                    f"GitHub run metadata saved: {'yes' if run else 'no'}; run ID: "
                    f"`{run.get('id', 'unavailable')}`; head SHA: "
                    f"`{run.get('head_sha', 'unavailable')}`; branch: "
                    f"`{run.get('head_branch', 'unavailable')}`."
                ),
                f"artifact inventory entries saved: `{len(artifacts.get('artifacts', []))}`.",
                f"Hugging Face provenance manifest: `{json.dumps(provenance.get('huggingface', {}), ensure_ascii=False)}`.",
            ],
            [
                "same-SHA workflow/config and run metadata together support the intended GLM-5.2 FP8 H200 replay environment only to the scope cited in the provenance report."
            ],
            [
                "per-request command overrides, cache residency, and server state cannot be inferred solely from expected configuration."
            ],
        )
    outputs.append(provenance_path)

    schema_path = reports / "02_artifact_schema.md"
    _write(
        schema_path,
        "02. H200 profile_export schema inventory",
        (
            [
                (
                    f"H200 raw record rows `{_display_count(all_rows)}`, valid profiling rows "
                    f"`{_display_count(profiled_rows)}`, excluded rows "
                    f"`{_display_count(excluded_rows)}`.\n\n"
                    + _markdown_table(
                        artifact_profile_counts,
                        [
                            "concurrency",
                            "record_count",
                            "profiling_phase_count",
                            "warmup_count",
                            "missing_phase_count",
                            "error_count",
                            "cancelled_count",
                        ],
                        20,
                    )
                    + "\n\nField inventory:\n\n"
                    + _markdown_table(
                        schema,
                        [
                            "field",
                            "presence_rate",
                            "dtype",
                            "null_rate",
                            "min",
                            "max",
                            "observed_unit",
                            "observed_unit_values",
                            "inferred_unit",
                        ],
                        40,
                    )
                    + "\n\nKey request-metric fields (per concurrency):\n\n"
                    + _markdown_table(
                        schema_key_metrics,
                        [
                            "concurrency",
                            "field",
                            "present_count",
                            "presence_rate",
                            "min",
                            "max",
                            "observed_unit",
                            "inferred_unit",
                        ],
                        60,
                    )
                )
            ]
            if h200_available and not h200_completed_zero
            else [h200_reason]
        ),
        [
            "`inter_token_latency` is named request-level ITL/TPOT only to the extent established by the InferenceX aggregation source; it is not a per-GPU decode measurement."
        ],
        [
            h200_reason
            if not h200_available
            else (
                f"ITL is observed for `{profiled_itl_count:,}/{profiled_rows:,}` valid profiling rows; "
                "missing per-row values and absent actual cache-residency telemetry limit metric interpretation."
            )
        ],
    )
    outputs.append(schema_path)

    mapping_path = reports / "03_id_mapping.md"
    _write(
        mapping_path,
        "03. Conversation-ID and root-trace mapping",
        (
            _mapping_evidence(h200_profiled, mapping, source_root_count)
            + [
                "Per-concurrency mapping summary:\n\n"
                + _markdown_table(
                    mapping,
                    [
                        "concurrency",
                        "h200_request_count",
                        "h200_root_ids",
                        "matched_root_ids",
                        "root_match_rate",
                        "loader_metadata_turn_match_rate",
                        "exact_turn_match_count",
                        "exact_turn_match_rate",
                        "explicit_source_trace_id_match_rate",
                    ],
                    20,
                ),
                "Normalization rules across all raw H200 rows:\n\n"
                + _markdown_table(
                    mapping_rules,
                    [
                        "concurrency",
                        "normalization_rule",
                        "h200_request_count",
                        "distinct_conversation_ids",
                        "distinct_root_trace_ids",
                        "source_matched_request_count",
                        "source_request_match_rate",
                    ],
                    20,
                ),
            ]
            if h200_available and not h200_completed_zero
            else [f"source root trace universe is `{_display_count(source_root_count)}` IDs; {h200_reason}"]
        ),
        [
            "a `::sa:` split remains a fallback normalization rule. Where `metadata.source_trace_id` is present, the direct loader field is stronger root-ID evidence."
        ],
        [
            (
                "loader metadata association is not, by itself, a strict source/H200 turn identity. "
                "This pipeline labels a strict exact turn only when that association also has compatible input length; it does not claim independently verified request timing/order identity."
            ),
            h200_reason
            if not h200_available
            else "The absence of an unmatched-example row does not prove full source-turn coverage; it only means no unmatched H200 root-ID example was emitted by this stage.\n\n"
            + _empty_or_table(
                mapping_examples,
                [
                    "concurrency",
                    "example_conversation_id",
                    "root_trace_id",
                    "normalization_rule",
                    "unmatched_request_count",
                ],
                empty_text="_No unmatched H200 root-ID example rows were emitted._",
                limit=20,
            ),
        ],
    )
    outputs.append(mapping_path)

    coverage_path = reports / "04_coverage.md"
    _write(
        coverage_path,
        "04. Coverage by concurrency",
        (
            _coverage_evidence(coverage, h200_profiled, source_root_count)
            + [
                "Observed vs never-observed source workload shape (source medians; this is a coverage-bias diagnostic, not a target-model comparison):\n\n"
                + _markdown_table(
                    coverage_bias,
                    [
                        "concurrency",
                        "observation_group",
                        "source_trace_count",
                        "source_request_count_total_median",
                        "source_recorded_span_s_median",
                        "source_total_input_tokens_median",
                        "source_total_output_tokens_median",
                        "source_subagent_count_median",
                        "source_max_input_tokens_median",
                    ],
                    20,
                ),
                "Source workload-model-label composition by observation group (labels are source provenance, not target-model classes):\n\n"
                + _markdown_table(
                    coverage_model_composition,
                    [
                        "concurrency",
                        "observation_group",
                        "source_model",
                        "source_trace_count_with_model",
                        "source_trace_count_in_group",
                        "source_model_trace_share",
                    ],
                    40,
                )
            ]
            if not coverage_blocked and not h200_completed_zero
            else [
                "Source trace universe is available, but H200 profiling coverage cannot be measured because raw artifacts are unavailable."
                if not h200_available
                else h200_reason
            ]
        ),
        [
            "different observed ID sets can reflect fixed-duration replay, warmup point, recycling, scheduling, or concurrency; coverage differences are not automatically performance effects."
        ],
        [
            coverage_reason
            if coverage_blocked
            else "source coverage does not establish that every source trace or turn was replayed at every concurrency."
        ],
    )
    outputs.append(coverage_path)

    id_path = reports / "05_id_level_results.md"
    _write(
        id_path,
        "05. ID-level observed H200 replay results",
        (
            [
                (
                    f"valid profiling rows `{_display_count(profiled_rows)}` are summarized into "
                    f"`{_display_count(len(summary))}` root-ID × concurrency rows. `session_num` groups are retained "
                    "as opaque/unvalidated metadata and are not treated as independent replay instances.\n\n"
                    + _markdown_table(
                        weighting,
                        ["weighting", "sample_count", "median_ttft_ms", "median_itl_ms", "median_e2e_ms"],
                        10,
                    )
                ),
                "ID-concurrency table (trace IDs are shortened only in reports; full public IDs remain in CSV/Parquet):\n\n"
                + _markdown_table(
                    summary,
                    [
                        "root_trace_id",
                        "concurrency",
                        "distinct_replay_instances",
                        "session_num_group_count",
                        "session_num_unique_row_rate",
                        "replay_instance_identity_status",
                        "profiled_request_count",
                        "root_request_count",
                        "subagent_request_count",
                        "median_ttft_ms",
                        "median_itl_ms",
                        "median_e2e_ms",
                        "wall_clock_output_rate",
                        "sample_quality_flag",
                    ],
                    25,
                ),
                (
                    "Replay branch taxonomy is parsed from H200 conversation-ID suffixes; source-origin taxonomy is inherited from mapped nested source traces. They are separate dimensions, not interchangeable root/subagent labels.\n\n"
                    "Replay branch summary:\n\n"
                    + _empty_or_table(
                        replay_branch_summary if not replay_branch_summary.empty else branch_summary,
                        [
                            "concurrency",
                            "branch_type",
                            "profiled_request_count",
                            "distinct_root_ids",
                            "median_input_tokens",
                            "median_ttft_ms",
                            "median_itl_ms",
                            "median_e2e_ms",
                            "error_count",
                            "cancellation_count",
                        ],
                        empty_text="_Replay branch summary is unavailable._",
                        limit=40,
                    )
                    + "\n\nSource-origin branch summary:\n\n"
                    + _empty_or_table(
                        source_origin_branch_summary,
                        [
                            "concurrency",
                            "source_branch_type",
                            "source_origin_branch_type",
                            "profiled_request_count",
                            "distinct_root_ids",
                            "median_input_tokens",
                            "median_ttft_ms",
                            "median_itl_ms",
                            "median_e2e_ms",
                            "error_count",
                            "cancellation_count",
                        ],
                        empty_text="_Source-origin branch summary is unavailable._",
                        limit=40,
                    )
                ),
                (
                    "`session_num` is retained as a replay grouping field; its observed uniqueness is diagnostic, not evidence that rows are independent replay instances.\n\n"
                    + _empty_or_table(
                        session_diagnostics,
                        [
                            "scope",
                            "concurrency",
                            "profiled_request_count",
                            "non_null_session_num_count",
                            "distinct_session_num",
                            "distinct_concurrency_session_num",
                            "duplicate_concurrency_session_num_row_count",
                            "session_num_unique_row_rate",
                            "session_num_uniqueness_key",
                            "session_num_semantics",
                            "replay_instance_identity_status",
                            "cross_concurrency_cluster_unit",
                        ],
                        empty_text="_Session-number grouping diagnostics are unavailable._",
                        limit=20,
                    )
                ),
            ]
            if h200_available and not h200_completed_zero
            else [h200_reason]
        ),
        [
            "request-weighted and root-ID-weighted values answer different questions. They must not be compared as interchangeable estimates, especially when replay coverage is uneven. Root trace ID, rather than session number, is the conservative cluster unit for paired bootstrap reporting."
        ],
        [
            h200_reason
            if not h200_available
            else "`session_num` semantic identity is not validated as a de-correlated replay-instance identifier. A conversation ID remains a workload identifier; no available table supports per-ID GPU count, utilization, or hardware-affinity attribution."
        ],
    )
    outputs.append(id_path)

    conc_path = reports / "06_cross_concurrency.md"
    paired_evidence = (
        [
            (
                f"strict-exact turn filter에서 나온 paired cross-concurrency row는 `{len(paired):,}`개다. "
                f"각 side의 target replay `output_tokens`를 그대로 유지하며, source output length로 대체하지 않는다. "
                f"동일 observed output token row는 `{paired_same_output:,}/{paired_output_present:,}`, "
                f"서로 다른 observed output token row는 `{paired_changed_output:,}/{paired_output_present:,}`이다."
            ),
            (
                f"paired rows 중 conc1을 baseline으로 가진 row는 `{paired_conc1_baseline:,}/{len(paired):,}`개다; "
                "나머지는 해당 exact turn의 최소 관측 concurrency를 baseline으로 사용한다."
            ),
            "Strict-exact paired table:\n\n"
            + _markdown_table(
                paired,
                [
                    "root_trace_id",
                    "concurrency",
                    "baseline_concurrency",
                    "matched_sample_count",
                    "baseline_matched_sample_count",
                    "output_tokens",
                    "baseline_output_tokens",
                    "output_token_delta",
                    "ttft_ratio",
                    "itl_ratio",
                    "e2e_ratio",
                ],
                25,
            ),
            "Root-ID clustered bootstrap summary:\n\n"
            + _markdown_table(
                paired_bootstrap,
                [
                    "concurrency",
                    "metric",
                    "paired_turn_count",
                    "root_id_cluster_count",
                    "median_ratio",
                    "bootstrap_ci_low",
                    "bootstrap_ci_high",
                    "n_bootstrap",
                ],
                30,
            ),
        ]
        if not paired.empty
        else ["strict-exact source/H200 turn pair가 없어 paired concurrency comparison을 산출하지 못했다."]
    )
    _write(
        conc_path,
        "06. Cross-concurrency comparisons",
        (
            [
                (
                    f"ID-level ratio rows `{len(ratios):,}` 중 baseline self-row를 제외한 cross-concurrency row는 `{len(cross_ratios):,}`개다. "
                    f"coverage-comparable row는 `{len(comparable_ratios):,}`, coverage-confounded row는 `{len(confounded_ratios):,}`개다."
                ),
                "아래 ID-level ratio 표는 coverage-comparable cross-concurrency rows만 제시한다. 이 표에 없는 cross-concurrency ratio는 workload/request/token coverage가 달라져 degradation evidence로 사용하지 않는다.\n\n"
                + _markdown_table(
                    comparable_ratios,
                    [
                        "root_trace_id",
                        "concurrency",
                        "baseline_concurrency",
                        "ttft_ratio",
                        "itl_ratio",
                        "e2e_ratio",
                        "wall_clock_output_rate_ratio",
                        "request_coverage_ratio",
                        "input_token_coverage_ratio",
                        "output_token_coverage_ratio",
                    ],
                    25,
                ),
                *paired_evidence,
                f"strict exact source/H200 rows for theoretical cache-shape analysis: `{exact_cache_rows:,}`.\n\n"
                + _markdown_table(
                    cache_relationship,
                    [
                        "concurrency",
                        "branch_group",
                        "exact_turn_request_count",
                        "distinct_root_ids",
                        "median_ttft_ms",
                        "median_theoretical_new_tokens",
                        "median_theoretical_cache_ratio",
                        "spearman_ttft_vs_theoretical_new_tokens",
                        "spearman_ttft_vs_theoretical_cache_ratio",
                    ],
                    40,
                ),
            ]
            if h200_available and not h200_completed_zero
            else [h200_reason]
        ),
        [
            "coverage-comparable ID-level ratios and strict-exact paired rows are descriptive replay comparisons, not proof of a monotonic or causal concurrency degradation."
        ],
        [
            h200_reason
            if not h200_available
            else "coverage-confounded rows, unpaired rows, shared-system scheduling, and small exact-pair counts prevent population-level causal claims."
        ],
    )
    outputs.append(conc_path)

    validation_path = reports / "07_validation.md"
    _write(
        validation_path,
        "07. Raw-to-published aggregate validation",
        (
            _validation_evidence(validation)
            if h200_available and not h200_completed_zero
            else [h200_reason]
        ),
        [
            "a pass supports only the encoded filter, unit conversion, percentile method, time window, and aggregate metric mapping; it does not validate every individual request attribution."
        ],
        [
            h200_reason
            if not h200_available
            else "aggregate validation remains unavailable for any metric lacking a unique published candidate or a compatible raw recomputation."
        ],
    )
    outputs.append(validation_path)

    limitation_path = reports / "08_limitations.md"
    _write(
        limitation_path,
        "08. Limitations",
        [
            "source `api_time` is collection-time provenance and is not an observed H200 replay latency.",
            "source model labels are workload provenance, not target model identities.",
            "the server is a shared system; conversation IDs do not establish GPU allocation or affinity.",
        ],
        [
            "theoretical hash-prefix reuse describes source workload shape only unless an artifact provides an actual cache metric at the relevant scope.",
        ],
        [
            "fixed-duration replay completeness, per-ID GPU utilization, fixed hardware assignment, direct Anthropic-versus-GLM model comparison, and independent-request confidence intervals are not established by these records.",
        ],
    )
    outputs.append(limitation_path)

    ko_path = reports / "results_summary_ko.md"
    ko_lines = [
        "# 분석 대상",
        "",
        "- **Evidence:** 공개 InferenceX GitHub Actions run `29820102138`과 `semianalysisai/cc-traces-weka-062126` source workload trace를 분석 대상으로 고정했다.",
        "- **Evidence:** source `model`은 Claude Code 수집 시의 workload label이다. H200 target `GLM-5.2 FP8` replay 성능과 동일시하지 않도록 별도 field로 보존한다.",
        "",
        "# H200 환경 검증",
        "",
        f"- **Evidence:** {run_metadata_phrase}; same-SHA InferenceX config/recipe는 target `GLM-5.2 FP8`, shared 16×H200, Dynamo+SGLang, Mooncake, HiSparse, 1,048,576 context, conc1–8을 명시한다 (`01_provenance.md`).",
        "- **Inference:** successful run metadata와 same-SHA recipe의 조합은 의도된 GLM-5.2 FP8 H200 replay 환경이라는 해석을 뒷받침한다 (confidence: 높음 for recipe association).",
        "- **Unknown:** per-request command override, queue/server state, actual cache residency는 aggregate/config만으로 확정할 수 없다.",
        "",
        "# 데이터와 ID 연결 방식",
        "",
        f"- **Evidence:** source root trace `{_display_count(source_root_count)}`개, source request `{_display_count(source_request_count)}`개를 flattened table로 보존했다.",
        "- **Evidence:** `metadata.source_trace_id`는 loader가 raw H200 row에 보존한 source-root evidence다. `::sa:` split은 metadata가 없을 때의 fallback이며, direct metadata와 동일한 강도로 주장하지 않는다.",
    ]
    if h200_available and not h200_completed_zero:
        direct_root = _value_count(
            h200_profiled, "root_trace_id_provenance", "metadata.source_trace_id"
        )
        loader_associated = _truthy_count(h200_profiled, "loader_metadata_turn_match")
        strict_exact = _value_count(h200_profiled, "match_class", "exact_turn_match")
        ko_lines.extend(
            [
                f"- **Evidence:** profiling H200 row `{profiled_rows:,}`개 중 `metadata.source_trace_id` root provenance `{direct_root:,}`개 ({_display_rate(direct_root, profiled_rows)}), loader metadata association `{loader_associated:,}`개 ({_display_rate(loader_associated, profiled_rows)}), input-compatible strict exact-turn `{strict_exact:,}`개 ({_display_rate(strict_exact, profiled_rows)})다.",
                "- **Unknown:** loader metadata association은 source outer/inner index 연결 evidence이지만, strict exact-turn도 input length compatibility까지의 보수적 기준이다. 독립적인 시간/order identity를 추가로 증명하지 않는다.",
            ]
        )
    else:
        ko_lines.extend(
            [
                f"- **Unknown:** {h200_reason} H200 ID match rate를 0으로 해석하지 않는다.",
            ]
        )
    ko_lines.extend(
        [
            "",
            "# ID coverage",
            "",
        ]
    )
    if not coverage_blocked and not h200_completed_zero:
        observed_roots = _root_union(h200_profiled)
        ko_lines.extend(
            [
                f"- **Evidence:** conc1–8 전체에서 profiling으로 한 번 이상 관측된 root ID는 `{_display_count(observed_roots)}/{_display_count(source_root_count)}` ({_display_rate(observed_roots, source_root_count)})다.",
                "- **Evidence:** concurrency별 observed root-ID / profiling request / token coverage와 replay suffix vs source-origin branch count를 `04_coverage.md`와 `id_coverage_matrix.csv`에 보존했다. 각 concurrency의 observed H200 ID가 source ID와 일치하는 비율과 source universe coverage는 분모가 다르다.",
                "- **Inference:** observed ID set 차이는 fixed-duration replay, warmup, recycling, scheduling 또는 concurrency에 따른 coverage bias일 수 있으므로 성능 비교 전에 통제한다.",
            ]
        )
    else:
        ko_lines.append(f"- **Unknown:** {coverage_reason} 0으로 해석하지 않는다.")
    ko_lines.extend(
        [
            "",
            "# ID별 성능 핵심 결과",
            "",
        ]
    )
    if h200_available and not h200_completed_zero:
        ko_lines.extend(
            [
                f"- **Evidence:** valid profiling row `{profiled_rows:,}`개를 root-ID × concurrency `{len(summary):,}`개로 집계했다. `session_num` group은 opaque/unvalidated metadata이며 독립 replay instance로 취급하지 않는다. request-weighted/root-ID-weighted 결과는 `weighting_summary.csv`에서 분리한다.",
                "- **Evidence:** TTFT, request-level ITL/TPOT, E2E는 profiling·성공·비취소·유효 metric filter의 observed target H200 replay 값이다. source `api_time`과 동일 조건 값으로 비교하지 않는다.",
                "- **Unknown:** conversation ID별 GPU 수, GPU utilization, 또는 GPU affinity는 이 shared 16×H200 record에서 식별할 수 없다.",
            ]
        )
    else:
        ko_lines.append(f"- **Unknown:** {h200_reason}")
    ko_lines.extend(
        [
            "",
            "# Concurrency 1~8 비교",
            "",
        ]
    )
    if h200_available and not h200_completed_zero:
        ko_lines.extend(
            [
                f"- **Evidence:** ID-level ratio `{len(ratios):,}`개 중 실제 cross-concurrency ratio `{len(cross_ratios):,}`개, coverage-comparable `{len(comparable_ratios):,}`개, coverage-confounded `{len(confounded_ratios):,}`개다. confounded row는 degradation evidence로 사용하지 않는다.",
                f"- **Evidence:** strict-exact paired H200 comparison `{len(paired):,}`개는 target replay의 실제 양쪽 `output_tokens`를 유지한다. 같은 output `{paired_same_output:,}/{paired_output_present:,}`, 다른 output `{paired_changed_output:,}/{paired_output_present:,}`이며 conc1 baseline pair는 `{paired_conc1_baseline:,}/{len(paired):,}`개다.",
                "- **Inference:** coverage-comparable ID-level ratio 및 strict-exact pair는 조건부 descriptive comparison이다. monotonic concurrency degradation 또는 단일 원인으로 해석하지 않는다 (confidence: 낮음~중간; paired sample count에 의존).",
            ]
        )
    else:
        ko_lines.append(f"- **Unknown:** {h200_reason}")
    ko_lines.extend(
        [
            "",
            "# Root agent와 subagent 비교",
            "",
            "- **Evidence:** H200 replay `branch_type`은 conversation-ID suffix taxonomy이고, `source_branch_type`/`source_origin_branch_type`은 mapped source nested trace origin taxonomy다. 둘은 source-origin과 replay structure를 나타내는 서로 다른 field다.",
        ]
    )
    if h200_available and not h200_completed_zero:
        ko_lines.append(
            "- **Evidence:** replay suffix taxonomy는 `replay_branch_type_summary.csv`/`root_subagent_summary.csv`, source-origin taxonomy는 `source_origin_branch_summary.csv`에 concurrency별로 분리한다. label 차이 자체를 target model 차이로 해석하지 않는다."
        )
        ko_lines.append(
            "- **Unknown:** `session_num`은 replay grouping field로 보존하지만 semantic replay-instance identity나 request independence를 증명하지 않는다. paired bootstrap은 보수적으로 root trace ID를 cluster unit으로 사용한다."
        )
    else:
        ko_lines.append(f"- **Unknown:** {h200_reason}")
    ko_lines.extend(
        [
            "",
            "# Context 및 theoretical cache reuse 영향",
            "",
            "- **Evidence:** source hash ID longest-common-prefix로 계산한 theoretical cache reuse는 source workload shape다. actual H200 server cache residency/hit와 동일하지 않다.",
            f"- **Evidence:** strict exact source/H200 row `{exact_cache_rows:,}`개에서만 theoretical new tokens/cache ratio와 observed H200 TTFT의 관계를 `cache_shape_relationship_summary.csv`로 계산했다.",
            "- **Unknown:** actual cache metric이 request scope에서 없으면 cache ratio와 TTFT의 인과 관계를 확정할 수 없다.",
            "",
            "# 가장 부담이 큰 trace IDs",
            "",
        ]
    )
    if h200_available and not h200_completed_zero:
        ko_lines.extend(
            [
                "- **Evidence:** 아래 ranking은 observed root-ID × concurrency row 기준이다. full public trace ID와 sample count는 CSV/Parquet에 보존한다.\n\n"
                + _ranked_metric_tables(
                    top_workload,
                    ["total_input_tokens", "total_output_tokens", "replay_nonroot_branch_request_count"],
                    [
                        "rank",
                        "root_trace_id",
                        "concurrency",
                        "profiled_request_count",
                        "rank_metric",
                        "total_input_tokens",
                        "total_output_tokens",
                        "median_ttft_ms",
                        "sample_quality_flag",
                    ],
                    limit=5,
                )
                + "\n\nLatency / wall-time / low-output-rate ranking:\n\n"
                + _ranked_metric_tables(
                    top_latency,
                    [
                        "median_ttft_ms",
                        "p90_ttft_ms",
                        "median_e2e_ms",
                        "total_h200_wall_time_s",
                        "wall_clock_output_rate",
                    ],
                    [
                        "rank",
                        "root_trace_id",
                        "concurrency",
                        "profiled_request_count",
                        "rank_metric",
                        "median_ttft_ms",
                        "p90_ttft_ms",
                        "median_e2e_ms",
                        "p90_e2e_ms",
                        "total_h200_wall_time_s",
                        "wall_clock_output_rate",
                        "sample_quality_flag",
                    ],
                    limit=5,
                ),
                "- **Inference:** 높은 observed workload 또는 wall time rank는 해당 run/coverage의 부담을 보여 주지만, 모든 source trace의 전역 rank나 GPU affinity를 뜻하지 않는다.",
            ]
        )
    else:
        ko_lines.append(f"- **Unknown:** {h200_reason}")
    ko_lines.extend(
        [
            "",
            "# Aggregate 결과 재현 검증",
            "",
        ]
    )
    if h200_available and not h200_completed_zero:
        status_column = "validation_status" if "validation_status" in validation else "status"
        passing = _status_count(validation, status_column, {"pass", "pass_alias_equivalent"})
        ko_lines.extend(
            [
                f"- **Evidence:** raw-to-published aggregate validation `{len(validation):,}`개 중 `{passing:,}`개가 `pass` 또는 documented alias-equivalent 상태다. metric별 raw/published/tolerance/status는 `aggregate_validation.csv`에 보존했다.",
                "- **Inference:** 이 일치는 선택한 raw filter·unit conversion·percentile·time-window 구현의 재현 evidence이며, ID-level mapping의 완전성 또는 causal interpretation을 보장하지 않는다.",
            ]
        )
    else:
        ko_lines.append(f"- **Unknown:** {h200_reason}")
    ko_lines.extend(
        [
            "",
            "# 확인된 사실",
            "",
            f"- **Evidence:** source workload는 `{_display_count(source_root_count)}` root trace / `{_display_count(source_request_count)}` request이며 입력 `{_display_count(source_input_total)}` tokens, 출력 `{_display_count(source_output_total)}` tokens이다.",
            (
                f"- **Evidence:** source `ttft` 존재율은 `{source_ttft_rate:.1%}`이다. source `api_time`은 source collection provenance이며 observed H200 replay latency와 분리한다."
                if source_ttft_rate is not None
                else "- **Evidence:** source `api_time`과 observed H200 replay latency는 다른 관측값으로 분리해 보존한다."
            ),
            "- **Evidence:** conversation ID는 workload trace 식별자이며 GPU 식별자가 아니다.",
            "",
            "# Source model label별 workload shape",
            "",
            "- **Evidence:** 아래 label은 source Claude Code workload provenance이며 target GLM-5.2 target-model 성능 분류가 아니다.\n\n"
            + _markdown_table(
                source_models,
                [
                    "source_model",
                    "source_request_count",
                    "distinct_root_trace_ids",
                    "median_input_tokens",
                    "p90_input_tokens",
                    "median_output_tokens",
                ],
                20,
            ),
            "- **Inference:** source model label과 H200 replay latency의 관계를 해석하려면 root ID, context, source-origin branch, replay branch, concurrency 및 coverage를 함께 통제해야 한다.",
            "",
            "# 추론",
            "",
            "- **Inference:** same-SHA recipe와 successful run metadata는 target GLM-5.2 FP8 H200 replay라는 해석을 뒷받침하지만, per-request override까지 증명하지는 않는다 (confidence: 높음 for recipe association; 낮음 for unobserved overrides).",
            "",
            "# 확인할 수 없는 것",
            "",
            "- **Unknown:** source/target model 직접 성능 비교, ID별 GPU attribution, source API measurement와 H200 replay measurement의 동등 조건 비교.",
            "",
            "# 데이터 한계",
            "",
            "- **Unknown:** fixed-duration replay의 warmup, recycling, scheduling, cancellation, repeated row, shared-system effect가 observed distribution에 미친 정확한 정도.",
            "",
            "# 재현 방법",
            "",
            "```sh\nmake bootstrap\ngh auth login --web --git-protocol ssh\nmake acquire-run\nmake all\n```",
            "",
            f"생성 시각(UTC): `{utc_now()}`",
            "",
        ]
    )
    ko_path.write_text("\n".join(ko_lines), encoding="utf-8")
    outputs.append(ko_path)
    return outputs
