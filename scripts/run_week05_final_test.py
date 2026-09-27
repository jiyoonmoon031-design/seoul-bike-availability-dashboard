from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import joblib
import pandas as pd
import pyarrow.parquet as pq
import yaml

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modeling.feature_engineering import (  # noqa: E402
    get_model_feature_columns,
)
from src.modeling.final_model import (  # noqa: E402
    evaluate_fitted_candidate,
    fit_final_candidate,
)
from src.modeling.model_comparison import (  # noqa: E402
    active_station_definition,
    assign_purged_ratio_splits,
    validate_week03_feature_allowlist,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Week 05 one-time final test evaluation " "for the frozen validation winner"
        )
    )

    parser.add_argument(
        "--input",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--params",
        type=Path,
        default=Path("config/params.yaml"),
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/week05_model_tuning.yaml"),
    )

    parser.add_argument(
        "--selection",
        type=Path,
        default=Path("reports/week05/final_model_selection.json"),
    )

    parser.add_argument(
        "--feature-manifest",
        type=Path,
        default=Path("reports/week03/feature_manifest.csv"),
    )

    parser.add_argument(
        "--confirm-final-test",
        required=True,
        choices=["ONCE"],
    )

    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def git_value(*args: str) -> str | None:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except Exception:
        return None


def expected_features(path: Path) -> list[str]:
    manifest = pd.read_csv(path)

    features = (
        manifest.loc[
            manifest["role"].eq("feature"),
            "column",
        ]
        .astype(str)
        .tolist()
    )

    ordered = get_model_feature_columns(pd.DataFrame(columns=features))

    if set(ordered) != set(features):
        raise ValueError("Week 03 feature manifest and allowlist disagree")

    return ordered


def read_input(
    path: Path,
    features: list[str],
) -> pd.DataFrame:
    required = {
        *features,
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
        raise ValueError(f"input missing columns: {sorted(missing)}")

    ordered = list(dict.fromkeys([*features, *sorted(required - set(features))]))

    return pd.read_parquet(
        path,
        columns=ordered,
    )


def main() -> None:
    args = parse_args()

    input_path = args.input.expanduser().resolve()
    params = yaml.safe_load(args.params.read_text(encoding="utf-8"))
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))

    selection_path = args.selection.resolve()

    report_dir = Path(config["artifacts"]["report_dir"])

    model_dir = Path(config["artifacts"]["model_dir"])

    report_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    model_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    lock_path = report_dir / "final_test_access.json"

    metrics_path = report_dir / "final_model_test_metrics.csv"

    metadata_path = report_dir / "final_model_metadata.json"

    model_path = model_dir / "final_model.joblib"

    feature_path = report_dir / "feature_names.json"

    if lock_path.exists() or metrics_path.exists():
        raise SystemExit(
            "REFUSED: final Week 05 test has already " "been started or completed."
        )

    selection = json.loads(selection_path.read_text(encoding="utf-8"))

    if selection.get("test_targets_accessed") is not False:
        raise SystemExit(
            "REFUSED: selection artifact does not prove " "an untouched test."
        )

    winner = selection["winner"]
    winner_id = winner["model_id"]
    winner_parameters = winner["parameters"]

    seed = int(config["random_seed"])

    feature_columns = expected_features(args.feature_manifest)

    frame = read_input(
        input_path,
        feature_columns,
    )

    feature_columns = validate_week03_feature_allowlist(
        frame,
        feature_columns,
    )

    week04 = params["WEEK04_MODEL_COMPARISON"]
    split_cfg = week04["split"]

    split_result = assign_purged_ratio_splits(
        frame,
        train_ratio=float(split_cfg["train_ratio"]),
        validation_ratio=float(split_cfg["validation_ratio"]),
        test_ratio=float(split_cfg["test_ratio"]),
        gap_minutes=int(split_cfg["gap_minutes"]),
    )

    frame = split_result.frame

    active_stations, active_threshold = active_station_definition(
        frame,
        percentile=float(params["ACTIVE_STATION"]["percentile"]),
    )

    print(
        f"Frozen winner: {winner_id}",
        flush=True,
    )

    print(
        "Refitting on train + validation...",
        flush=True,
    )

    candidate = fit_final_candidate(
        frame,
        model_id=winner_id,
        feature_columns=feature_columns,
        seed=seed,
        parameters=winner_parameters,
    )

    # Save the frozen model before test evaluation.
    joblib.dump(
        candidate,
        model_path,
        compress=3,
    )

    transformed_features = candidate.preprocessor.get_feature_names_out().tolist()

    feature_path.write_text(
        json.dumps(
            {
                "raw_feature_order": feature_columns,
                "transformed_feature_order": transformed_features,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    head = git_value(
        "rev-parse",
        "--short=12",
        "HEAD",
    )

    model_version = f"week05-{winner_id}-{head or 'local'}"

    access_record = {
        "status": "started",
        "accessed_at_utc": datetime.now(UTC).isoformat(),
        "model_id": winner_id,
        "model_version": model_version,
        "selection_sha256": sha256(selection_path),
        "git_head": git_value(
            "rev-parse",
            "HEAD",
        ),
        "policy": ("one final test evaluation only"),
    }

    # From this point onward, reruns are intentionally blocked.
    lock_path.write_text(
        json.dumps(
            access_record,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        "FINAL TEST ACCESS STARTED. " "This run cannot be repeated automatically.",
        flush=True,
    )

    metrics = evaluate_fitted_candidate(
        frame,
        candidate=candidate,
        split="test",
        active_stations=active_stations,
        timing_repeats=5,
    )

    metrics.to_csv(
        metrics_path,
        index=False,
        float_format="%.12g",
    )

    model_sha = sha256(model_path)

    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "model_version": model_version,
        "model_id": winner_id,
        "parameters": winner_parameters,
        "random_seed": seed,
        "refit_splits": [
            "train",
            "validation",
        ],
        "evaluation_split": "test",
        "test_evaluation_count": 1,
        "split": split_result.metadata,
        "active_station_definition": {
            "percentile": float(params["ACTIVE_STATION"]["percentile"]),
            "threshold": active_threshold,
            "station_count": len(active_stations),
            "source": "original train split only",
        },
        "feature_order": feature_columns,
        "training_rows": candidate.training_rows,
        "model_artifact": {
            "path": str(model_path),
            "sha256": model_sha,
            "committed_to_git": False,
        },
        "input": {
            "path": str(input_path),
            "sha256": sha256(input_path),
        },
        "selection_artifact": {
            "path": str(selection_path),
            "sha256": sha256(selection_path),
        },
        "git_head": git_value(
            "rev-parse",
            "HEAD",
        ),
    }

    metadata_path.write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    access_record["status"] = "completed"
    access_record["completed_at_utc"] = datetime.now(UTC).isoformat()
    access_record["metrics_sha256"] = sha256(metrics_path)

    lock_path.write_text(
        json.dumps(
            access_record,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 72)
    print("WEEK 05 FINAL TEST COMPLETE")
    print("=" * 72)

    display = metrics[
        [
            "segment",
            "horizon_min",
            "mae",
            "rmse",
            "b1_mae_same_rows",
            "improvement_vs_b1",
        ]
    ]

    print(display.to_string(index=False))

    print()
    print("MODEL_VERSION:", model_version)
    print("MODEL:", model_path)
    print("MODEL SHA256:", model_sha)
    print("TEST EVALUATIONS: 1")


if __name__ == "__main__":
    main()
