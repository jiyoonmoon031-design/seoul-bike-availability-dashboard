from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.modeling.feature_engineering import (  # noqa: E402
    HORIZONS,
    build_feature_manifest,
    build_week03_features,
    get_model_feature_columns,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build leakage-safe Week 03 model features."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Week 02 trip_targets_weather_15_30_60.parquet",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output feature-table parquet path",
    )
    parser.add_argument(
        "--manifest-output",
        type=Path,
        help="Column-role manifest CSV (default: beside output)",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        help="Build summary JSON (default: beside output)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = args.input.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    manifest_path = (
        args.manifest_output.expanduser().resolve()
        if args.manifest_output
        else output_path.with_suffix(".manifest.csv")
    )
    summary_path = (
        args.summary_output.expanduser().resolve()
        if args.summary_output
        else output_path.with_suffix(".summary.json")
    )

    source = pd.read_parquet(input_path)
    features = build_week03_features(source)
    manifest = build_feature_manifest(features)
    model_features = get_model_feature_columns(features)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(output_path, index=False)
    manifest.to_csv(manifest_path, index=False)

    summary = {
        "input": str(input_path),
        "output": str(output_path),
        "rows": len(features),
        "stations": int(features["station_id"].nunique()),
        "start": features["base_time"].min().isoformat(),
        "end": features["base_time"].max().isoformat(),
        "observed_rows": int(features["is_observed"].sum()),
        "unobserved_rows": int((~features["is_observed"]).sum()),
        "model_feature_count": len(model_features),
        "model_features": model_features,
        "valid_target_rows": {
            str(horizon): int(features[f"target_h{horizon}_valid"].sum())
            for horizon in HORIZONS
        },
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Manifest: {manifest_path}")
    print(f"Summary : {summary_path}")


if __name__ == "__main__":
    main()
