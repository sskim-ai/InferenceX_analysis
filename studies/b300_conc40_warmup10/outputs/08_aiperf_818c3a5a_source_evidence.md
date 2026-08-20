# AIPerf 818c3a5a source evidence

## Pins

- InferenceX commit: `8767d90c11860a10668f2d66179711a9c24fc8bd`
- `git ls-tree` gitlink: `818c3a5a2922c535af6271ff296ed374e292b8e4 utils/aiperf`
- Historical AIPerf checkout: `818c3a5a2922c535af6271ff296ed374e292b8e4`
- Historical public corpus alias: `semianalysis_cc_traces_weka_062126` -> `semianalysisai/cc-traces-weka-062126`, revision `23f152f6f0f9399a85901b89a6458def0ef16729`.

## Implementation path

1. Flag definition: `src/aiperf/config/flags/cli_config.py:2289-2303`. The description says the budget is per concurrency lane and additional to mandatory snapshot primers.
2. Phase config field: `src/aiperf/config/phases.py:365-377`.
3. Warmup request target: `src/aiperf/timing/phase/runner.py:153-170` computes `sum(baseline_counts) + requests_per_lane * lane_count`; this run logged 44 + 10*40 = 444.
4. t* snapshot construction: `src/aiperf/timing/trajectory_source.py:607-642` samples t* from the 0.25-0.75 time range, then builds the snapshot.
5. Mandatory primer selection: `src/aiperf/timing/trajectory_source.py:74-93` selects `next_turn_index - 1` for each live stream; `:422-449` counts one primer for every live stream having a pre-t* request.
6. Primer dispatch: `src/aiperf/timing/strategies/agentic_replay.py:625-768`; it prepares root and subagent primers and aligns them to t*.
7. Per-lane pressure quota: `src/aiperf/timing/strategies/agentic_replay.py:443-501`; baseline primers do not consume quota, while every later admitted `TurnToSend` increments the lane counter, regardless of root/subagent conversation.
8. Pressure replay: `src/aiperf/timing/strategies/agentic_replay.py:779-825` and `:831-929`; it resumes at the post-snapshot next request, sets max tokens to 1, removes idle delays, and continues the live DAG.
9. Profiling handoff: `src/aiperf/timing/strategies/agentic_replay.py:951-975`, `:1317-1436`, and `:1665-1803` persist the drained live streams and resume their next request in profiling.
10. Recycle: `src/aiperf/timing/strategies/agentic_replay.py:1606-1643` and `:1871-1886`; a recycled trace starts a fresh session at turn 0. The same method can be reached during accelerated warmup, so a lane may change root before its 10-request quota is full. Profiling recycle has no new warmup phase.
11. Output shortening: `_WARMUP_MAX_TOKENS = 1` at `src/aiperf/timing/strategies/agentic_replay.py:86`; all warmup turn builders apply it at `:1888-1902`.
12. Phase recording: `src/aiperf/records/record_processor_service.py:246-266` copies `credit_phase` to `benchmark_phase` and preserves trace/source indices and correlation IDs in export metadata.
13. Source provenance: `src/aiperf/dataset/loader/weka_trace.py:1612-1694` emits root/main turns with `(source_outer_idx, NULL)`; `:1932-1999` emits nested subagent turns with `(source_outer_idx, source_inner_idx)`; `:2003-2091` emits detected flat-agent chains while preserving their outer indices.
14. Historical global source ordering evidence: `src/aiperf/dataset/loader/weka_trace.py:1252-1316` orders shared trace records by `(t, outer_idx, stream_idx, k)`. No equal `(t, outer_idx)` group occurred in the 94 source roots observed here, so the derived source positions have no tie ambiguity.

## Answers A-I

- A: `10` means 10 additional admitted model-request credits per live trajectory lane, not 10 root turns, sessions, or source rows attached to one fixed root.
- B: First, each live stream gets its last request before t* as a mandatory primer. Then the configured 10-request pressure budget replays post-t* requests from the live DAG; if a tree finishes, a fresh root at source turn 0 can continue consuming that lane's quota.
- C: Yes. Subagent requests are ordinary admitted turns for the lane quota. Artifact: pressure stage root=269, subagent=131.
- D: The phase starts with 40 initial lanes, but the quota belongs to lanes, not immutable initial roots. Warmup-time recycling produced additional root IDs.
- E: Profiling-time recycled traces do not receive this warmup; they start fresh at turn 0.
- F: Warmup output is forced to 1 token. Artifact independently shows output_sequence_length=1 for all 444 warmup records.
- G: Recorded idle gaps are not retained in the pressure stage: it runs with zero idle delay. Mandatory primers are t*-aligned and their lead is capped by the scenario's global system-idle guard (`agentic_replay.py:609-623`); the per-trace runtime idle cap is profiling-only (`timing/phase/runner.py:223-238`).
- H: Yes. Export metadata records phase directly; artifact has `benchmark_phase=warmup` for 444 rows.
- I: t* is sampled first, the live snapshot is built, pre-t* primers run, and only then the 10 post-snapshot pressure requests per lane run before profiling handoff.
