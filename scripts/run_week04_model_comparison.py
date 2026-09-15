from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq
import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.modeling.feature_engineering import (  # noqa: E402
    HORIZONS,
    get_model_feature_columns,
)
from src.modeling.model_comparison import (  # noqa: E402
    BASELINE_IDS,
    MODEL_CANDIDATES,
    MODEL_DISPLAY_NAMES,
    assign_purged_ratio_splits,
    evaluate_validation_comparison,
    fit_baselines,
    fit_candidate,
    make_wide_comparison_table,
    validate_week03_feature_allowlist,
)

IMPLEMENTATION_PATHS = (
    Path("src/modeling/model_comparison.py"),
    Path("scripts/run_week04_model_comparison.py"),
    Path("config/params.yaml"),
    Path("requirements.txt"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Train Week 04 candidates and create a validation-only comparison. "
            "The final test split is reserved for Week 05."
        )
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--params", type=Path, default=Path("config/params.yaml"))
    parser.add_argument(
        "--feature-manifest",
        type=Path,
        default=Path("reports/week03/feature_manifest.csv"),
    )
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=Path("reports/week04/model_comparison_metrics.csv"),
    )
    parser.add_argument(
        "--comparison-output",
        type=Path,
        default=Path("reports/week04/model_comparison_table.csv"),
    )
    parser.add_argument(
        "--metadata-output",
        type=Path,
        default=Path("reports/week04/run_metadata.json"),
    )
    parser.add_argument(
        "--predictions-output",
        type=Path,
        help=(
            "Optional uncommitted validation parquet for Kim Suyeon's separate "
            "error-distribution analysis"
        ),
    )
    return parser.parse_args()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_value(*arguments: str) -> str | None:
    try:
        return subprocess.run(
            ["git", *arguments],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _dependency_versions() -> dict[str, str]:
    packages = ("numpy", "pandas", "pyarrow", "scikit-learn", "lightgbm", "PyYAML")
    versions: dict[str, str] = {}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not-installed"
    return versions


def _expected_features(manifest_path: Path) -> list[str]:
    manifest = pd.read_csv(manifest_path)
    required = {"column", "role"}
    if not required <= set(manifest.columns):
        raise ValueError("Week 03 feature manifest must contain column and role")
    manifest_features = (
        manifest.loc[manifest["role"].eq("feature"), "column"].astype(str).tolist()
    )
    # The Week 03 manifest preserves source parquet order.  Model order is the
    # canonical order returned by get_model_feature_columns(), also recorded in
    # the Week 03 build summary.  Use the manifest for role/inclusion checks and
    # the shared function for ordering.
    ordered = get_model_feature_columns(pd.DataFrame(columns=manifest_features))
    if set(ordered) != set(manifest_features):
        raise ValueError("Week 03 manifest and feature allowlist disagree")
    return ordered


def _read_input(input_path: Path, expected_features: list[str]) -> pd.DataFrame:
    required = {
        *expected_features,
        "base_time",
        "rent_count",
        "return_count",
        "is_observed",
        "is_peak",
    }
    for horizon in HORIZONS:
        required.update({f"delta_hist_h{horizon}", f"target_h{horizon}_valid"})
    available = set(pq.ParquetFile(input_path).schema.names)
    missing = required - available
    if missing:
        raise ValueError(f"input parquet is missing columns: {sorted(missing)}")
    ordered = list(
        dict.fromkeys([*expected_features, *sorted(required - set(expected_features))])
    )
    return pd.read_parquet(input_path, columns=ordered)


def _implementation_hashes() -> dict[str, str]:
    return {str(path): _sha256(REPOSITORY_ROOT / path) for path in IMPLEMENTATION_PATHS}


def _implementation_dirty() -> bool:
    status = _git_value(
        "status",
        "--porcelain",
        "--",
        *(str(path) for path in IMPLEMENTATION_PATHS),
    )
    return bool(status)


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPOSITORY_ROOT))
    except ValueError:
        return str(path)


def _write_predictions(
    path: Path,
    frame: pd.DataFrame,
    baselines: Any,
    candidates: dict[str, Any],
) -> None:
    validation = frame.loc[frame["split"].eq("validation")].copy()
    output = validation[
        [
            "station_id",
            "base_time",
            "district",
            "is_peak",
            *[f"delta_hist_h{horizon}" for horizon in HORIZONS],
            *[f"target_h{horizon}_valid" for horizon in HORIZONS],
        ]
    ].copy()
    for baseline_id in BASELINE_IDS:
        predictions = baselines.predict_all(validation, baseline_id)
        for horizon, values in predictions.items():
            output[f"prediction_{baseline_id}_h{horizon}"] = values
    for model_id, candidate in candidates.items():
        predictions = candidate.predict_all(validation)
        for horizon, values in predictions.items():
            output[f"prediction_{model_id}_h{horizon}"] = values
    path.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(path, index=False)


