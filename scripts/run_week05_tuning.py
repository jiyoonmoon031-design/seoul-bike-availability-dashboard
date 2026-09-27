from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
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
    build_parameter_trials,
    choose_final_model,
    evaluate_fitted_candidate,
    native_feature_importance,
    permutation_importance_raw,
    sha256_file,
    summarize_finalist,
)
from src.modeling.model_comparison import (  # noqa: E402
    active_station_definition,
    assign_purged_ratio_splits,
    fit_candidate,
    make_estimator,
    make_preprocessor,
    validate_week03_feature_allowlist,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Week 05 validation-only model tuning")
    parser.add_argument("--input", required=True, type=Path)
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
        "--feature-manifest",
        type=Path,
        default=Path("reports/week03/feature_manifest.csv"),
    )
    return parser.parse_args()


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

    names = set(pq.ParquetFile(path).schema.names)
    missing = required - names

    if missing:
        raise ValueError(f"input missing columns: {sorted(missing)}")

    return pd.read_parquet(
        path,
        columns=list(required),
    )


def main() -> None:
    args = parse_args()

    input_path = args.input.expanduser().resolve()
    params = yaml.safe_load(args.params.read_text())
    config = yaml.safe_load(args.config.read_text())

    week04 = params["WEEK04_MODEL_COMPARISON"]
    split_cfg = week04["split"]
    seed = int(config["random_seed"])

    features = expected_features(args.feature_manifest)
    frame = read_input(input_path, features)

    features = validate_week03_feature_allowlist(
        frame,
        features,
    )

    split_result = assign_purged_ratio_splits(
        frame,
        train_ratio=float(split_cfg["train_ratio"]),
        validation_ratio=float(split_cfg["validation_ratio"]),
        test_ratio=float(split_cfg["test_ratio"]),
        gap_minutes=int(split_cfg["gap_minutes"]),
    )

    frame = split_result.frame

    # This is the only explicit safeguard needed during tuning:
    # no test rows are used below.
    train = frame.loc[frame["split"].eq("train")].copy()
    validation = frame.loc[frame["split"].eq("validation")].copy()

    active_stations, active_threshold = active_station_definition(
        frame,
        percentile=float(params["ACTIVE_STATION"]["percentile"]),
    )

    active_peak = (
        validation["station_id"].astype(str).isin(active_stations)
        & validation["is_peak"].astype(bool)
        & validation["target_h30_valid"].astype(bool)
        & validation["delta_hist_h30"].notna()
    )

    if not active_peak.any():
        raise ValueError("ACTIVE_PEAK validation target is empty")

    # RF and LightGBM use the same tree preprocessor.
    preprocessor = make_preprocessor(
        train,
        features,
        "random_forest",
    )

    x_train = np.asarray(
        preprocessor.fit_transform(train[features]),
        dtype=np.float32,
    )
    x_validation = np.asarray(
        preprocessor.transform(validation[features]),
        dtype=np.float32,
    )

    train_mask = (
        train["target_h30_valid"].astype(bool) & train["delta_hist_h30"].notna()
    ).to_numpy()

    y_train = train.loc[
        train_mask,
        "delta_hist_h30",
    ].to_numpy(dtype=np.float64)

    validation_mask = active_peak.to_numpy()
    y_validation = validation.loc[
        active_peak,
        "delta_hist_h30",
    ].to_numpy(dtype=np.float64)

    history: list[dict] = []
    best_params: dict[str, dict] = {}

    for index, model_id in enumerate(("random_forest", "lightgbm")):
        candidate_cfg = config["candidates"][model_id]

        trials = build_parameter_trials(
            fixed=candidate_cfg["fixed"],
            search_space=candidate_cfg["search_space"],
            n_trials=int(config["search"][f"{model_id}_trials"]),
            seed=seed + index,
            baseline_parameters=week04["models"][model_id],
        )

        model_rows: list[dict] = []

        for trial_no, parameters in enumerate(
            trials,
            start=1,
        ):
            print(
                f"{model_id} trial {trial_no}/{len(trials)}",
                flush=True,
            )

            estimator = make_estimator(
                model_id,
                seed=seed,
                parameters=parameters,
            )

            if model_id == "lightgbm":
                names = preprocessor.get_feature_names_out()

                x_fit = pd.DataFrame(
                    x_train,
                    columns=names,
                )
                x_eval = pd.DataFrame(
                    x_validation,
                    columns=names,
                )
            else:
                x_fit = x_train
                x_eval = x_validation

            started = time.perf_counter()

            estimator.fit(
                x_fit[train_mask],
                y_train,
            )

            fit_seconds = time.perf_counter() - started

            prediction = np.asarray(
                estimator.predict(x_eval),
                dtype=np.float64,
            )

            error = prediction[validation_mask] - y_validation

            mae = float(np.mean(np.abs(error)))
            rmse = float(np.sqrt(np.mean(np.square(error))))

            row = {
                "model_id": model_id,
                "trial": trial_no,
                "active_peak_30m_mae": mae,
                "active_peak_30m_rmse": rmse,
                "fit_seconds": fit_seconds,
                "parameters_json": json.dumps(
                    parameters,
                    sort_keys=True,
                ),
            }

            history.append(row)
            model_rows.append(row)

        best = min(
            model_rows,
            key=lambda x: (
                x["active_peak_30m_mae"],
                x["trial"],
            ),
        )

        best_params[model_id] = json.loads(best["parameters_json"])

    report_dir = Path(config["artifacts"]["report_dir"])
    report_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    pd.DataFrame(history).to_csv(
        report_dir / "tuning_history.csv",
        index=False,
    )

    finalists = {}
    finalist_metrics = []
    summaries = []

    for model_id in (
        "random_forest",
        "lightgbm",
    ):
        candidate = fit_candidate(
            frame,
            model_id=model_id,
            feature_columns=features,
            seed=seed,
            parameters=best_params[model_id],
        )

        finalists[model_id] = candidate

        metrics = evaluate_fitted_candidate(
            frame,
            candidate=candidate,
            split="validation",
            active_stations=active_stations,
            timing_repeats=5,
        )

        finalist_metrics.append(metrics)

        summaries.append(
            summarize_finalist(
                metrics,
                model_id=model_id,
                parameters=best_params[model_id],
            )
        )

    all_metrics = pd.concat(
        finalist_metrics,
        ignore_index=True,
    )

    all_metrics.to_csv(
        report_dir / "finalists_validation_metrics.csv",
        index=False,
    )

    winner = choose_final_model(
        summaries,
        preferred_inference_max=float(config["selection"]["tertiary"]["preferred_max"]),
    )

    winner_id = winner["model_id"]
    winner_candidate = finalists[winner_id]

    validation_only = frame.loc[frame["split"].eq("validation")].copy()

    native = native_feature_importance(winner_candidate)

    permutation = permutation_importance_raw(
        winner_candidate,
        validation_only,
        active_stations=active_stations,
        repeats=int(config["importance"]["permutation_repeats"]),
        seed=seed,
    )

    importance = native.merge(
        permutation,
        how="outer",
        on="feature",
    )

    importance = importance.sort_values(
        [
            "permutation_mae_increase",
            "native_importance",
        ],
        ascending=False,
    )

    importance.to_csv(
        report_dir / "feature_importance.csv",
        index=False,
    )

    selection = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "winner": winner,
        "finalists": summaries,
        "best_parameters": best_params,
        "selection_policy": config["selection"],
        "split": split_result.metadata,
        "active_station_percentile": float(params["ACTIVE_STATION"]["percentile"]),
        "active_station_threshold": active_threshold,
        "active_station_count": len(active_stations),
        "feature_order": features,
        "input": {
            "path": str(input_path),
            "sha256": sha256_file(input_path),
        },
        "test_targets_accessed": False,
        "test_metrics_generated": False,
        "final_test_policy": ("reserved for one final Week 05 evaluation"),
    }

    (report_dir / "final_model_selection.json").write_text(
        json.dumps(
            selection,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 70)
    print("WEEK 05 VALIDATION TUNING COMPLETE")
    print("=" * 70)

    print(pd.DataFrame(summaries).drop(columns=["parameters"]).to_string(index=False))

    print()
    print("WINNER:", winner_id)
    print(
        "ACTIVE_PEAK 30m MAE:",
        winner["primary_active_peak_30m_mae"],
    )
    print(
        "ALL mean MAE:",
        winner["secondary_all_horizon_mean_mae"],
    )
    print(
        "Inference ms/1k:",
        winner["inference_time_ms_per_1k_rows"],
    )

    print()
    print("TEST ACCESSED: False")
    print("Next step: review validation result, " "then run the one-time final test.")


if __name__ == "__main__":
    main()
