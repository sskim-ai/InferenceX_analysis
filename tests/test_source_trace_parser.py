from __future__ import annotations

import json
from pathlib import Path

import pytest

from h200_agentx_analysis.hf_trace_parser import (
    TraceAccumulator,
    TraceJSONLError,
    flatten_trace,
    iter_source_requests,
    iter_trace_objects,
    longest_common_prefix,
)
from h200_agentx_analysis.source_flattening import build_source_trace_tables


def _request(
    *,
    t: float,
    model: str,
    input_tokens: int,
    output_tokens: int,
    hash_ids: list[int],
    request_type: str = "s",
) -> dict[str, object]:
    return {
        "t": t,
        "model": model,
        "in": input_tokens,
        "out": output_tokens,
        "hash_ids": hash_ids,
        "api_time": 1.25,
        "ttft": 0.5,
        "think_time": 0.1,
        "type": request_type,
    }


def _trace() -> dict[str, object]:
    return {
        "id": "abc",
        "models": ["claude-opus-source", "claude-haiku-source"],
        "block_size": 64,
        "hash_id_scope": "local",
        "requests": [
            _request(
                t=0.0,
                model="claude-opus-source",
                input_tokens=128,
                output_tokens=4,
                hash_ids=[0, 1],
            ),
            {
                "t": 0.5,
                "type": "subagent",
                "agent_id": "agent_001",
                "subagent_type": "Subagent",
                "duration_ms": 100,
                "requests": [
                    _request(
                        t=0.5,
                        model="claude-haiku-source",
                        input_tokens=192,
                        output_tokens=3,
                        hash_ids=[10, 11, 12],
                    ),
                    _request(
                        t=0.75,
                        model="claude-haiku-source",
                        input_tokens=256,
                        output_tokens=5,
                        hash_ids=[10, 11, 12, 13],
                        request_type="n",
                    ),
                ],
            },
            _request(
                t=1.0,
                model="claude-opus-source",
                input_tokens=192,
                output_tokens=6,
                hash_ids=[0, 1, 2],
            ),
        ],
    }


def test_flattens_top_level_and_nested_subagent_requests() -> None:
    rows, summary = flatten_trace(_trace())

    assert len(rows) == 4
    assert [row["source_branch_type"] for row in rows] == ["root", "subagent", "subagent", "root"]
    assert rows[0]["source_conversation_path"] == "abc"
    assert rows[1]["source_conversation_path"] == "abc::sa:agent_001"
    assert rows[1]["source_parent_conversation_path"] == "abc"
    assert rows[1]["source_agent_id"] == "agent_001"
    assert rows[1]["source_outer_request_index"] == 1
    assert rows[1]["source_inner_request_index"] == 0
    assert rows[1]["branch_fork_indicator"] is True
    assert summary["source_request_count_total"] == 4
    assert summary["source_root_request_count"] == 2
    assert summary["source_subagent_count"] == 1
    assert summary["source_subagent_request_count"] == 2
    assert summary["source_total_input_tokens"] == 768
    assert summary["source_total_output_tokens"] == 18


def test_theoretical_hash_prefix_fields_are_branch_local() -> None:
    rows, _ = flatten_trace(_trace())

    # The root's second request shares two 64-token blocks with its prior root
    # request, even though a subagent ran between the two root requests.
    root_second = rows[3]
    assert root_second["lcp_block_count"] == 2
    assert root_second["theoretical_cached_tokens"] == 128
    assert root_second["theoretical_new_tokens"] == 64
    assert root_second["theoretical_cache_ratio"] == pytest.approx(128 / 192)
    assert root_second["rollback_blocks"] == 0

    # The first subagent request has no prior request in *that* branch; the
    # next one does have a three-block common prefix.
    assert rows[1]["lcp_block_count"] is None
    assert rows[2]["lcp_block_count"] == 3
    assert rows[2]["theoretical_cached_tokens"] == 192
    assert rows[2]["theoretical_new_tokens"] == 64
    assert rows[2]["hash_ids_fingerprint"]
    assert "hash_ids" not in rows[2]


