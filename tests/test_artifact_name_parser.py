from h200_agentx_analysis.artifact_parser import (
    AGGREGATE_CATEGORY,
    RAW_CATEGORY,
    artifact_category,
    duplicate_artifacts,
    parse_artifact_inventory,
    parse_concurrency,
)


def test_real_style_agentic_names_are_classified_and_parsed() -> None:
    raw = "agentic_glm5.2_p1x1_d1x8_conc2_kvdram-hisparse_fp8_dynamo-sglang_conc2_h200"
    aggregate = "bmk_agentic_glm5.2_p1x1_d1x8_conc8_h200"
    assert artifact_category(raw) == RAW_CATEGORY
    assert parse_concurrency(raw) == 2
    assert artifact_category(aggregate) == AGGREGATE_CATEGORY
    assert parse_concurrency(aggregate) == 8


def test_invalid_or_ambiguous_concurrency_is_not_assigned() -> None:
    assert parse_concurrency("agentic_no_concurrency_h200") is None
    assert parse_concurrency("agentic_conc1_conc2_h200") is None
    assert artifact_category("results_bmk") == "run_summary"


def test_duplicate_artifact_detection_is_scoped_to_category_and_concurrency() -> None:
    inventory = parse_artifact_inventory(
        {
            "artifacts": [
                {"id": 1, "name": "agentic_glm_conc1"},
                {"id": 2, "name": "agentic_glm_conc1_copy"},
                {"id": 3, "name": "bmk_agentic_glm_conc1"},
            ]
        }
    )
    duplicates = duplicate_artifacts(inventory)
    assert list(duplicates) == [(RAW_CATEGORY, 1)]
    assert [item.artifact_id for item in duplicates[(RAW_CATEGORY, 1)]] == ["1", "2"]
