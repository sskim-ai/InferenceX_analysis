import pandas as pd

from h200_agentx_analysis.plotting import _cross_concurrency_ratio_groups, _rank_metric_subset


def test_rank_metric_subset_prevents_wall_time_chart_from_using_ttft_block() -> None:
    # The top-ID CSV concatenates separate top-N blocks. A chart whose title
    # says wall time must not use the first (TTFT-ranked) block by position.
    frame = pd.DataFrame(
        {
            "root_trace_id": ["ttft-id", "wall-a", "wall-b"],
            "rank_metric": [
                "median_ttft_ms",
                "total_h200_wall_time_s",
                "total_h200_wall_time_s",
            ],
            "total_h200_wall_time_s": [999.0, 10.0, 20.0],
        }
    )
    selected = _rank_metric_subset(frame, "total_h200_wall_time_s")
    assert selected["root_trace_id"].tolist() == ["wall-a", "wall-b"]
    assert selected["total_h200_wall_time_s"].tolist() == [10.0, 20.0]


def test_cross_concurrency_ratio_groups_drop_self_baselines_and_mark_confounded() -> None:
    frame = pd.DataFrame(
        {
            "concurrency": [1, 2, 3],
            "baseline_concurrency": [1, 1, 1],
            "coverage_comparable": [True, True, False],
        }
    )
    comparable, confounded = _cross_concurrency_ratio_groups(frame)
    assert comparable["concurrency"].tolist() == [2]
    assert confounded["concurrency"].tolist() == [3]