def test_empty_subagent_is_counted_without_creating_a_request_row() -> None:
    trace = _trace()
    requests = trace["requests"]
    assert isinstance(requests, list)
    requests.insert(
        1,
        {
            "type": "subagent",
            "agent_id": "empty",
            "subagent_type": "Subagent",
            "requests": [],
        },
    )
    accumulator = TraceAccumulator.from_trace(trace)
    rows = list(iter_source_requests(trace, accumulator=accumulator))
    summary = accumulator.summary_row()

    assert len(rows) == 4
    assert summary["source_subagent_count"] == 2
    assert summary["source_subagent_request_count"] == 2


def test_models_and_source_metrics_are_preserved_separately() -> None:
    rows, summary = flatten_trace(_trace())

    assert json.loads(summary["source_models"]) == ["claude-opus-source", "claude-haiku-source"]
    assert rows[0]["source_model"] == "claude-opus-source"
    assert rows[0]["source_api_time_s"] == pytest.approx(1.25)
    assert rows[0]["source_ttft_s"] == pytest.approx(0.5)
    assert rows[0]["source_think_time_s"] == pytest.approx(0.1)


def test_streaming_jsonl_rejects_malformed_line(tmp_path: Path) -> None:
    source = tmp_path / "traces.jsonl"
    source.write_text('{"id":"good","requests":[]}\n{not json}\n', encoding="utf-8")

    iterator = iter_trace_objects(source)
    assert next(iterator)["id"] == "good"
    with pytest.raises(TraceJSONLError, match="line 2"):
        next(iterator)


def test_prefix_helper_handles_empty_and_diverging_sequences() -> None:
    assert longest_common_prefix([], []) == 0
    assert longest_common_prefix([1, 2, 3], [1, 2, 4]) == 2
    assert longest_common_prefix([1], [2]) == 0


def test_streaming_builder_writes_summary_and_request_parquet(tmp_path: Path) -> None:
    pyarrow = pytest.importorskip("pyarrow")
    source = tmp_path / "traces.jsonl"
    source.write_text(json.dumps(_trace()) + "\n", encoding="utf-8")

    result = build_source_trace_tables(source, tmp_path / "processed", batch_size=1)

    assert result.source_available is True
    assert result.trace_count == 1
    assert result.request_count == 4
    summary = pyarrow.parquet.read_table(result.summary_path).to_pylist()
    requests = pyarrow.parquet.read_table(result.requests_path).to_pylist()
    assert summary[0]["root_trace_id"] == "abc"
    assert len(requests) == 4
    assert requests[2]["theoretical_new_tokens"] == 64


def test_missing_source_empty_policy_is_explicit(tmp_path: Path) -> None:
    pyarrow = pytest.importorskip("pyarrow")

    result = build_source_trace_tables(
        tmp_path / "not-acquired.jsonl", tmp_path / "processed", missing_policy="empty"
    )

    assert result.source_available is False
    assert result.trace_count == 0
    assert pyarrow.parquet.read_table(result.summary_path).num_rows == 0
    assert pyarrow.parquet.read_table(result.requests_path).num_rows == 0


def test_duplicate_root_does_not_replace_existing_outputs(tmp_path: Path) -> None:
    source = tmp_path / "traces.jsonl"
    source.write_text(json.dumps(_trace()) + "\n" + json.dumps(_trace()) + "\n", encoding="utf-8")
    processed = tmp_path / "processed"
    processed.mkdir()
    summary = processed / "source_trace_summary.parquet"
    requests = processed / "source_requests.parquet"
    summary.write_text("keep-summary", encoding="utf-8")
    requests.write_text("keep-requests", encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate root trace id"):
        build_source_trace_tables(source, processed, batch_size=1)

    assert summary.read_text(encoding="utf-8") == "keep-summary"
    assert requests.read_text(encoding="utf-8") == "keep-requests"
    assert not list(processed.glob("*.building"))
