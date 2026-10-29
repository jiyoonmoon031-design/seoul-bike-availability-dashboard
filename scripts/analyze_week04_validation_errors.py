from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modeling.model_comparison import (
    active_station_definition,
    assign_purged_ratio_splits,
)

HORIZONS = (15, 30, 60)
MODEL_PREFIXES = {
    "b1_persistence": "prediction_b1_persistence",
    "b2_recent_mean": "prediction_b2_recent_mean",
    "b3_dow_time_mean": "prediction_b3_dow_time_mean",
    "linear_model": "prediction_linear_model",
    "random_forest": "prediction_random_forest",
    "lightgbm": "prediction_lightgbm",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze Week 04 validation residual distributions."
    )
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--feature-table", required=True, type=Path)
    parser.add_argument("--params", type=Path, default=Path("config/params.yaml"))
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def required_prediction_columns() -> list[str]:
    columns = ["station_id", "base_time", "district", "is_peak"]
    for horizon in HORIZONS:
        columns.extend(
            [
                f"delta_hist_h{horizon}",
                f"target_h{horizon}_valid",
            ]
        )
        columns.extend(
            f"{prefix}_h{horizon}" for prefix in MODEL_PREFIXES.values()
        )
    return columns


def load_active_stations(
    feature_table: Path,
    params: dict,
) -> tuple[set[str], float]:
    columns = [
        "station_id",
        "base_time",
        "rent_count",
        "return_count",
        "is_observed",
    ]
    available = set(pq.ParquetFile(feature_table).schema.names)
    missing = set(columns) - available
    if missing:
        raise ValueError(f"feature table missing columns: {sorted(missing)}")

    frame = pd.read_parquet(feature_table, columns=columns)
    split_cfg = params["WEEK04_MODEL_COMPARISON"]["split"]
    split = assign_purged_ratio_splits(
        frame,
        train_ratio=float(split_cfg["train_ratio"]),
        validation_ratio=float(split_cfg["validation_ratio"]),
        test_ratio=float(split_cfg["test_ratio"]),
        gap_minutes=int(split_cfg["gap_minutes"]),
    )
    return active_station_definition(
        split.frame,
        percentile=float(params["ACTIVE_STATION"]["percentile"]),
    )


def summarize_residuals(
    residual: np.ndarray,
    absolute: np.ndarray,
) -> dict[str, float | int]:
    return {
        "evaluated_rows": int(residual.size),
        "mae": float(absolute.mean()),
        "rmse": float(np.sqrt(np.square(residual).mean())),
        "mean_error": float(residual.mean()),
        "median_error": float(np.median(residual)),
        "q05_error": float(np.quantile(residual, 0.05)),
        "q25_error": float(np.quantile(residual, 0.25)),
        "q75_error": float(np.quantile(residual, 0.75)),
        "q95_error": float(np.quantile(residual, 0.95)),
        "underprediction_rate": float(np.mean(residual < 0)),
        "overprediction_rate": float(np.mean(residual > 0)),
        "exact_rate": float(np.mean(residual == 0)),
    }


def main() -> None:
    args = parse_args()
    params = yaml.safe_load(args.params.read_text(encoding="utf-8"))
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    active_stations, active_threshold = load_active_stations(
        args.feature_table,
        params,
    )
    frame = pd.read_parquet(
        args.predictions,
        columns=required_prediction_columns(),
    )
    frame["base_time"] = pd.to_datetime(frame["base_time"])
    frame["hour"] = frame["base_time"].dt.hour
    frame["is_active"] = frame["station_id"].astype(str).isin(active_stations)

    summary_rows: list[dict] = []
    segment_rows: list[dict] = []
    hourly_rows: list[dict] = []
    station_rows: list[dict] = []
    worst_rows: list[dict] = []

    segments = {
        "ALL": pd.Series(True, index=frame.index),
        "ACTIVE": frame["is_active"],
        "PEAK": frame["is_peak"].astype(bool),
        "ACTIVE_PEAK": frame["is_active"] & frame["is_peak"].astype(bool),
    }

    for model_id, prefix in MODEL_PREFIXES.items():
        for horizon in HORIZONS:
            target_column = f"delta_hist_h{horizon}"
            valid_column = f"target_h{horizon}_valid"
            prediction_column = f"{prefix}_h{horizon}"
            valid = (
                frame[valid_column].astype(bool)
                & frame[target_column].notna()
                & frame[prediction_column].notna()
            )
            subset = frame.loc[
                valid,
                [
                    "station_id",
                    "base_time",
                    "district",
                    "hour",
                    target_column,
                    prediction_column,
                ],
            ].copy()
            subset["residual"] = (
                subset[prediction_column] - subset[target_column]
            )
            subset["absolute_error"] = subset["residual"].abs()

            summary_rows.append(
                {
                    "model_id": model_id,
                    "horizon_min": horizon,
                    **summarize_residuals(
                        subset["residual"].to_numpy(),
                        subset["absolute_error"].to_numpy(),
                    ),
                }
            )

            for segment, mask in segments.items():
                segment_subset = subset.loc[mask.loc[subset.index]]
                segment_rows.append(
                    {
                        "model_id": model_id,
                        "horizon_min": horizon,
                        "segment": segment,
                        **summarize_residuals(
                            segment_subset["residual"].to_numpy(),
                            segment_subset["absolute_error"].to_numpy(),
                        ),
                    }
                )

            hourly = subset.groupby("hour", sort=True).agg(
                evaluated_rows=("residual", "size"),
                mae=("absolute_error", "mean"),
                mean_error=("residual", "mean"),
            )
            for hour, row in hourly.iterrows():
                hourly_rows.append(
                    {
                        "model_id": model_id,
                        "horizon_min": horizon,
                        "hour": int(hour),
                        **row.to_dict(),
                    }
                )

            station = subset.groupby("station_id", sort=True).agg(
                evaluated_rows=("residual", "size"),
                mae=("absolute_error", "mean"),
                mean_error=("residual", "mean"),
            )
            for station_id, row in station.iterrows():
                station_rows.append(
                    {
                        "model_id": model_id,
                        "horizon_min": horizon,
                        "station_id": station_id,
                        **row.to_dict(),
                    }
                )

            worst = subset.nlargest(10, "absolute_error")
            for rank, (_, row) in enumerate(worst.iterrows(), start=1):
                worst_rows.append(
                    {
                        "model_id": model_id,
                        "horizon_min": horizon,
                        "rank": rank,
                        "station_id": row["station_id"],
                        "base_time": row["base_time"].isoformat(),
                        "district": row["district"],
                        "y_true": row[target_column],
                        "y_pred": row[prediction_column],
                        "residual": row["residual"],
                        "absolute_error": row["absolute_error"],
                    }
                )

    outputs = {
        "residual_summary.csv": summary_rows,
        "residual_by_segment.csv": segment_rows,
        "residual_by_hour.csv": hourly_rows,
        "residual_by_station.csv": station_rows,
        "worst_cases.csv": worst_rows,
    }
    for filename, rows in outputs.items():
        pd.DataFrame(rows).to_csv(output_dir / filename, index=False)

    (output_dir / "analysis_metadata.txt").write_text(
        "\n".join(
            [
                f"prediction_rows={len(frame)}",
                f"active_station_threshold={active_threshold}",
                f"active_station_count={len(active_stations)}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
