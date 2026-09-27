from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
from sklearn.model_selection import ParameterSampler

from src.modeling.feature_engineering import HORIZONS
from src.modeling.model_comparison import (
    FittedCandidate,
    active_station_definition,
    segment_mask,
)

SEGMENTS = ("ALL", "ACTIVE", "PEAK", "ACTIVE_PEAK")


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_parameter_trials(
    *,
    fixed: Mapping[str, Any],
    search_space: Mapping[str, list[Any]],
    n_trials: int,
    seed: int,
    baseline_parameters: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return deterministic unique parameter trials.

    The Week 04 configuration is inserted first so Week 05 tuning can never
    silently discard the previously measured reference configuration.
    """
    if n_trials < 1:
        raise ValueError("n_trials must be >= 1")

    trials: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(parameters: Mapping[str, Any]) -> None:
        merged = dict(fixed)
        merged.update(parameters)
        merged = _jsonable(merged)
        key = json.dumps(merged, sort_keys=True)
        if key not in seen:
            seen.add(key)
            trials.append(merged)

    if baseline_parameters:
        add(baseline_parameters)

    remaining = max(n_trials - len(trials), 0)

    if remaining:
        possible = 1
        for values in search_space.values():
            possible *= len(values)

        sampled = ParameterSampler(
            dict(search_space),
            n_iter=min(max(remaining * 3, remaining), possible),
            random_state=seed,
        )

        for params in sampled:
            add(params)
            if len(trials) >= n_trials:
                break

    return trials[:n_trials]


def evaluate_fitted_candidate(
    frame: pd.DataFrame,
    *,
    candidate: FittedCandidate,
    split: str,
    active_stations: set[str],
    timing_repeats: int = 5,
) -> pd.DataFrame:
    """Evaluate one fitted candidate without fitting or reading another split."""
    evaluation = frame.loc[frame["split"].eq(split)].copy()
    if evaluation.empty:
        raise ValueError(f"{split} split is empty")

    predictions = candidate.predict_all(evaluation)

    sample_rows = min(1000, len(evaluation))
    sample_positions = np.linspace(
        0,
        len(evaluation) - 1,
        num=sample_rows,
        dtype=np.int64,
    )
    sample = evaluation.iloc[sample_positions].copy()

    candidate.predict_all(sample)
    timings: list[float] = []

    for _ in range(timing_repeats):
        start = time.perf_counter()
        candidate.predict_all(sample)
        timings.append(time.perf_counter() - start)

    inference_ms = float(np.median(timings) * 1000 * (1000 / len(sample)))

    rows: list[dict[str, Any]] = []

    for segment in SEGMENTS:
        in_segment = segment_mask(evaluation, segment, active_stations)

        for horizon in HORIZONS:
            target_col = f"delta_hist_h{horizon}"
            valid_col = f"target_h{horizon}_valid"

            pred = predictions[horizon]

            eligible = (
                in_segment.to_numpy()
                & evaluation[valid_col].astype(bool).to_numpy()
                & evaluation[target_col].notna().to_numpy()
                & np.isfinite(pred)
            )

            target = evaluation[target_col].to_numpy(dtype=np.float64)

            if eligible.any():
                error = pred[eligible] - target[eligible]
                mae = float(np.mean(np.abs(error)))
                rmse = float(np.sqrt(np.mean(np.square(error))))
                b1_mae = float(np.mean(np.abs(target[eligible])))
                improvement = float((b1_mae - mae) / b1_mae) if b1_mae > 0 else np.nan
            else:
                mae = rmse = b1_mae = improvement = np.nan

            rows.append(
                {
                    "split": split,
                    "model_id": candidate.model_id,
                    "segment": segment,
                    "horizon_min": horizon,
                    "evaluated_rows": int(eligible.sum()),
                    "mae": mae,
                    "rmse": rmse,
                    "b1_mae_same_rows": b1_mae,
                    "improvement_vs_b1": improvement,
                    "inference_time_ms_per_1k_rows": inference_ms,
                }
            )

    return pd.DataFrame(rows)


def summarize_finalist(
    metrics: pd.DataFrame,
    *,
    model_id: str,
    parameters: Mapping[str, Any],
) -> dict[str, Any]:
    primary = metrics.loc[
        metrics["segment"].eq("ACTIVE_PEAK") & metrics["horizon_min"].eq(30),
        "mae",
    ]

    if len(primary) != 1:
        raise ValueError("ACTIVE_PEAK 30m metric must exist exactly once")

    all_segment = metrics.loc[
        metrics["segment"].eq("ALL"),
        "mae",
    ]

    inference = metrics["inference_time_ms_per_1k_rows"].dropna()

    return {
        "model_id": model_id,
        "parameters": _jsonable(dict(parameters)),
        "primary_active_peak_30m_mae": float(primary.iloc[0]),
        "secondary_all_horizon_mean_mae": float(all_segment.mean()),
        "inference_time_ms_per_1k_rows": float(inference.iloc[0]),
    }


def choose_final_model(
    finalists: list[dict[str, Any]],
    *,
    preferred_inference_max: float,
) -> dict[str, Any]:
    if not finalists:
        raise ValueError("no finalists")

    complexity = {
        "random_forest": 1,
        "lightgbm": 2,
    }

    def key(item: dict[str, Any]) -> tuple[Any, ...]:
        return (
            item["primary_active_peak_30m_mae"],
            item["secondary_all_horizon_mean_mae"],
            item["inference_time_ms_per_1k_rows"],
            complexity.get(item["model_id"], 999),
        )

    winner = min(finalists, key=key).copy()
    winner["preferred_inference_max_ms_per_1k_rows"] = preferred_inference_max
    winner["inference_preference_met"] = (
        winner["inference_time_ms_per_1k_rows"] <= preferred_inference_max
    )
    return winner


def native_feature_importance(
    candidate: FittedCandidate,
) -> pd.DataFrame:
    names = list(candidate.preprocessor.get_feature_names_out())
    per_horizon: list[np.ndarray] = []

    for horizon in HORIZONS:
        estimator = candidate.estimators[horizon]

        if candidate.model_id == "lightgbm" and hasattr(estimator, "booster_"):
            values = np.asarray(
                estimator.booster_.feature_importance(importance_type="gain"),
                dtype=np.float64,
            )
            method = "gain"
        elif hasattr(estimator, "feature_importances_"):
            values = np.asarray(
                estimator.feature_importances_,
                dtype=np.float64,
            )
            method = "native_impurity"
        else:
            raise ValueError(
                f"native feature importance unavailable for " f"{candidate.model_id}"
            )

        total = values.sum()
        if total > 0:
            values = values / total

        per_horizon.append(values)

    average = np.mean(np.vstack(per_horizon), axis=0)

    return (
        pd.DataFrame(
            {
                "feature": names,
                "native_importance": average,
                "native_method": method,
            }
        )
        .sort_values("native_importance", ascending=False)
        .reset_index(drop=True)
    )


def permutation_importance_raw(
    candidate: FittedCandidate,
    validation: pd.DataFrame,
    *,
    active_stations: set[str],
    repeats: int,
    seed: int,
    max_rows: int = 20000,
) -> pd.DataFrame:
    """Raw-feature permutation importance on validation ACTIVE∩PEAK, 30m."""
    in_segment = segment_mask(
        validation,
        "ACTIVE_PEAK",
        active_stations,
    )

    valid = (
        in_segment
        & validation["target_h30_valid"].astype(bool)
        & validation["delta_hist_h30"].notna()
    )

    sample = validation.loc[valid].copy()

    if sample.empty:
        raise ValueError("no ACTIVE_PEAK validation rows for importance")

    if len(sample) > max_rows:
        positions = np.linspace(
            0,
            len(sample) - 1,
            num=max_rows,
            dtype=np.int64,
        )
        sample = sample.iloc[positions].copy()

    target = sample["delta_hist_h30"].to_numpy(dtype=np.float64)
    baseline_prediction = candidate.predict_all(sample)[30]
    baseline_mae = float(np.mean(np.abs(baseline_prediction - target)))

    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []

    for feature in candidate.feature_columns:
        increases: list[float] = []

        original = sample[feature].to_numpy(copy=True)

        for _ in range(repeats):
            permuted = sample.copy()
            permuted[feature] = rng.permutation(original)

            prediction = candidate.predict_all(permuted)[30]
            mae = float(np.mean(np.abs(prediction - target)))
            increases.append(mae - baseline_mae)

        rows.append(
            {
                "feature": feature,
                "permutation_mae_increase": float(np.mean(increases)),
                "permutation_std": float(np.std(increases)),
                "baseline_mae": baseline_mae,
                "sample_rows": len(sample),
                "segment": "ACTIVE_PEAK",
                "horizon_min": 30,
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values(
            "permutation_mae_increase",
            ascending=False,
        )
        .reset_index(drop=True)
    )


def fit_final_candidate(
    frame: pd.DataFrame,
    *,
    model_id: str,
    feature_columns: list[str],
    seed: int,
    parameters: Mapping[str, Any],
) -> FittedCandidate:
    """Refit the frozen winner on train + validation, excluding purge gaps/test."""
    from src.modeling.model_comparison import (
        make_estimator,
        make_preprocessor,
    )

    fit_frame = frame.loc[frame["split"].isin(["train", "validation"])].copy()

    if fit_frame.empty:
        raise ValueError("train + validation refit frame is empty")

    preprocessor = make_preprocessor(
        fit_frame,
        feature_columns,
        model_id,
    )

    transformed = preprocessor.fit_transform(fit_frame[feature_columns])

    if model_id != "linear_model":
        transformed = np.asarray(
            transformed,
            dtype=np.float32,
        )

    if model_id == "lightgbm":
        transformed = pd.DataFrame(
            transformed,
            columns=preprocessor.get_feature_names_out(),
        )

    estimators: dict[int, Any] = {}
    training_rows: dict[int, int] = {}

    for horizon in HORIZONS:
        valid_column = f"target_h{horizon}_valid"
        target_column = f"delta_hist_h{horizon}"

        mask = (
            fit_frame[valid_column].astype(bool) & fit_frame[target_column].notna()
        ).to_numpy()

        if not mask.any():
            raise ValueError(f"no valid refit targets for {horizon}m")

        estimator = make_estimator(
            model_id,
            seed=seed,
            parameters=parameters,
        )

        target = fit_frame.loc[
            mask,
            target_column,
        ].to_numpy(dtype=np.float64)

        estimator.fit(
            transformed[mask],
            target,
        )

        estimators[horizon] = estimator
        training_rows[horizon] = int(mask.sum())

    return FittedCandidate(
        model_id=model_id,
        feature_columns=list(feature_columns),
        preprocessor=preprocessor,
        estimators=estimators,
        training_rows=training_rows,
    )