def main() -> None:
    args = parse_args()
    input_path = args.input.expanduser().resolve()
    params_path = args.params.expanduser().resolve()
    manifest_path = args.feature_manifest.expanduser().resolve()
    params = yaml.safe_load(params_path.read_text(encoding="utf-8"))
    config = params["WEEK04_MODEL_COMPARISON"]
    split_config = config["split"]
    seed = int(config["seed"])

    expected_features = _expected_features(manifest_path)
    print(f"Reading Week 03 feature table: {input_path}", flush=True)
    frame = _read_input(input_path, expected_features)
    feature_columns = validate_week03_feature_allowlist(frame, expected_features)
    print(
        f"Loaded {len(frame):,} rows with {len(feature_columns)} ordered features",
        flush=True,
    )

    split_result = assign_purged_ratio_splits(
        frame,
        train_ratio=float(split_config["train_ratio"]),
        validation_ratio=float(split_config["validation_ratio"]),
        test_ratio=float(split_config["test_ratio"]),
        gap_minutes=int(split_config["gap_minutes"]),
    )
    frame = split_result.frame
    print(
        "Split rows: " + json.dumps(split_result.metadata["row_counts"]),
        flush=True,
    )

    baselines = fit_baselines(frame)
    candidates = {}
    for model_id in MODEL_CANDIDATES:
        print(f"Training {MODEL_DISPLAY_NAMES[model_id]}...", flush=True)
        candidate = fit_candidate(
            frame,
            model_id=model_id,
            feature_columns=feature_columns,
            seed=seed,
            parameters=config["models"][model_id],
        )
        candidates[model_id] = candidate
        print(
            f"Finished {MODEL_DISPLAY_NAMES[model_id]}: "
            + json.dumps(candidate.training_rows),
            flush=True,
        )

    metrics, evaluation_metadata = evaluate_validation_comparison(
        frame,
        baselines=baselines,
        candidates=candidates,
        active_percentile=float(params["ACTIVE_STATION"]["percentile"]),
        timing_repeats=int(config["inference_timing_repeats"]),
    )
    comparison = make_wide_comparison_table(metrics)

    metrics_path = args.metrics_output.expanduser().resolve()
    comparison_path = args.comparison_output.expanduser().resolve()
    metadata_path = args.metadata_output.expanduser().resolve()
    for path in (metrics_path, comparison_path, metadata_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(metrics_path, index=False, float_format="%.12g")
    comparison.to_csv(comparison_path, index=False, float_format="%.12g")

    if args.predictions_output:
        prediction_path = args.predictions_output.expanduser().resolve()
        _write_predictions(prediction_path, frame, baselines, candidates)
        print(f"Validation predictions: {prediction_path}", flush=True)

    head = _git_value("rev-parse", "HEAD")
    implementation_dirty = _implementation_dirty()
    metadata = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "week": 4,
        "owner": "Moon Jiyoon",
        "related_issue": 49,
        "evaluation_policy": evaluation_metadata,
        "split": split_result.metadata,
        "seed": seed,
        "horizons_minutes": list(HORIZONS),
        "feature_contract": {
            "source": "Week 03 get_model_feature_columns() and feature_manifest.csv",
            "count": len(feature_columns),
            "ordered_columns": feature_columns,
        },
        "baseline_definitions": {
            "b1_persistence": "zero future net change",
            "b2_recent_mean": (
                "complete previous 60-minute net change scaled to each horizon"
            ),
            "b3_dow_time_mean": (
                "train-only station × weekday × hour × minute target mean; "
                "train global-mean fallback"
            ),
        },
        "models": {
            model_id: {
                "display_name": MODEL_DISPLAY_NAMES[model_id],
                "parameters": config["models"][model_id],
                "training_rows_by_horizon": candidates[model_id].training_rows,
                "preprocessing_fit_split": "train only",
            }
            for model_id in MODEL_CANDIDATES
        },
        "input": {
            "filename": input_path.name,
            "sha256": _sha256(input_path),
            "rows": len(frame),
            "stations": int(frame["station_id"].nunique()),
            "period_start": pd.Timestamp(frame["base_time"].min()).isoformat(),
            "period_end": pd.Timestamp(frame["base_time"].max()).isoformat(),
        },
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "dependency_versions": _dependency_versions(),
        },
        "repository": {
            "head_at_run": head,
            "implementation_files_dirty_at_run": implementation_dirty,
            "implementation_file_sha256": _implementation_hashes(),
        },
        "outputs": {
            "long_metrics": {
                "path": _display_path(metrics_path),
                "sha256": _sha256(metrics_path),
            },
            "comparison_table": {
                "path": _display_path(comparison_path),
                "sha256": _sha256(comparison_path),
            },
        },
        "reproduction_tolerance": {
            "metric": "MAE",
            "decimal_places": 3,
            "comparison_split": "validation",
        },
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(comparison.to_string(index=False), flush=True)
    print(f"Long metrics: {metrics_path}", flush=True)
    print(f"Comparison : {comparison_path}", flush=True)
    print(f"Run metadata: {metadata_path}", flush=True)
    print("Final test metrics were not generated (reserved for Week 05).", flush=True)


if __name__ == "__main__":
    main()
