import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from h200_agentx_analysis.id_normalization import (
    BRANCH_AUXILIARY,
    BRANCH_FANOUT,
    BRANCH_ROOT,
    BRANCH_SUBAGENT_MAIN,
    BRANCH_WORKER_GROUP,
    normalize_conversation_id,
    normalize_to_source_ids,
    source_branch_path,
)


@pytest.mark.parametrize(
    ("conversation_id", "branch_type"),
    [
        ("abc", BRANCH_ROOT),
        ("abc::sa:agent_001", BRANCH_SUBAGENT_MAIN),
        ("abc::sa:agent_001:fa:000", BRANCH_FANOUT),
        ("abc::sa:agent_001:aux:000", BRANCH_AUXILIARY),
        ("abc::sa:agent_001:wg:001_002", BRANCH_WORKER_GROUP),
        ("abc::fa:000", BRANCH_FANOUT),
        ("abc::aux:000", BRANCH_AUXILIARY),
    ],
)
def test_documented_agentx_suffixes_normalize_to_root(
    conversation_id: str, branch_type: str
) -> None:
    normalized = normalize_conversation_id(conversation_id)
    assert normalized.root_trace_id == "abc"
    assert normalized.branch_type == branch_type


def test_source_aware_replay_suffix_is_only_used_when_source_matches() -> None:
    matched = normalize_to_source_ids("abc__replay_7::sa:a", {"abc"})
    assert matched.root_trace_id == "abc"
    assert matched.source_id_matched
    assert matched.normalization_rule == "strip_replay_suffix"
    unmatched = normalize_to_source_ids("abc__replay_7::sa:a", {"elsewhere"})
    assert unmatched.root_trace_id == "abc__replay_7"
    assert not unmatched.source_id_matched


def test_runtime_branch_decorations_map_to_base_source_path() -> None:
    assert source_branch_path("abc") == "abc"
    assert source_branch_path("abc::sa:agent:fa:000") == "abc::sa:agent"
    assert source_branch_path("abc::sa:agent:aux:000") == "abc::sa:agent"
    assert source_branch_path("abc::fa:000") == "abc"
    assert source_branch_path("abc::aux:000") == "abc"


def test_join_uses_unique_source_columns_and_matches_decorated_branch() -> None:
    # Regression: right join keys also occur in the source payload field list;
    # duplicate labels used to make the pandas merge fail before matching.
    script = Path(__file__).resolve().parents[1] / "scripts" / "join_trace_ids.py"
    spec = importlib.util.spec_from_file_location("join_trace_ids_for_test", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    h200 = pd.DataFrame(
        [
            {
                "conversation_id": "abc::sa:agent:fa:000",
                "turn_index": 2,
                "input_tokens": 100,
                "concurrency": 2,
            }
        ]
    )
    source = pd.DataFrame(
        [
            {
                "root_trace_id": "abc",
                "source_conversation_path": "abc::sa:agent",
                "source_branch_request_index": 2,
                "source_input_tokens": 100,
                "source_request_index": 8,
                "theoretical_new_tokens": 25,
            }
        ]
    )
    joined = module._join(h200, {"abc"}, source)
    assert joined.loc[0, "match_class"] == "exact_turn_match"
    assert joined.loc[0, "source_request_index"] == 8


def test_join_prefers_explicit_loader_source_root_and_turn_metadata() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "join_trace_ids.py"
    spec = importlib.util.spec_from_file_location("join_trace_ids_metadata_for_test", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    h200 = pd.DataFrame(
        [
            {
                "conversation_id": "rendered-id::aux:001",
                "source_trace_id": "abc",
                "source_outer_idx": 3,
                "source_inner_idx": None,
                "turn_index": 0,
                "input_tokens": 100,
                "output_tokens": 10,
                "concurrency": 1,
            }
        ]
    )
    source = pd.DataFrame(
        [
            {
                "root_trace_id": "abc",
                "source_conversation_path": "abc",
                "source_outer_request_index": 3,
                "source_inner_request_index": None,
                "source_branch_request_index": 3,
                "source_input_tokens": 100,
                "source_output_tokens": 10,
                "source_request_index": 3,
            }
        ]
    )
    joined = module._join(h200, {"abc"}, source)
    assert joined.loc[0, "root_trace_id"] == "abc"
    assert joined.loc[0, "root_trace_id_provenance"] == "metadata.source_trace_id"
    assert bool(joined.loc[0, "loader_metadata_turn_match"])
    assert bool(joined.loc[0, "loader_metadata_input_tokens_match"])
    assert joined.loc[0, "match_class"] == "exact_turn_match"
