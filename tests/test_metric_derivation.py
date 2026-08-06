import json
import math

import pandas as pd

from h200_agentx_analysis.metrics import add_derived_metrics
from h200_agentx_analysis.validation import (
    load_published_aggregates,
    recompute_raw_aggregates,
    validate_aggregates,
)


def test_metric_derivations_preserve_units_and_guard_invalid_denominators() -> None:
    frame = pd.DataFrame(
        [
            {
                "input_tokens": 100,
                "output_tokens": 11,
                "ttft_ms": 100.0,
                "e2e_ms": 600.0,
                "itl_ms": 50.0,
            },
            {"input_tokens": 1, "output_tokens": 1, "ttft_ms": 50.0, "e2e_ms": 40.0, "itl_ms": 0.0},
            {
                "input_tokens": 1,
                "output_tokens": 0,
                "ttft_ms": None,
                "e2e_ms": -1.0,
                "itl_ms": None,
            },
        ]
    )
    result = add_derived_metrics(frame)
    assert result.loc[0, "ttft_s"] == 0.1
    assert result.loc[0, "post_ttft_s"] == 0.5
    assert result.loc[0, "observed_itl_implied_tps"] == 20.0
    assert result.loc[0, "post_ttft_tps"] == 20.0
    assert result.loc[0, "e2e_output_tps"] == 11 / 0.6
    assert result.loc[0, "input_tokens_per_observed_ttft_s"] == 1000.0
    assert result.loc[1, "ttft_exceeds_e2e"]
    assert math.isnan(result.loc[1, "observed_itl_implied_tps"])
    assert math.isnan(result.loc[1, "post_ttft_tps"])
    assert math.isnan(result.loc[2, "e2e_output_tps"])


def test_aggregate_validation_includes_per_gpu_and_metadata_rows() -> None:
    requests = pd.DataFrame(
        [
            {
                "concurrency": 1,
                "input_tokens": 100,
                "output_tokens": 20,
                "ttft_ms": 10.0,
                "itl_ms": 2.0,
                "e2e_ms": 50.0,
                "request_start_ns": 0,
                "request_end_ns": 1_000_000_000,
                "target_gpu_count": 2,
                "target_model": "GLM-5.2 FP8",
                "target_precision": "FP8",
                "framework": "Dynamo + SGLang",
            }
        ]
    )
    raw = recompute_raw_aggregates(requests)
    assert raw.loc[0, "per_gpu_total_throughput_tps"] == 60.0
    published = pd.DataFrame(
        [
            {
                "concurrency": 1,
                "source_file_path": "aggregate.json",
                **{
                    f"published_{field}": raw.loc[0, field]
                    for field in raw.columns
                    if field != "concurrency"
                },
            }
        ]
    )
    result = validate_aggregates(raw, published)
    status = result.set_index("metric")["validation_status"]
    assert status["per_gpu_total_throughput_tps"] == "pass"
    assert status["target_model"] == "pass"
    assert status["precision"] == "pass"
    assert status["framework"] == "pass"


def test_aggregate_validation_skips_multiple_published_json_candidates() -> None:
    raw = pd.DataFrame(
        [
            {
                "concurrency": 1,
                "successful_profiled_request_count": 7,
                "total_input_tokens": 10,
            }
        ]
    )
    published = pd.DataFrame(
        [
            {
                "concurrency": 1,
                "source_file_path": "bmk_agentic_conc1/result.json",
                "artifact_match_status": "unambiguous",
                "published_successful_profiled_request_count": 7,
            },
            {
                "concurrency": 1,
                "source_file_path": "results_bmk/result.json",
                "artifact_match_status": "unambiguous",
                "published_successful_profiled_request_count": 7,
            },
        ]
    )
    result = validate_aggregates(raw, published)
    assert set(result["validation_status"]) == {"ambiguous_published_candidates"}
    assert set(result["published_candidate_file_count"]) == {2}
    assert result["published_value"].isna().all()


def test_published_token_total_derivation_and_glm_alias_are_auditable(tmp_path) -> None:
    aggregate = tmp_path / "aggregate.json"
    aggregate.write_text(
        json.dumps(
            {
                "conc": 1,
                "model": "zai-org/GLM-5.2-FP8",
                "num_prefill_gpu": 8,
                "num_decode_gpu": 8,
                "num_requests_successful": 10,
                "request_metrics": {
                    "tokens": {
                        "input": {"mean": 12.30005},
                        "output_actual": {"mean": 4.20004},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    published = load_published_aggregates(
        [aggregate],
        artifact_context={
            str(aggregate): {
                "artifact_match_status": "unambiguous",
                "artifact_id": "fixture",
                "artifact_name": "bmk_agentic_fixture",
                "concurrency": 1,
            }
        },
    )
    assert abs(published.loc[0, "published_total_input_tokens"] - 123.0005) < 1e-9
    assert abs(published.loc[0, "published_total_output_tokens"] - 42.0004) < 1e-9
    assert "input.mean" in published.loc[0, "published_total_input_tokens_derivation"]
    assert published.loc[0, "published_gpu_count"] == 16.0
    raw = pd.DataFrame(
        [
            {
                "concurrency": 1,
                "total_input_tokens": 123.0,
                "total_output_tokens": 42.0,
                "target_model": "GLM-5.2 FP8",
            }
        ]
    )
    validation = validate_aggregates(raw, published)
    statuses = validation.set_index("metric")["validation_status"]
    assert statuses["total_input_tokens"] == "pass"
    assert statuses["total_output_tokens"] == "pass"
    assert statuses["target_model"] == "pass_alias_equivalent"
    model_note = validation.loc[validation["metric"] == "target_model", "validation_note"].iloc[0]
    assert "literal target-model labels differ" in model_note
