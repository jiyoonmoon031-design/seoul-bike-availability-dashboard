from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.modeling.naive_baseline import add_naive_predictions  # noqa: E402
from src.modeling.naive_baseline import (
    assign_chronological_splits,
    evaluate_naive_baselines,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate Week 03 persistence and zero naive baselines."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument(
        "--params",
        type=Path,
        default=Path("config/params.yaml"),
    )
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=Path("reports/week03/naive_baseline_metrics.csv"),
    )
    parser.add_argument(
        "--predictions-output",
        type=Path,
        help="Optional parquet containing targets, splits, and predictions",
    )
    parser.add_argument(
        "--allow-short-history",
        action="store_true",
        help="Smoke-test only: do not enforce minimum_history_days",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    params = yaml.safe_load(args.params.read_text(encoding="utf-8"))
    evaluation = params["EVALUATION"]
    active_percentile = float(params["ACTIVE_STATION"]["percentile"])

    frame = pd.read_parquet(args.input.expanduser().resolve())
    frame = add_naive_predictions(frame)
    frame = assign_chronological_splits(
        frame,
        validation_days=int(evaluation["validation_days"]),
        test_days=int(evaluation["test_days"]),
        minimum_history_days=int(evaluation["minimum_history_days"]),
        enforce_minimum_history=not args.allow_short_history,
    )
    metrics = evaluate_naive_baselines(
        frame,
        active_percentile=active_percentile,
    )

    metrics_path = args.metrics_output.expanduser().resolve()
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(metrics_path, index=False)

    if args.predictions_output:
        prediction_path = args.predictions_output.expanduser().resolve()
        prediction_path.parent.mkdir(parents=True, exist_ok=True)
        prediction_columns = [
            column
            for column in frame.columns
            if column
            in {
                "station_id",
                "base_time",
                "district",
                "is_peak",
                "split",
            }
            or column.startswith("delta_hist_h")
            or column.startswith("target_h")
            or column.startswith("prediction_")
            or column.startswith("persistence_h")
        ]
        frame[prediction_columns].to_parquet(prediction_path, index=False)
        print(f"Predictions: {prediction_path}")

    print(metrics.to_string(index=False))
    print(f"Metrics: {metrics_path}")


if __name__ == "__main__":
    main()
