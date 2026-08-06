import json

import pandas as pd

from h200_agentx_analysis.metrics import (
    exact_duplicate_fingerprints,
    exact_duplicate_mask,
    filter_profile_records,
)


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "github_run_id": "run",
        "artifact_id": "artifact-a",
        "concurrency": 1,
        "conversation_id": "root",
        "session_num": 0,
        "turn_index": 1,
        "request_start_ns": 100,
        "record_ordinal": 1,
        "source_file_path": "first.jsonl",
        "benchmark_phase": "profiling",
        "error_present": False,
        "was_cancelled": False,
        "input_tokens": 10,
        "output_tokens": 3,
        "ttft_ms": 10.0,
        "e2e_ms": 20.0,
        "itl_ms": 5.0,
    }
    row.update(overrides)
    return row


def test_only_fully_identical_records_are_duplicate_candidates() -> None:
    identical = _row(record_ordinal=2, source_file_path="duplicate.jsonl")
    other_session = _row(session_num=1)
    other_artifact = _row(artifact_id="artifact-b")
    frame = pd.DataFrame([_row(), identical, other_session, other_artifact])
    mask = exact_duplicate_mask(frame)
    assert mask.tolist() == [False, True, False, False]


def test_duplicate_exclusion_is_opt_in_and_keeps_replays() -> None:
    first = _row()
    duplicate = _row(record_ordinal=2)
    replay = _row(session_num=1)
    frame = pd.DataFrame([first, duplicate, replay])
    included, _ = filter_profile_records(frame, exclude_exact_duplicates=False)
    assert len(included) == 3
    included, excluded = filter_profile_records(frame, exclude_exact_duplicates=True)
    assert len(included) == 2
    assert excluded.iloc[0]["exclusion_reason"] == "exact_duplicate"


def test_full_record_fingerprint_is_stable_across_streaming_batches() -> None:
    first = pd.DataFrame([_row(record_ordinal=1)])
    second = pd.DataFrame([_row(record_ordinal=999, source_file_path="later.jsonl")])
    first_fingerprint = exact_duplicate_fingerprints(first).iloc[0]
    second_fingerprint = exact_duplicate_fingerprints(second).iloc[0]
    assert first_fingerprint == second_fingerprint


def test_h200_builder_marks_exact_duplicates_split_across_batches(tmp_path) -> None:
    from h200_agentx_analysis.h200_io import build_h200_request_tables

    profile = tmp_path / "raw" / "conc1" / "raw_agentic" / "profile_export.jsonl"
    profile.parent.mkdir(parents=True)
    record = {
        "metadata": {
            "session_num": 0,
            "conversation_id": "trace-a",
            "turn_index": 0,
            "request_start_ns": 1,
            "request_end_ns": 10,
            "benchmark_phase": "profiling",
            "was_cancelled": False,
        },
        "metrics": {
            "input_sequence_length": {"value": 10, "unit": "tokens"},
            "output_sequence_length": {"value": 2, "unit": "tokens"},
            "time_to_first_token": {"value": 2, "unit": "ms"},
            "request_latency": {"value": 5, "unit": "ms"},
            "inter_token_latency": {"value": 3, "unit": "ms"},
        },
    }
    profile.write_text("\n".join([json.dumps(record), json.dumps(record)]) + "\n", encoding="utf-8")
    output = tmp_path / "processed"
    result = build_h200_request_tables(profile.parents[2], output, batch_size=1)
    rows = pd.read_parquet(output / "h200_requests_all.parquet")
    profiled = pd.read_parquet(output / "h200_requests_profiled.parquet")
    assert result.exact_duplicate_count == 1
    assert rows["is_exact_duplicate"].tolist() == [False, True]
    # Exact duplicate handling is deliberately explicit: source-compatible
    # profiling rows are retained and carry the duplicate marker for analysis.
    assert len(profiled) == 2
