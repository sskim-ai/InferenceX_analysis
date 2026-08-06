from __future__ import annotations

import json

from h200_agentx_analysis.plotting import generate_figures
from h200_agentx_analysis.reporting import generate_reports


def test_blocked_h200_status_is_reported_as_unknown_not_zero(tmp_path) -> None:
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    (processed / "h200_build_status.json").write_text(
        json.dumps(
            {
                "status": "blocked_no_profile_export",
                "h200_available": False,
                "profiled_record_count": 0,
            }
        ),
        encoding="utf-8",
    )
    (processed / "coverage_status.json").write_text(
        json.dumps(
            {
                "status": "blocked_no_profile_export",
                "interpretation": "zero coverage must not be inferred",
            }
        ),
        encoding="utf-8",
    )

    generate_reports(tmp_path)
    outputs = generate_figures(tmp_path)

    coverage_report = (tmp_path / "reports" / "04_coverage.md").read_text(encoding="utf-8")
    korean_report = (tmp_path / "reports" / "results_summary_ko.md").read_text(
        encoding="utf-8"
    )
    assert "cannot be measured because raw artifacts are unavailable" in coverage_report
    assert "0으로 해석하지 않는다" in korean_report
    assert len(outputs) == 15
    assert all(path.exists() for path in outputs)
