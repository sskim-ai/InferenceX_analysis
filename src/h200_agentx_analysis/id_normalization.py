"""Conversation-ID normalization and auditable matching to source trace IDs.

The benchmark loader can append an AgentX branch suffix to a source trace ID.
It can also add replay/session decorations in future versions.  This module
never strips a decoration merely because it *looks* familiar: alternate rules
are accepted only when their output is observed in the source ID universe.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any

BRANCH_ROOT = "root"
BRANCH_SUBAGENT_MAIN = "subagent_main"
BRANCH_FANOUT = "fanout"
BRANCH_AUXILIARY = "auxiliary"
BRANCH_WORKER_GROUP = "worker_group"
BRANCH_UNKNOWN = "unknown"


@dataclass(frozen=True)
class NormalizedConversationId:
    conversation_id: str | None
    root_trace_id: str | None
    branch_suffix: str | None
    branch_type: str
    normalization_rule: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MatchResult:
    conversation_id: str | None
    root_trace_id: str | None
    branch_suffix: str | None
    branch_type: str
    normalization_rule: str
    source_id_matched: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_AGENT_SUFFIX = "::sa:"
_DIRECT_BRANCH_SUFFIXES: tuple[tuple[str, str, str], ...] = (
    ("::fa:", BRANCH_FANOUT, "split_direct_fanout_suffix"),
    ("::aux:", BRANCH_AUXILIARY, "split_direct_auxiliary_suffix"),
    ("::wg:", BRANCH_WORKER_GROUP, "split_direct_worker_group_suffix"),
)
_REPLAY_SUFFIX_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "strip_replay_suffix",
        re.compile(
            r"(?:::|__|[#|])(?:replay|instance|session|worker|copy|dup)(?:[:_\-]?[a-z0-9]+)+$", re.I
        ),
    ),
    (
        "strip_loader_dup_suffix",
        re.compile(r"(?:__|[#|])(?:dup|repeat)(?:[_\-]?\d+)+$", re.I),
    ),
)


def normalize_conversation_id(value: Any) -> NormalizedConversationId:
    """Apply the documented AgentX suffix rule without source-aware guessing."""

    conversation_id = _clean_id(value)
    if conversation_id is None:
        return NormalizedConversationId(None, None, None, BRANCH_UNKNOWN, "missing_conversation_id")

    if _AGENT_SUFFIX not in conversation_id:
        # The actual AgentX loader can emit branch decorations directly on a
        # root trace ID (for example ``<root>::fa:003``), not only below a
        # ``::sa:<agent>`` branch.  These suffixes are syntactic workload
        # paths, never part of the source root ID.
        for marker, branch_type, rule in _DIRECT_BRANCH_SUFFIXES:
            if marker not in conversation_id:
                continue
            root_trace_id, suffix_tail = conversation_id.split(marker, 1)
            if root_trace_id:
                return NormalizedConversationId(
                    conversation_id,
                    root_trace_id,
                    marker + suffix_tail,
                    branch_type,
                    rule,
                )
        return NormalizedConversationId(
            conversation_id,
            conversation_id,
            "root",
            BRANCH_ROOT,
            "identity",
        )
    root_trace_id, suffix_tail = conversation_id.split(_AGENT_SUFFIX, 1)
    if not root_trace_id:
        return NormalizedConversationId(
            conversation_id,
            None,
            _AGENT_SUFFIX + suffix_tail,
            BRANCH_UNKNOWN,
            "invalid_empty_root_before_sa",
        )
    suffix = _AGENT_SUFFIX + suffix_tail
    return NormalizedConversationId(
        conversation_id,
        root_trace_id,
        suffix,
        classify_branch_suffix(suffix),
        "split_before_first_sa",
    )


def classify_branch_suffix(branch_suffix: str | None) -> str:
    """Classify the documented AgentX suffix families conservatively."""

    if branch_suffix in {None, "", "root"}:
        return BRANCH_ROOT
    suffix = branch_suffix.lower()
    if suffix.startswith("::fa:"):
        return BRANCH_FANOUT
    if suffix.startswith("::aux:"):
        return BRANCH_AUXILIARY
    if suffix.startswith("::wg:"):
        return BRANCH_WORKER_GROUP
    if not suffix.startswith(_AGENT_SUFFIX):
        return BRANCH_UNKNOWN
    if ":fa:" in suffix:
        return BRANCH_FANOUT
    if ":aux:" in suffix:
        return BRANCH_AUXILIARY
    if ":wg:" in suffix:
        return BRANCH_WORKER_GROUP
    # ``::sa:<agent_id>`` is the regular nested-agent path.  Unknown extended
    # tags stay in this class only when an agent ID is present before the tag.
    tail = suffix[len(_AGENT_SUFFIX) :]
    if tail and not tail.startswith(":"):
        return BRANCH_SUBAGENT_MAIN
    return BRANCH_UNKNOWN


def source_branch_path(value: Any, *, root_trace_id: Any | None = None) -> str | None:
    """Map an H200 AgentX conversation path to the base source branch path.

    Source traces retain the root path or ``<root>::sa:<agent>``.  Runtime
    fan-out/auxiliary/worker-group decorations are workload-loader branches
    rather than independently represented source conversation paths, so they
    are stripped only after the agent identifier.
    """

    normalized = normalize_conversation_id(value)
    source_root = _clean_id(root_trace_id) or normalized.root_trace_id
    if normalized.conversation_id is None or source_root is None:
        return None
    if normalized.branch_type == BRANCH_ROOT:
        return source_root
    suffix = normalized.branch_suffix or ""
    if not suffix.startswith(_AGENT_SUFFIX):
        # Direct ``::fa:``, ``::aux:``, and ``::wg:`` decorations have no
        # independently serialized source branch.  They conservatively map to
        # the supplied source root and retain their H200 branch type separately.
        return source_root
    tail = suffix[len(_AGENT_SUFFIX) :] if suffix.startswith(_AGENT_SUFFIX) else ""
    agent_id = re.split(r":(?:fa|aux|wg):", tail, maxsplit=1, flags=re.I)[0]
    agent_id = agent_id.strip(":")
    if not agent_id:
        return None
    return f"{source_root}{_AGENT_SUFFIX}{agent_id}"


def candidate_root_ids(value: Any) -> list[tuple[str, str]]:
    """Return ordered normalization candidates, including only conservative rules."""

    normalized = normalize_conversation_id(value)
    root = normalized.root_trace_id
    if root is None:
        return []
    candidates: list[tuple[str, str]] = [(root, normalized.normalization_rule)]
    for rule, pattern in _REPLAY_SUFFIX_PATTERNS:
        stripped = pattern.sub("", root)
        if stripped and stripped != root:
            candidates.append((stripped, rule))
    # Preserve order and avoid reporting an equivalent rule twice.
    unique: list[tuple[str, str]] = []
    seen: set[str] = set()
    for candidate, rule in candidates:
        if candidate not in seen:
            seen.add(candidate)
            unique.append((candidate, rule))
    return unique


def normalize_to_source_ids(value: Any, source_ids: Iterable[Any]) -> MatchResult:
    """Normalize a conversation ID and select the first candidate found in source IDs.

    If no candidate matches, the documented primary root is still returned for
    transparent unmatched-ID reporting.
    """

    source_set = {_clean_id(item) for item in source_ids}
    source_set.discard(None)
    base = normalize_conversation_id(value)
    for candidate, rule in candidate_root_ids(value):
        if candidate in source_set:
            return MatchResult(
                conversation_id=base.conversation_id,
                root_trace_id=candidate,
                branch_suffix=base.branch_suffix,
                branch_type=base.branch_type,
                normalization_rule=rule,
                source_id_matched=True,
            )
    return MatchResult(
        conversation_id=base.conversation_id,
        root_trace_id=base.root_trace_id,
        branch_suffix=base.branch_suffix,
        branch_type=base.branch_type,
        normalization_rule=base.normalization_rule,
        source_id_matched=False,
    )


def normalize_dataframe(frame: Any, *, source_ids: Iterable[Any] | None = None) -> Any:
    """Add canonical ID columns to a pandas-like DataFrame.

    Pandas is imported lazily so core ID helpers remain usable in a bare
    Python preflight environment.
    """

    if "conversation_id" not in frame.columns:
        result = frame.copy()
        result["root_trace_id"] = None
        result["branch_suffix"] = None
        result["branch_type"] = BRANCH_UNKNOWN
        result["normalization_rule"] = "missing_conversation_id_column"
        result["source_id_matched"] = False
        return result

    source_values = list(source_ids) if source_ids is not None else None
    records = (
        [normalize_to_source_ids(value, source_values) for value in frame["conversation_id"]]
        if source_values is not None
        else [
            MatchResult(
                **normalize_conversation_id(value).to_dict(),
                source_id_matched=False,
            )
            for value in frame["conversation_id"]
        ]
    )
    result = frame.copy()
    result["root_trace_id"] = [record.root_trace_id for record in records]
    result["branch_suffix"] = [record.branch_suffix for record in records]
    result["branch_type"] = [record.branch_type for record in records]
    result["normalization_rule"] = [record.normalization_rule for record in records]
    result["source_id_matched"] = [record.source_id_matched for record in records]
    return result


def summarize_mapping(
    h200_frame: Any,
    source_ids: Iterable[Any],
    *,
    concurrency_column: str = "concurrency",
) -> Any:
    """Produce an auditable root-ID mapping summary by concurrency.

    The output intentionally includes unknown/missing conversation IDs instead
    of dropping them from the denominator.
    """

    import pandas as pd

    source_set = {_clean_id(value) for value in source_ids}
    source_set.discard(None)
    if h200_frame.empty:
        columns = [
            concurrency_column,
            "h200_request_rows",
            "h200_distinct_root_ids",
            "matched_root_ids",
            "unmatched_root_ids",
            "root_match_rate",
            "source_trace_count",
            "never_observed_source_ids",
        ]
        return pd.DataFrame(columns=columns)

    frame = normalize_dataframe(h200_frame, source_ids=source_set)
    if concurrency_column not in frame.columns:
        frame[concurrency_column] = None
    rows: list[dict[str, Any]] = []
    for concurrency, group in frame.groupby(concurrency_column, dropna=False):
        roots = {value for value in group["root_trace_id"] if value}
        matched = roots.intersection(source_set)
        rows.append(
            {
                concurrency_column: concurrency,
                "h200_request_rows": int(len(group)),
                "h200_distinct_root_ids": len(roots),
                "matched_root_ids": len(matched),
                "unmatched_root_ids": len(roots - source_set),
                "root_match_rate": len(matched) / len(roots) if roots else None,
                "source_trace_count": len(source_set),
                "never_observed_source_ids": len(source_set - matched),
            }
        )
    return pd.DataFrame(rows)


def _clean_id(value: Any) -> str | None:
    if value is None:
        return None
    if type(value).__name__ == "NAType":
        return None
    try:
        if bool(value != value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text or None
