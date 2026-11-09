from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import joblib
import numpy as np
import pandas as pd

from src.modeling.feature_engineering import HORIZONS
from src.modeling.model_comparison import (
    GROUP_COLUMNS,
    assign_purged_ratio_splits,
    fit_baselines,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the Week 11 train-only B3 fallback "
            "baseline artifact."
        )
    )

    parser.add_argument(
        "--feature-table",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "models/week11/fallback_baselines.joblib"
        ),
    )

    parser.add_argument(
        "--metadata-output",
        type=Path,
        default=Path(
            "reports/week11/fallback_baseline_metadata.json"
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    feature_path = args.feature_table.expanduser().resolve()

    if not feature_path.exists():
        raise FileNotFoundError(
            f"feature table not found: {feature_path}"
        )

    columns = [
        "station_id",
        "base_time",
        *GROUP_COLUMNS[1:],
    ]

    for horizon in HORIZONS:
        columns.extend(
            [
                f"delta_hist_h{horizon}",
                f"target_h{horizon}_valid",
            ]
        )

    # Remove duplicates while preserving order.
    columns = list(dict.fromkeys(columns))

    frame = pd.read_parquet(
        feature_path,
        columns=columns,
    )

    split_result = assign_purged_ratio_splits(frame)

    baselines = fit_baselines(split_result.frame)

    validation = {}

    for horizon in HORIZONS:
        group_mean = baselines.group_means[horizon]
        global_mean = baselines.global_means[horizon]

        if group_mean.empty:
            raise RuntimeError(
                f"B3 {horizon}m group lookup is empty"
            )

        if not np.isfinite(global_mean):
            raise RuntimeError(
                f"B3 {horizon}m global mean is non-finite"
            )

        validation[str(horizon)] = {
            "group_count": int(len(group_mean)),
            "global_mean": float(global_mean),
        }

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.metadata_output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        baselines,
        args.output,
    )

    metadata = {
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "baseline_id": "b3_dow_time_mean",
        "fallback_chain": [
            "primary_model",
            "b3_dow_time_mean",
            "b1_persistence",
        ],
        "group_columns": list(GROUP_COLUMNS),
        "horizons": [
            int(value)
            for value in HORIZONS
        ],
        "training_policy": (
            "original chronological train split only"
        ),
        "feature_table": {
            "path": str(feature_path),
            "sha256": sha256_file(feature_path),
        },
        "artifact": {
            "path": str(args.output),
            "sha256": sha256_file(args.output),
            "committed_to_git": False,
        },
        "validation": validation,
        "split": split_result.metadata,
    }

    args.metadata_output.write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "metadata": str(args.metadata_output),
                "validation": validation,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
