import json

import pandas as pd

from src.validation.recommendation_report import write_report


def test_report_contains_horizon_and_micro_results(tmp_path):
    metrics = pd.DataFrame(
        [
            {
                "scope": "horizon",
                "horizon_min": 15,
                "mode": "rent",
                "availability_threshold": 1,
                "eligible_requests": 10,
                "hits": 9,
                "hit_rate": 0.9,
                "mean_candidates": 3,
            },
            {
                "scope": "micro",
                "horizon_min": None,
                "mode": "return",
                "availability_threshold": 2,
                "eligible_requests": 30,
                "hits": 24,
                "hit_rate": 0.8,
                "mean_candidates": 3,
            },
        ]
    )
    metrics_path = tmp_path / "metrics.csv"
    metadata_path = tmp_path / "metadata.json"
    report_path = tmp_path / "report.md"
    figure_path = tmp_path / "figures" / "hit-rate.svg"
    metrics.to_csv(metrics_path, index=False)
    metadata_path.write_text(
        json.dumps(
            {
                "input_sha256": "abc123",
                "candidate_rows": 120,
                "eligible_requests": 40,
            }
        ),
        encoding="utf-8",
    )

    write_report(metrics_path, metadata_path, report_path, figure_path)

    report = report_path.read_text(encoding="utf-8")
    assert "15 min" in report
    assert "ALL micro" in report
    assert "90.00%" in report
    assert "Below target" in report
    assert "abc123" in report
    assert figure_path.exists()
