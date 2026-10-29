from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import joblib
import pandas as pd
import pyarrow.parquet as pq
import yaml

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modeling.final_model import evaluate_fitted_candidate  # noqa: E402
from src.modeling.model_comparison import (  # noqa: E402
    active_station_definition,
    assign_purged_ratio_splits,
    validate_week03_feature_allowlist,
)

METRIC_COLUMNS = (
    "evaluated_rows",
    "mae",
    "rmse",
    "b1_mae_same_rows",
    "improvement_vs_b1",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Independently reproduce Week 05 final model metrics."
    )
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--feature-table", required=True, type=Path)
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("reports/week05/final_model_metadata.json"),
    )
    parser.add_argument(
        "--expected-metrics",
        type=Path,
        default=Path("reports/week05/final_model_test_metrics.csv"),
    )
    parser.add_argument("--params", type=Path, default=Path("config/params.yaml"))
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--tolerance", type=float, default=1e-10)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_feature_table(
    path: Path,
    feature_columns: list[str],
) -> pd.DataFrame:
    required = {
        *feature_columns,
        "base_time",
        "station_id",
        "rent_count",
        "return_count",
        "is_observed",
        "is_peak",
        "delta_hist_h15",
        "delta_hist_h30",
        "delta_hist_h60",
        "target_h15_valid",
        "target_h30_valid",
        "target_h60_valid",
    }
    available = set(pq.ParquetFile(path).schema.names)
    missing = required - available
    if missing:
        raise ValueError(f"feature table missing columns: {sorted(missing)}")
    columns = list(dict.fromkeys([*feature_columns, *sorted(required)]))
    return pd.read_parquet(path, columns=columns)


def compare_metrics(
    reproduced: pd.DataFrame,
    expected: pd.DataFrame,
    tolerance: float,
) -> tuple[pd.DataFrame, float]:
    keys = ["split", "model_id", "segment", "horizon_min"]
    merged = reproduced.merge(
        expected,
        on=keys,
        suffixes=("_reproduced", "_expected"),
        validate="one_to_one",
    )
    if len(merged) != len(expected) or len(merged) != len(reproduced):
        raise ValueError("reproduced and expected metric rows differ")

    maximum = 0.0
    for column in METRIC_COLUMNS:
        difference = (
            merged[f"{column}_reproduced"] - merged[f"{column}_expected"]
        ).abs()
        merged[f"{column}_absolute_difference"] = difference
        maximum = max(maximum, float(difference.max()))
    merged["within_tolerance"] = True
    for column in METRIC_COLUMNS:
        if column == "evaluated_rows":
            valid = merged[f"{column}_absolute_difference"].eq(0)
        else:
            valid = merged[f"{column}_absolute_difference"].le(tolerance)
        merged["within_tolerance"] &= valid
    return merged, maximum


def main() -> None:
    args = parse_args()
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    params = yaml.safe_load(args.params.read_text(encoding="utf-8"))
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    model_sha = sha256(args.model)
    feature_sha = sha256(args.feature_table)
    expected_model_sha = metadata["model_artifact"]["sha256"]
    expected_feature_sha = metadata["input"]["sha256"]
    if model_sha != expected_model_sha:
        raise ValueError("model SHA-256 does not match metadata")
    if feature_sha != expected_feature_sha:
        raise ValueError("feature SHA-256 does not match metadata")

    candidate = joblib.load(args.model)
    feature_columns = list(candidate.feature_columns)
    if feature_columns != metadata["feature_order"]:
        raise ValueError("model feature order does not match metadata")

    frame = read_feature_table(args.feature_table, feature_columns)
    validate_week03_feature_allowlist(frame, feature_columns)
    split_cfg = params["WEEK04_MODEL_COMPARISON"]["split"]
    split_result = assign_purged_ratio_splits(
        frame,
        train_ratio=float(split_cfg["train_ratio"]),
        validation_ratio=float(split_cfg["validation_ratio"]),
        test_ratio=float(split_cfg["test_ratio"]),
        gap_minutes=int(split_cfg["gap_minutes"]),
    )
    active_stations, active_threshold = active_station_definition(
        split_result.frame,
        percentile=float(params["ACTIVE_STATION"]["percentile"]),
    )
    reproduced = evaluate_fitted_candidate(
        split_result.frame,
        candidate=candidate,
        split="test",
        active_stations=active_stations,
        timing_repeats=5,
    )
    expected = pd.read_csv(args.expected_metrics)
    comparison, maximum = compare_metrics(
        reproduced,
        expected,
        args.tolerance,
    )
    reproduced.to_csv(output_dir / "reproduced_metrics.csv", index=False)
    comparison.to_csv(output_dir / "metric_comparison.csv", index=False)

    summary = {
        "model_sha256": model_sha,
        "feature_table_sha256": feature_sha,
        "feature_order_matches": True,
        "feature_count": len(feature_columns),
        "test_rows": int(split_result.frame["split"].eq("test").sum()),
        "active_station_threshold": active_threshold,
        "active_station_count": len(active_stations),
        "metric_rows": len(comparison),
        "all_rows_within_tolerance": bool(comparison["within_tolerance"].all()),
        "maximum_absolute_difference": maximum,
        "tolerance": args.tolerance,
    }
    (output_dir / "reproduction_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if not summary["all_rows_within_tolerance"]:
        raise SystemExit("reproduced metrics differ from expected metrics")


if __name__ == "__main__":
    main()
