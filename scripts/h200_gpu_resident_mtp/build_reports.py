#!/usr/bin/env python3
"""Render study reports, figures, and the GitHub-first ChatGPT handoff."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import matplotlib
import pandas as pd

# The analysis is designed to run headlessly in CI/remote Codex sessions.
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
STUDY_ROOT_DEFAULT = REPOSITORY_ROOT / "studies/h200_gpu_resident_mtp"
ANALYSIS_START_COMMIT = "5411307f0be9e481a37a80d5ee477faf81c16c8c"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-root", type=Path, default=STUDY_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.study_root
    processed = root / "processed"
    reports = root / "reports"
    figures = root / "figures"
    handoff = root / "handoff"
    for path in (reports, figures, handoff):
        path.mkdir(parents=True, exist_ok=True)
    tables = {path.stem: _read_csv(path) for path in processed.glob("*.csv")}
    tables["artifact_inventory"] = _read_csv(root / "manifests" / "artifact_inventory.csv")
    recipe = _read_json(root / "manifests/source_recipe_evidence.json")
    runtime = _read_json(root / "manifests/runtime_log_evidence.json")
    _augment_runtime_configuration(processed, tables.get("runtime_configuration", pd.DataFrame()), runtime)
    tables["runtime_configuration"] = _read_csv(processed / "runtime_configuration.csv")
    _augment_mtp_metrics(processed, tables.get("mtp_metrics", pd.DataFrame()), runtime)
    tables["mtp_metrics"] = _read_csv(processed / "mtp_metrics.csv")
    _write_kv_runtime(processed, recipe, runtime)
    tables["kv_cache_runtime"] = _read_csv(processed / "kv_cache_runtime.csv")
    _build_figures(figures, tables)
    _build_reports(reports, tables, recipe, runtime)
    _build_handoff(handoff, tables, recipe, runtime)
    print(json.dumps({"status": "completed", "report_dir": str(reports)}, ensure_ascii=False))
    return 0


def _build_reports(
    reports: Path,
    tables: dict[str, pd.DataFrame],
    recipe: dict[str, Any],
    runtime: dict[str, Any],
) -> None:
    concurrency = tables.get("concurrency_summary", pd.DataFrame())
    cache = tables.get("cache_metrics", pd.DataFrame())
    mtp = tables.get("mtp_metrics", pd.DataFrame())
    resolution = tables.get("requested_id_resolution", pd.DataFrame())
    comparison = tables.get("h200_c8_hisparse_vs_gpu_resident", pd.DataFrame())
    validation = tables.get("validation_summary", pd.DataFrame())
    runtime_text = _runtime_evidence_text(runtime)
    _write(
        reports / "00_provenance.md",
        "# 00. Provenance\n\n"
        "## Evidence\n\n"
        f"- Public InferenceX Actions run: `{_recipe_value(recipe, ['actions_run', 'id']) or 'Unknown'}`.\n"
        f"- Canonical execution SHA: `{_recipe_value(recipe, ['actions_run', 'head_sha']) or 'Unknown'}`.\n"
        f"- Associated PR: `#{_recipe_value(recipe, ['pull_request', 'number']) or 'Unknown'}`.\n"
        "- Raw result, aggregate, and server-log artifact inventory is recorded in "
        "`../manifests/artifact_inventory.csv`.\n\n"
        "## Inference\n\n"
        "- The at-run SHA, not current `main` or a post-merge PR head, is the canonical configuration ref.\n\n"
        "## Unknown\n\n"
        "- Artifact evidence alone cannot establish per-request GPU affinity or independent request samples.\n",
    )
    _write(
        reports / "01_runtime_architecture.md",
        "# 01. Runtime architecture\n\n"
        "## Evidence\n\n"
        + _table(tables.get("runtime_configuration", pd.DataFrame()))
        + "\n\n"
        + runtime_text
        + "\n\n## Inference\n\n"
        "- The runtime logs resolve the prefill TP discrepancy in favor of TP=8 with attention-CP=8. The shared 32×H200 backend allocation is not a per-ID hardware assignment.\n\n"
        "## Unknown\n\n"
        "- The 40-GPU resource-snapshot count includes non-backend allocation; it is not the benchmark backend GPU total. Per-request GPU affinity is not exposed.\n",
    )
    _write(
        reports / "02_kv_cache_runtime.md",
        "# 02. KV-cache runtime\n\n"
        "## Evidence\n\n"
        + _table(tables.get("kv_cache_runtime", pd.DataFrame()))
        + "\n\n"
        + _table(cache)
        + "\n\n## Inference\n\n"
        "- Server logs directly show FP8 allocation records and disabled CPU/KV offload paths. Their rank-scoped GiB values must not be summed or multiplied into an unsupported cluster-wide physical capacity.\n\n"
        "## Unknown\n\n"
        "- A profile `usage_prompt_cache_read_tokens` counter is retained as observed evidence, but it is not promoted to a logical-prompt ratio when its scope is incompatible or unverified.\n"
        "- Do not treat source theoretical prefix reuse as actual server cache residency.\n",
    )
    _write(
        reports / "03_mtp_runtime.md",
        "# 03. MTP runtime\n\n"
        "## Evidence\n\n"
        "- Configured EAGLE MTP: three speculative steps, top-k 1, four draft tokens, and simulated acceptance length 2.99.\n\n"
        + _table(mtp)
        + "\n\n"
        + runtime_text
        + "\n\n## Inference\n\n"
        "- Weighted decode TPS is an observed replay metric under the configured MTP behavior; it is not a non-MTP single-model decode-TPS estimate.\n\n"
        "## Unknown\n\n"
        "- Request-profile rows may omit accepted/drafted token counters even when server logs contain aggregate/runtime acceptance messages.\n",
    )
    _write(
        reports / "04_concurrency_results.md",
        "# 04. c8 / c12 / c16 concurrency results\n\n"
        "## Evidence\n\n"
        + _table(_select(concurrency, [
            "concurrency", "profiled_request_count", "root_id_count", "input_sequence_length_total",
            "output_tokens_total", "wall_span_s", "ttft_mean_ms", "ttft_median_ms", "ttft_p90_ms",
            "weighted_decode_tps", "wall_output_tps", "itl_sample_count", "error_count_all_rows",
            "cancellation_count_all_rows",
        ]))
        + "\n\n### Source-root vs source-subagent origin\n\n"
        + _table(tables.get("root_subagent_summary", pd.DataFrame()))
        + "\n\n## Inference\n\n"
        "- Cross-concurrency changes are interpreted only after observed source-ID coverage and source-key matching; fixed-duration replay can change workload coverage.\n\n"
        "## Unknown\n\n"
        "- No individual conversation ID is assigned a fixed GPU, GPU count, or hardware affinity.\n",
    )
    _write(
        reports / "05_requested_ids_analysis.md",
        "# 05. Requested ID analysis\n\n"
        "## Evidence\n\n"
        + _table(resolution)
        + "\n\n"
        + _requested_tables_text(tables)
        + "\n\n## Inference\n\n"
        "- Prefixes are only used as canonical IDs after strict `startswith()` resolution is unique.\n\n"
        "## Unknown\n\n"
        "- A not-observed ID is not evidence that it was never eligible for replay; run duration, warmup, recycling, and routing affect coverage.\n",
    )
    _write(
        reports / "06_cross_concurrency.md",
        "# 06. Cross-concurrency matching\n\n"
        "## Evidence\n\n"
        + _table(tables.get("cross_concurrency_match_summary", pd.DataFrame()))
        + "\n\n## Inference\n\n"
        "- Pair rows collapse repeated records to a source-key/concurrency median before ratios; raw request rows are not treated as independent replicates.\n\n"
        "## Unknown\n\n"
        "- Identical source keys do not ensure identical output lengths under a speculative-decoding replay. Strict decode subsets require the observed output length to agree.\n",
    )
    _write(
        reports / "07_hisparse_c8_vs_gpu_resident_c8.md",
        "# 07. HiSparse c8 vs GPU-resident MTP c8\n\n"
        "## Evidence\n\n"
        + _table(comparison)
        + "\n\n"
        + _table(tables.get("exact_match_c8_summary", pd.DataFrame()))
        + "\n\n## Inference\n\n"
        "- Every ratio is an **observed system-level difference**, not a causal HiSparse effect: GPU count, P/D topology, KV dtype/residency, MTP, routing, and software can all differ.\n\n"
        "## Unknown\n\n"
        "- The available evidence cannot isolate the contribution of any one of those changes.\n",
    )
    _write(
        reports / "08_local_2gpu_contextual_reference.md",
        "# 08. User-reported 2-GPU contextual reference\n\n"
        "## Evidence\n\n"
        + _table(tables.get("local_2gpu_user_reported_reference", pd.DataFrame()))
        + "\n\n## Inference\n\n"
        "- These two rows are a provenance-labelled user-reported aggregate reference, useful for later review but not request-level evidence.\n\n"
        "## Unknown\n\n"
        "- No direct apples-to-apples conclusion is possible against 32×H200, 2P2D, MTP-enabled public replay without local raw logs and configuration evidence.\n",
    )
    _write(
        reports / "09_validation.md",
        "# 09. Aggregate validation\n\n"
        "## Evidence\n\n"
        + _table(validation)
        + "\n\n"
        + _table(_select(tables.get("aggregate_validation", pd.DataFrame()), [
            "concurrency", "metric", "raw_value", "published_value", "validation_status", "validation_note",
        ]))
        + "\n\n## Inference\n\n"
        "- A pass is limited to the documented filtering, units, percentile convention, and available aggregate metric path.\n\n"
        "## Unknown\n\n"
        "- A not-comparable aggregate field is not a validation pass.\n",
    )
    _write(
        reports / "10_limitations.md",
        "# 10. Limitations\n\n"
        "## Evidence\n\n"
        "- The workload’s source Claude labels are preserved only as source-workload provenance. The target replay model is GLM-5.2 FP8.\n"
        "- Source `api_time` is not an H200 latency measurement.\n"
        "- Raw profile records can repeat a source key; a shared H200 system serves all requests.\n\n"
        "## Inference\n\n"
        "- c8/c12/c16 coverage differences can bias unpaired averages.\n\n"
        "## Unknown\n\n"
        "- Per-ID GPU utilisation, exact GPU allocation, and physical cache residency cannot be inferred from a conversation ID.\n"
        "- MTP acceptance and KV allocation require actual runtime counters/log scope; absent metrics remain Unknown.\n",
    )
    _write_korean_summary(reports / "results_summary_ko.md", tables, recipe, runtime)


def _build_handoff(
    handoff: Path,
    tables: dict[str, pd.DataFrame],
    recipe: dict[str, Any],
    runtime: dict[str, Any],
) -> None:
    concurrency = tables.get("concurrency_summary", pd.DataFrame())
    ids = tables.get("requested_id_resolution", pd.DataFrame())
    comparison = tables.get("h200_c8_hisparse_vs_gpu_resident", pd.DataFrame())
    artifacts = tables.get("artifact_inventory", pd.DataFrame())
    _write(
        handoff / "codex_to_chatgpt.md",
        "# Codex → ChatGPT handoff: H200 GPU-resident MTP\n\n"
        "## Git / Run Provenance\n\n"
        f"- Analysis repository: `https://github.com/sskim-ai/InferenceX_analysis`\n"
        f"- Analysis branch: `analysis/h200-gpu-resident-mtp`\n"
        f"- Analysis starting commit: `{ANALYSIS_START_COMMIT}`\n"
        f"- InferenceX Actions run: `{_recipe_value(recipe, ['actions_run', 'id'])}`\n"
        f"- Canonical run SHA: `{_recipe_value(recipe, ['actions_run', 'head_sha'])}`\n"
        f"- PR: `#{_recipe_value(recipe, ['pull_request', 'number'])}`\n\n"
        "## Downloaded Artifacts\n\n"
        + _artifact_handoff_table(artifacts)
        + "\n\n- **Evidence:** each selected archive has `expired=false`, local SHA-256 matching the GitHub digest, and a passing ZIP CRC check. Full local paths/checksums are in `../manifests/artifact_inventory.csv`.\n\n"
        "## Confirmed Architecture\n\n"
        + _table(tables.get("runtime_configuration", pd.DataFrame()))
        + "\n\n## Runtime KV Findings\n\n"
        + _handoff_kv_highlights()
        + "\n\n"
        + _table(tables.get("kv_cache_runtime", pd.DataFrame()))
        + "\n\n## MTP Findings\n\n"
        + _table(tables.get("mtp_metrics", pd.DataFrame()))
        + "\n\n## Routing / Worker Distribution\n\n"
        "- **Evidence:** frontend logs select both prefill workers and both decode workers across decode DP ranks.\n"
        "- **Unknown:** profile `worker_id` is an observed request field, not proof of a fixed backend worker or GPU affinity. See `../processed/worker_distribution.csv`.\n"
        + "\n\n## c8/c12/c16 Key Metrics\n\n"
        + _table(_select(concurrency, [
            "concurrency", "profiled_request_count", "ttft_mean_ms", "ttft_median_ms", "ttft_p90_ms",
            "itl_weighted_ms", "weighted_decode_tps", "wall_output_tps", "output_tokens_total",
        ]))
        + "\n\n## Requested ID Resolution\n\n"
        + _table(ids)
        + "\n\n## ID01 Key Metrics\n\n"
        + _requested_metrics_table(tables.get("id01_by_concurrency", pd.DataFrame()))
        + "\n\n## ID02 Key Metrics\n\n"
        + _requested_metrics_table(tables.get("id02_by_concurrency", pd.DataFrame()))
        + "\n\n- **Scope warning:** full per-ID CSVs retain `usage_prompt_cache_read_tokens` as an observed raw counter, but neither it nor `cache_load_tps` is a validated logical-prompt or physical-KV metric.\n"
        + "\n\n## HiSparse c8 vs GPU-resident c8\n\n"
        + _table(comparison)
        + "\n\n## User 2GPU Contextual Comparison\n\n"
        + _table(tables.get("local_2gpu_user_reported_reference", pd.DataFrame()))
        + "\n\n## Evidence\n\n"
        "- Public artifacts, their checksums, aggregate validation, and recipe/runtime-log findings are versioned in this study.\n\n"
        "## Inference\n\n"
        "- GPU-resident versus HiSparse c8 findings are observed system-level ratios, not isolated causal effects.\n\n"
        "## Unknown\n\n"
        "- Do not infer per-ID GPU attribution, physical KV allocation beyond log scope, or request-level local-server behavior without private raw evidence.\n\n"
        "## Important Caveats\n\n"
        "- Source workload model labels are not target-model labels.\n"
        "- MTP changes output behavior; strict decode ratios require matching output lengths.\n"
        "- Cache metrics have explicit scope labels; do not conflate a frontend/cache counter with physical KV residency.\n"
        "- Server logs show dynamic routing across two prefill and two decode workers. Request `worker_id` is not demonstrated GPU or backend-worker affinity; see `../processed/worker_distribution.csv`.\n\n"
        "## Files ChatGPT Should Read Next\n\n"
        "1. `studies/h200_gpu_resident_mtp/reports/results_summary_ko.md`\n"
        "2. `studies/h200_gpu_resident_mtp/processed/concurrency_summary.csv`\n"
        "3. `studies/h200_gpu_resident_mtp/processed/schema_mapping.csv`\n"
        "4. `studies/h200_gpu_resident_mtp/processed/profile_field_inventory.csv`\n"
        "5. `studies/h200_gpu_resident_mtp/processed/profile_metric_inventory.csv`\n"
        "6. `studies/h200_gpu_resident_mtp/processed/requested_id_resolution.csv`\n"
        "7. `studies/h200_gpu_resident_mtp/processed/h200_c8_hisparse_vs_gpu_resident.csv`\n"
        "8. `studies/h200_gpu_resident_mtp/processed/exact_match_c8_summary.csv`\n"
        "9. `studies/h200_gpu_resident_mtp/processed/kv_cache_runtime.csv`\n"
        "10. `studies/h200_gpu_resident_mtp/processed/worker_distribution.csv`\n"
        "11. `studies/h200_gpu_resident_mtp/manifests/provenance.json`\n"
        "12. `studies/h200_gpu_resident_mtp/handoff/local_server_evidence_needed.md`\n",
    )
    resolved_ids = [
        str(value)
        for value in ids.get("resolved_full_source_trace_id", pd.Series(dtype="string")).dropna()
        if str(value)
    ]
    checklist = "# Preliminary local-server evidence needed\n\n"
    checklist += "This is a checklist for the next analysis phase, not the final internal-GPT prompt.\n\n"
    checklist += "## Configuration and topology\n\n"
    checklist += "- Exact target checkpoint, quantization/precision, GPU SKU/count, TP/DP/PP/EP, and aggregated topology evidence.\n"
    checklist += "- MTP/speculative algorithm, steps, draft tokens, acceptance configuration, and max model/batch limits.\n"
    checklist += "- KV dtype, page/block size, physical GPU KV slots/GiB, prefix-cache configuration, offload policy, and max running requests.\n\n"
    checklist += "## Request-level evidence\n\n"
    checklist += "- source_trace_id, source_outer_idx, source_inner_idx, source_conversation_path, turn_index, timestamps, worker/routing ID.\n"
    checklist += "- input tokens with documented semantics; cache-read/load/store counters with scope; output tokens; TTFT; ITL/decode-duration definition; E2E; cancellation/error and context-overflow fields.\n\n"
    checklist += "## IDs to check locally\n\n"
    if resolved_ids:
        checklist += "- Confirm whether each resolved public ID appears in local data: " + ", ".join(f"`{v}`" for v in resolved_ids) + ".\n"
    else:
        checklist += "- Requested public IDs were not yet resolved in available public data.\n"
    checklist += "\n## Why these fields matter\n\n"
    checklist += "- Public MTP replay exposes a profile cache counter whose ratio to usage prompt tokens can exceed one, so exact local metric scope is essential before comparison.\n"
    checklist += "- Physical KV allocation and MTP acceptance require startup/runtime evidence rather than architecture assumptions.\n"
    _write(handoff / "local_server_evidence_needed.md", checklist)


def _write_korean_summary(
    path: Path, tables: dict[str, pd.DataFrame], recipe: dict[str, Any], runtime: dict[str, Any]
) -> None:
    concurrency = tables.get("concurrency_summary", pd.DataFrame())
    ids = tables.get("requested_id_resolution", pd.DataFrame())
    comparison = tables.get("h200_c8_hisparse_vs_gpu_resident", pd.DataFrame())
    text = "# 분석 대상\n\n"
    text += f"- Public InferenceX run `{_recipe_value(recipe, ['actions_run', 'id'])}`의 GLM-5.2 FP8 H200 replay를 분석했다. source Claude label은 workload provenance이며 target model이 아니다.\n\n"
    text += "# H200 환경 검증\n\n"
    text += _table(tables.get("runtime_configuration", pd.DataFrame())) + "\n\n"
    text += "# 데이터와 ID 연결 방식\n\n"
    text += "- **Evidence:** profile metadata의 `source_trace_id`와 `source_outer_idx`를 source table에 연결했다. prefix ID는 strict `startswith()` 후보가 하나일 때만 full ID로 확정했다.\n"
    text += "- **Unknown:** conversation ID는 GPU affinity나 ID별 GPU 수를 뜻하지 않는다.\n\n"
    text += "# ID coverage\n\n" + _table(ids) + "\n\n"
    text += "# ID별 성능 핵심 결과\n\n" + _requested_tables_text(tables) + "\n\n"
    text += "# Concurrency c8 / c12 / c16 비교\n\n"
    text += "- 이 study의 public run은 c8/c12/c16이며, 고정 시간 replay이므로 coverage를 동반해 비교한다.\n"
    text += _table(_select(concurrency, [
        "concurrency", "profiled_request_count", "ttft_median_ms", "weighted_decode_tps", "wall_output_tps",
    ])) + "\n\n"
    text += "# Root agent와 subagent 비교\n\n"
    text += _table(tables.get("root_subagent_summary", pd.DataFrame())) + "\n\n"
    text += "# Context 및 theoretical cache reuse 영향\n\n"
    text += "- **Evidence:** profile cache counter와 aggregate frontend-cache metrics는 별도 scope로 보존했다.\n"
    text += "- **Unknown:** theoretical source prefix reuse는 actual H200 cache residency/hit와 동일하지 않다.\n\n"
    text += _table(tables.get("context_cache_relationship", pd.DataFrame())) + "\n\n"
    text += "# 가장 부담이 큰 trace IDs\n\n" + _table(_select(tables.get("top_ids_by_workload_or_latency", pd.DataFrame()).head(20), [
        "concurrency", "root_trace_id", "profiled_request_count", "input_sequence_length_total", "output_tokens_total", "ttft_median_ms",
    ])) + "\n\n"
    text += "# Aggregate 결과 재현 검증\n\n" + _table(tables.get("validation_summary", pd.DataFrame())) + "\n\n"
    text += "# 확인된 사실\n\n"
    text += "- **Evidence:** raw profile rows와 published aggregate의 request count, tokens, TTFT, ITL, E2E, throughput은 validation table 범위에서 대조된다.\n\n"
    text += "# 추론\n\n"
    text += "- **Inference (high confidence):** runtime log는 FP8 KV allocation record와 HiSparse/OFFload 비활성화를 직접 보인다. 다만 rank-scoped GiB를 cluster 전체 physical capacity로 합산하지 않는다.\n\n"
    text += "# 확인할 수 없는 것\n\n"
    text += "- **Unknown:** HiSparse 단독 효과, ID별 GPU attribution, 사내 2-GPU의 request-level behavior, and unsupported cache/MTP counter semantics.\n\n"
    text += "# 데이터 한계\n\n"
    text += "- warmup/recycling, shared system, repeated source IDs, MTP output variance, and cache metric scope prevent naïve request-independence or apples-to-apples conclusions.\n\n"
    text += "# 재현 방법\n\n"
    text += "```sh\nmake mtp-analyze\nmake mtp-report\n```\n\n"
    text += "# 기존 HiSparse c8와의 observed difference\n\n" + _table(comparison) + "\n"
    _write(path, text)


def _write_kv_runtime(processed: Path, recipe: dict[str, Any], runtime: dict[str, Any]) -> None:
    rows = [
        {
            "concurrency": "configured",
            "component": "configured_decode",
            "field": "kv_cache_dtype",
            "value": "fp8_e4m3",
            "scope": "configured recipe",
            "classification": "Evidence",
        },
        {
            "concurrency": "configured",
            "component": "configured_decode",
            "field": "kv_offloading",
            "value": "none",
            "scope": "configured matrix",
            "classification": "Evidence",
        },
        {
            "concurrency": "configured",
            "component": "configured_decode",
            "field": "page_size",
            "value": "64",
            "scope": "configured recipe",
            "classification": "Evidence",
        },
        {
            "concurrency": "configured",
            "component": "configured_decode",
            "field": "max_running_requests",
            "value": "200",
            "scope": "configured recipe",
            "classification": "Evidence",
        },
    ]
    for item in _runtime_items(runtime):
        subject = str(item.get("subject") or item.get("field") or "runtime_log")
        value = item.get("value")
        scope = item.get("scope") or item.get("details") or item.get("source") or "server log"
        references = item.get("references")
        concurrencies = sorted(
            {
                str(reference.get("concurrency"))
                for reference in references
                if isinstance(reference, dict) and reference.get("concurrency") is not None
            }
        ) if isinstance(references, list) else []
        source = "; ".join(
            f"c{reference.get('concurrency')}:{reference.get('member')}:{reference.get('lines', reference.get('json_path', ''))}"
            for reference in references[:3]
            if isinstance(reference, dict)
        ) if isinstance(references, list) else "server log"
        flattened = value.items() if isinstance(value, dict) else [(subject, value)]
        for key, item_value in flattened:
            rows.append(
                {
                    "concurrency": ";".join(concurrencies) if concurrencies else "runtime",
                    "component": subject,
                    "field": key,
                    "value": json.dumps(item_value, ensure_ascii=False, sort_keys=True)
                    if isinstance(item_value, (dict, list))
                    else item_value,
                    "scope": scope,
                    "source": source,
                    "classification": item.get("classification") or "Evidence",
                }
            )
    if not runtime:
        rows.append(
            {
                "component": "runtime_log",
                "concurrency": "runtime",
                "field": "physical_kv_allocation",
                "value": None,
                "scope": "server logs not yet parsed",
                "source": None,
                "classification": "Unknown",
            }
        )
    pd.DataFrame(rows).to_csv(processed / "kv_cache_runtime.csv", index=False)


def _augment_mtp_metrics(processed: Path, frame: pd.DataFrame, runtime: dict[str, Any]) -> None:
    if frame.empty:
        return
    result = frame.copy()
    finding = next(
        (item for item in _runtime_items(runtime) if item.get("subject") == "mtp_launch_and_runtime_behavior"),
        None,
    )
    if not finding or not isinstance(finding.get("value"), dict):
        result.to_csv(processed / "mtp_metrics.csv", index=False)
        return
    value = finding["value"]
    for source, target in (
        ("runtime_decode_batch_sample_accept_length_range", "runtime_sample_acceptance_length_range"),
        ("runtime_decode_batch_sample_accept_rate_range", "runtime_sample_acceptance_rate_range"),
        ("simulate_acceptance_length", "runtime_configured_simulated_acceptance_length"),
        ("simulate_acceptance_method", "runtime_configured_acceptance_method"),
        ("simulate_acceptance_token_mode", "runtime_configured_acceptance_token_mode"),
    ):
        result[target] = json.dumps(value[source]) if isinstance(value.get(source), list) else value.get(source)
    result["runtime_log_status"] = "sampled_decode_batch_evidence_not_request_weighted"
    result["runtime_evidence_classification"] = "Evidence"
    result.to_csv(processed / "mtp_metrics.csv", index=False)


def _augment_runtime_configuration(processed: Path, frame: pd.DataFrame, runtime: dict[str, Any]) -> None:
    if frame.empty:
        return
    result = frame.copy()
    if "field" not in result:
        return
    selected: dict[str, tuple[str, str]] = {
        "backend_hardware_and_pd_topology.backend_gpu_count": ("runtime_backend_gpu_count", "backend GPU count"),
        "backend_hardware_and_pd_topology.prefill_workers": ("runtime_prefill_workers", "server log"),
        "backend_hardware_and_pd_topology.decode_workers": ("runtime_decode_workers", "server log"),
        "effective_prefill_server_flags.tp_size": ("runtime_prefill_tp_size", "server log resolves matrix/recipe discrepancy"),
        "effective_prefill_server_flags.attn_cp_size": ("runtime_prefill_attn_cp_size", "server log"),
        "effective_decode_server_flags_and_kv_residency_controls.enable_hisparse": ("runtime_enable_hisparse", "server log"),
        "effective_decode_server_flags_and_kv_residency_controls.cpu_offload_gb": ("runtime_cpu_offload_gb", "server log"),
        "effective_decode_server_flags_and_kv_residency_controls.disaggregation_decode_enable_offload_kvcache": ("runtime_decode_kv_offload", "server log"),
        "effective_decode_server_flags_and_kv_residency_controls.kv_cache_dtype": ("runtime_decode_kv_dtype", "server log"),
    }
    additions = []
    for item in _runtime_items(runtime):
        subject = str(item.get("subject"))
        value = item.get("value")
        if not isinstance(value, dict):
            continue
        for key, item_value in value.items():
            requested = selected.get(f"{subject}.{key}")
            if not requested:
                continue
            field, source = requested
            additions.append(
                {
                    "field": field,
                    "value": item_value,
                    "classification": item.get("classification", "Evidence"),
                    "source": source,
                }
            )
    if additions:
        result = pd.concat([result, pd.DataFrame(additions)], ignore_index=True, sort=False)
    result.drop_duplicates(subset=["field"], keep="last").to_csv(
        processed / "runtime_configuration.csv", index=False
    )


def _build_figures(figures: Path, tables: dict[str, pd.DataFrame]) -> None:
    summary = tables.get("concurrency_summary", pd.DataFrame())
    _line_plot(summary, "ttft_median_ms", "TTFT median (ms)", figures / "ttft_vs_concurrency.png")
    _line_plot(summary, "weighted_decode_tps", "Weighted decode TPS (tok/s)", figures / "weighted_decode_tps_vs_concurrency.png")
    _line_plot(summary, "wall_output_tps", "Wall output TPS (tok/s)", figures / "wall_output_tps_vs_concurrency.png")
    for label in ("id01", "id02"):
        frame = tables.get(f"{label}_by_concurrency", pd.DataFrame())
        _line_plot(frame, "ttft_median_ms", f"{label.upper()} TTFT median (ms)", figures / f"{label}_ttft.png")
        _line_plot(frame, "weighted_decode_tps", f"{label.upper()} weighted decode TPS (tok/s)", figures / f"{label}_tps.png")
    cache = tables.get("cache_metrics", pd.DataFrame())
    _line_plot(cache, "server_frontend_cache_hit_rate", "Server frontend cache hit rate", figures / "cache_read_ratio.png")
    mtp = tables.get("mtp_metrics", pd.DataFrame())
    _mtp_acceptance_plot(mtp, figures / "mtp_acceptance_metric.png")
    _branch_plot(tables.get("root_subagent_summary", pd.DataFrame()), "ttft_median_ms", "TTFT median (ms)", figures / "root_vs_subagent_ttft.png")
    _branch_plot(tables.get("root_subagent_summary", pd.DataFrame()), "weighted_decode_tps", "Weighted decode TPS (tok/s)", figures / "root_vs_subagent_tps.png")
    comparison = tables.get("h200_c8_hisparse_vs_gpu_resident", pd.DataFrame())
    _comparison_plot(comparison, figures / "hisparse_c8_vs_gpu_resident_mtp_c8.png")


def _line_plot(frame: pd.DataFrame, field: str, ylabel: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    if not frame.empty and {"concurrency", field}.issubset(frame.columns):
        data = frame[["concurrency", field]].dropna().sort_values("concurrency")
        if not data.empty:
            ax.plot(data["concurrency"], data[field], marker="o")
            for _, item in data.iterrows():
                ax.annotate(f"{item[field]:.3g}", (item["concurrency"], item[field]), xytext=(0, 7), textcoords="offset points", ha="center")
        else:
            ax.text(0.5, 0.5, "Unknown / no observed sample", ha="center", va="center", transform=ax.transAxes)
    else:
        ax.text(0.5, 0.5, "Unknown / no observed sample", ha="center", va="center", transform=ax.transAxes)
    ax.set_xlabel("Requested concurrency")
    ax.set_ylabel(ylabel)
    ax.set_title(ylabel + " by concurrency")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _comparison_plot(frame: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    data = frame.loc[frame.get("comparison_scope", pd.Series(dtype="string")) == "run_level_unpaired_observed_system_difference"].copy()
    data = data.loc[data.get("metric", pd.Series(dtype="string")).isin(["weighted_decode_tps", "wall_output_tps"])]
    if not data.empty:
        labels = data["metric"].tolist()
        x = range(len(labels))
        ax.bar([i - 0.18 for i in x], pd.to_numeric(data["hisparse_c8_value"], errors="coerce"), width=0.36, label="HiSparse c8")
        ax.bar([i + 0.18 for i in x], pd.to_numeric(data["gpu_resident_mtp_c8_value"], errors="coerce"), width=0.36, label="GPU-resident MTP c8")
        ax.set_xticks(list(x), labels)
        ax.legend()
    else:
        ax.text(0.5, 0.5, "Unknown / no comparable c8 data", ha="center", va="center", transform=ax.transAxes)
    ax.set_ylabel("tok/s")
    ax.set_title("Observed system-level c8 comparison (not causal)")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _mtp_acceptance_plot(frame: pd.DataFrame, path: Path) -> None:
    """Plot server-log MTP samples without relabelling them as request averages."""

    fig, ax = plt.subplots(figsize=(7, 4.5))
    rows: list[tuple[float, float, float, float]] = []
    if not frame.empty and {"concurrency", "runtime_sample_acceptance_length_range"}.issubset(frame.columns):
        for _, item in frame.iterrows():
            value = item.get("runtime_sample_acceptance_length_range")
            try:
                parsed = json.loads(value) if isinstance(value, str) else value
                low, high = float(parsed[0]), float(parsed[1])
                concurrency = float(item["concurrency"])
            except (IndexError, TypeError, ValueError, json.JSONDecodeError):
                continue
            rows.append((concurrency, low, high, (low + high) / 2))
    if rows:
        rows.sort()
        x = [row[0] for row in rows]
        y = [row[3] for row in rows]
        lower = [row[3] - row[1] for row in rows]
        upper = [row[2] - row[3] for row in rows]
        ax.errorbar(x, y, yerr=[lower, upper], fmt="o-", capsize=4)
        for concurrency, low, high, midpoint in rows:
            ax.annotate(
                f"{low:.2f}–{high:.2f}",
                (concurrency, midpoint),
                xytext=(0, 7),
                textcoords="offset points",
                ha="center",
            )
    else:
        ax.text(0.5, 0.5, "Unknown / no server-log MTP sample", ha="center", va="center", transform=ax.transAxes)
    ax.set_xlabel("Requested concurrency")
    ax.set_ylabel("Sampled acceptance length")
    ax.set_title("MTP decode-batch acceptance samples (not request-weighted)")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _branch_plot(frame: pd.DataFrame, field: str, ylabel: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    if not frame.empty and {"concurrency", "source_branch_type", field}.issubset(frame.columns):
        data = frame[["concurrency", "source_branch_type", field]].dropna()
        if not data.empty:
            for branch, group in data.groupby("source_branch_type"):
                group = group.sort_values("concurrency")
                ax.plot(group["concurrency"], group[field], marker="o", label=str(branch))
            ax.legend(title="source branch origin")
        else:
            ax.text(0.5, 0.5, "Unknown / no observed sample", ha="center", va="center", transform=ax.transAxes)
    else:
        ax.text(0.5, 0.5, "Unknown / no observed sample", ha="center", va="center", transform=ax.transAxes)
    ax.set_xlabel("Requested concurrency")
    ax.set_ylabel(ylabel)
    ax.set_title("Source-root vs source-subagent origin")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _artifact_handoff_table(frame: pd.DataFrame) -> str:
    """Render the nine requested artifact records, not merely a manifest link."""

    if frame.empty:
        return "- No artifact inventory rows available."
    selected = frame.loc[
        frame.get("category", pd.Series(dtype="string")).isin(
            ["raw_result", "aggregate", "server_logs"]
        )
    ].copy()
    return _table(
        _select(
            selected.sort_values(["concurrency", "category"]),
            [
                "concurrency",
                "category",
                "artifact_id",
                "artifact_name",
                "github_digest",
                "download_status",
                "zip_validation",
                "expired",
            ],
        )
    )


def _handoff_kv_highlights() -> str:
    """Keep the scope-critical runtime KV allocations above long evidence tables."""

    return _table(
        pd.DataFrame(
            [
                {
                    "component": "prefill runtime",
                    "observed allocation": "logical token limit 1,048,576; scheduler 16,384 blocks × page 64; 6.93–7.70 GiB primary + 0.77 GiB secondary allocation records",
                    "scope": "individual logged ATTN_CP/TP rank in one 8-GPU prefill worker; logical pool is per worker, not a 16-GPU/global total",
                    "classification": "Evidence",
                },
                {
                    "component": "decode runtime",
                    "observed allocation": "runtime-profiled token value 218,560; 12.51 GiB primary + 0.16 GiB secondary allocation records; page 64 / FP8 E4M3",
                    "scope": "individual logged DP/TP rank in one decode worker; do not sum or multiply into cluster physical capacity",
                    "classification": "Evidence",
                },
            ]
        )
    )


def _requested_metrics_table(frame: pd.DataFrame) -> str:
    return _table(
        _select(
            frame,
            [
                "root_trace_id",
                "concurrency",
                "all_request_count",
                "warmup_count",
                "profiled_request_count",
                "output_tokens_total",
                "ttft_mean_ms",
                "ttft_median_ms",
                "ttft_p90_ms",
                "itl_sample_count",
                "weighted_decode_tps",
                "e2e_median_ms",
                "wall_span_s",
                "wall_output_tps",
                "error_count",
                "cancellation_count",
                "sample_quality",
            ],
        )
    )


def _requested_tables_text(tables: dict[str, pd.DataFrame]) -> str:
    chunks = []
    for label in ("id01", "id02", "id03", "id04", "id05"):
        frame = tables.get(f"{label}_by_concurrency", pd.DataFrame())
        if frame.empty:
            chunks.append(f"### {label.upper()}\n\n- **Unknown:** no public profiling rows or no unique resolution.\n")
        else:
            chunks.append(
                f"### {label.upper()}\n\n"
                + _table(_select(frame, [
                    "root_trace_id", "concurrency", "profiled_request_count", "ttft_median_ms", "ttft_p90_ms",
                    "weighted_decode_tps", "wall_output_tps", "output_tokens_total", "error_count", "cancellation_count",
                ]))
            )
    chunks.append(
        "- **Scope warning:** raw `usage_prompt_cache_read_tokens` is retained in full per-ID CSVs, "
        "but it is not a validated logical-cache ratio, physical KV-load metric, or `cache_load_tps` basis."
    )
    return "\n\n".join(chunks)


def _runtime_evidence_text(runtime: dict[str, Any]) -> str:
    if not runtime:
        return "- **Unknown:** runtime-log evidence file was not available when this report was built."
    rows = []
    for item in _runtime_items(runtime):
        subject = item.get("subject") or item.get("field") or "runtime_log"
        value = item.get("value")
        rows.append(f"- **{item.get('classification', 'Evidence')}:** `{subject}` = `{value}` ({item.get('source', 'server log')}).")
    return "\n".join(rows) if rows else "- **Unknown:** no structured runtime findings were parsed."


def _runtime_items(runtime: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("evidence", "findings", "runtime_findings", "items"):
        value = runtime.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _recipe_value(payload: dict[str, Any], keys: list[str]) -> Any | None:
    value: Any = payload
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path) if path.exists() else pd.DataFrame()
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _select(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return frame[[column for column in columns if column in frame]].copy() if not frame.empty else frame


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "- No comparable rows available."
    view = frame.copy()
    if len(view) > 30:
        view = view.head(30)
    columns = list(view.columns)
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    rows = []
    for values in view.itertuples(index=False, name=None):
        cells = [_cell(value) for value in values]
        rows.append("| " + " | ".join(cells) + " |")
    suffix = "\n\n- Table is truncated to 30 rows." if len(frame) > len(view) else ""
    return "\n".join([header, divider, *rows]) + suffix


def _cell(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _write(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
