"""Leakage-safe Week 04 forecasting model comparison.

The module consumes the enriched Week 03 feature table, keeps its ordered
feature allowlist, creates one purged chronological split for every model, and
evaluates validation predictions only.  The final test period is labelled for
the Week 05 handoff but its targets are never evaluated here.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from .feature_engineering import (
    BASE_INTERVAL_MIN,
    HORIZONS,
    FeatureContractError,
    get_model_feature_columns,
)
from .naive_baseline import SEGMENTS

MODEL_DISPLAY_NAMES = {
    "b1_persistence": "B1 Persistence (zero delta)",
    "b2_recent_mean": "B2 Recent 60m mean",
    "b3_dow_time_mean": "B3 Train DOW-time mean",
    "linear_model": "Linear Model",
    "random_forest": "Random Forest",
    "lightgbm": "LightGBM",
}
MODEL_CANDIDATES = ("linear_model", "random_forest", "lightgbm")
BASELINE_IDS = ("b1_persistence", "b2_recent_mean", "b3_dow_time_mean")
GROUP_COLUMNS = ("station_id", "weekday_index", "hour", "minute")


@dataclass(frozen=True)
class SplitResult:
    """A split-assigned frame and JSON-serializable split metadata."""

    frame: pd.DataFrame
    metadata: dict[str, Any]


@dataclass
class FittedCandidate:
    """A shared train-only preprocessor and one estimator per horizon."""

    model_id: str
    feature_columns: list[str]
    preprocessor: ColumnTransformer
    estimators: dict[int, BaseEstimator]
    training_rows: dict[int, int]

    def predict_all(self, frame: pd.DataFrame) -> dict[int, np.ndarray]:
        """Predict all horizons after one ordered feature transformation."""

        transformed = self.preprocessor.transform(frame[self.feature_columns])
        if self.model_id == "lightgbm":
            transformed = pd.DataFrame(
                np.asarray(transformed, dtype=np.float32),
                columns=self.preprocessor.get_feature_names_out(),
            )
        return {
            horizon: np.asarray(estimator.predict(transformed), dtype=np.float64)
            for horizon, estimator in self.estimators.items()
        }


@dataclass
class FittedBaselines:
    """Train-only state needed by the three pre-registered naive baselines."""

    group_means: dict[int, pd.Series]
    global_means: dict[int, float]

    def predict_all(
        self, frame: pd.DataFrame, baseline_id: str
    ) -> dict[int, np.ndarray]:
        """Return baseline predictions without reading evaluation targets."""

        if baseline_id == "b1_persistence":
            return {
                horizon: np.zeros(len(frame), dtype=np.float64) for horizon in HORIZONS
            }

        if baseline_id == "b2_recent_mean":
            if "delta_prev_60m" not in frame:
                raise FeatureContractError("delta_prev_60m is required for B2")
            recent_delta = pd.to_numeric(
                frame["delta_prev_60m"], errors="coerce"
            ).to_numpy(dtype=np.float64)
            return {horizon: recent_delta * (horizon / 60.0) for horizon in HORIZONS}

        if baseline_id == "b3_dow_time_mean":
            missing = set(GROUP_COLUMNS) - set(frame.columns)
            if missing:
                raise FeatureContractError(
                    f"missing B3 grouping columns: {sorted(missing)}"
                )
            index = pd.MultiIndex.from_frame(frame[list(GROUP_COLUMNS)])
            return {
                horizon: self.group_means[horizon]
                .reindex(index)
                .fillna(self.global_means[horizon])
                .to_numpy(dtype=np.float64)
                for horizon in HORIZONS
            }

        raise ValueError(f"unknown baseline: {baseline_id}")


def _serialize_timestamp(value: pd.Timestamp) -> str:
    return pd.Timestamp(value).isoformat()


def _range_metadata(values: pd.DatetimeIndex) -> dict[str, Any]:
    if len(values) == 0:
        return {"start": None, "end": None, "timestamps": 0}
    return {
        "start": _serialize_timestamp(values[0]),
        "end": _serialize_timestamp(values[-1]),
        "timestamps": len(values),
    }


def assign_purged_ratio_splits(
    frame: pd.DataFrame,
    *,
    train_ratio: float = 0.70,
    validation_ratio: float = 0.15,
    test_ratio: float = 0.15,
    gap_minutes: int = 60,
) -> SplitResult:
    """Assign one chronological 70/15/15 split with two purge gaps.

    Ratios apply to retained unique 15-minute timestamps after removing the two
    purge gaps.  Every station at a timestamp receives the same split label.
    The split uses timestamps rather than row positions, so station population
    changes cannot place the same time in two partitions.
    """

    if "base_time" not in frame:
        raise FeatureContractError("base_time is required for chronological splits")
    ratios = np.asarray([train_ratio, validation_ratio, test_ratio], dtype=float)
    if (ratios <= 0).any() or not math.isclose(float(ratios.sum()), 1.0, abs_tol=1e-9):
        raise ValueError("train/validation/test ratios must be positive and sum to 1")
    if gap_minutes <= 0 or gap_minutes % BASE_INTERVAL_MIN:
        raise ValueError("gap_minutes must be a positive multiple of 15")

    result = frame.copy()
    result["base_time"] = pd.to_datetime(result["base_time"], errors="coerce")
    if result["base_time"].isna().any():
        raise FeatureContractError("base_time contains invalid timestamps")

    timestamps = pd.DatetimeIndex(result["base_time"].drop_duplicates()).sort_values()
    if len(timestamps) > 1:
        cadence = timestamps.to_series().diff().dropna()
        if cadence.min() < pd.Timedelta(minutes=BASE_INTERVAL_MIN):
            raise FeatureContractError("base_time cadence is finer than 15 minutes")

    gap_steps = gap_minutes // BASE_INTERVAL_MIN
    retained = len(timestamps) - 2 * gap_steps
    if retained < 3:
        raise FeatureContractError("not enough timestamps for purged ratio splits")

    train_size = int(math.floor(retained * train_ratio))
    validation_size = int(math.floor(retained * validation_ratio))
    test_size = retained - train_size - validation_size
    if min(train_size, validation_size, test_size) <= 0:
        raise FeatureContractError("a chronological split would be empty")

    train_end = train_size
    first_gap_end = train_end + gap_steps
    validation_end = first_gap_end + validation_size
    second_gap_end = validation_end + gap_steps

    train_times = timestamps[:train_end]
    first_gap_times = timestamps[train_end:first_gap_end]
    validation_times = timestamps[first_gap_end:validation_end]
    second_gap_times = timestamps[validation_end:second_gap_end]
    test_times = timestamps[second_gap_end:]

    result["split"] = "excluded_gap"
    result.loc[result["base_time"].isin(train_times), "split"] = "train"
    result.loc[result["base_time"].isin(validation_times), "split"] = "validation"
    result.loc[result["base_time"].isin(test_times), "split"] = "test"

    retained_actual = len(train_times) + len(validation_times) + len(test_times)
    metadata = {
        "strategy": "chronological_unique_timestamp_ratio_with_purge",
        "requested_ratios": {
            "train": train_ratio,
            "validation": validation_ratio,
            "test": test_ratio,
        },
        "actual_retained_timestamp_ratios": {
            "train": len(train_times) / retained_actual,
            "validation": len(validation_times) / retained_actual,
            "test": len(test_times) / retained_actual,
        },
        "base_interval_minutes": BASE_INTERVAL_MIN,
        "gap_minutes": gap_minutes,
        "gap_timestamps_each_boundary": gap_steps,
        "data_period": _range_metadata(timestamps),
        "train": _range_metadata(train_times),
        "train_validation_gap": _range_metadata(first_gap_times),
        "validation": _range_metadata(validation_times),
        "validation_test_gap": _range_metadata(second_gap_times),
        "test": _range_metadata(test_times),
        "row_counts": {
            label: int(result["split"].eq(label).sum())
            for label in ("train", "validation", "test", "excluded_gap")
        },
    }
    return SplitResult(frame=result, metadata=metadata)


def validate_week03_feature_allowlist(
    frame: pd.DataFrame, expected_features: Iterable[str] | None = None
) -> list[str]:
    """Return and optionally verify the exact ordered Week 03 feature list."""

    feature_columns = get_model_feature_columns(frame)
    if not feature_columns:
        raise FeatureContractError("the Week 03 feature allowlist is empty")
    missing = set(feature_columns) - set(frame.columns)
    if missing:
        raise FeatureContractError(f"missing Week 03 features: {sorted(missing)}")

    if expected_features is not None:
        expected = list(expected_features)
        if feature_columns != expected:
            raise FeatureContractError(
                "input feature order differs from the saved Week 03 manifest"
            )
    return feature_columns


def _column_groups(
    frame: pd.DataFrame, feature_columns: list[str]
) -> tuple[list[str], list[str]]:
    categorical = [
        column
        for column in feature_columns
        if column in {"station_id", "district"}
        or isinstance(frame[column].dtype, pd.StringDtype)
        or pd.api.types.is_object_dtype(frame[column].dtype)
        or isinstance(frame[column].dtype, pd.CategoricalDtype)
    ]
    numeric = [column for column in feature_columns if column not in categorical]
    if not numeric:
        raise FeatureContractError("at least one numeric feature is required")
    return categorical, numeric


def make_preprocessor(
    frame: pd.DataFrame, feature_columns: list[str], model_id: str
) -> ColumnTransformer:
    """Create train-only preprocessing while preserving raw feature order."""

    categorical, numeric = _column_groups(frame, feature_columns)
    if model_id == "linear_model":
        categorical_pipeline = Pipeline(
            [
                (
                    "imputer",
                    SimpleImputer(strategy="constant", fill_value="__MISSING__"),
                ),
                (
                    "encoder",
                    OneHotEncoder(
                        handle_unknown="ignore",
                        dtype=np.float32,
                    ),
                ),
            ]
        )
        numeric_pipeline = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]
        )
        sparse_threshold = 1.0
    else:
        categorical_pipeline = Pipeline(
            [
                (
                    "imputer",
                    SimpleImputer(strategy="constant", fill_value="__MISSING__"),
                ),
                (
                    "encoder",
                    OrdinalEncoder(
                        handle_unknown="use_encoded_value",
                        unknown_value=-1,
                        dtype=np.float32,
                    ),
                ),
            ]
        )
        numeric_pipeline = Pipeline([("imputer", SimpleImputer(strategy="median"))])
        sparse_threshold = 0.0

    return ColumnTransformer(
        [
            ("categorical", categorical_pipeline, categorical),
            ("numeric", numeric_pipeline, numeric),
        ],
        sparse_threshold=sparse_threshold,
        verbose_feature_names_out=False,
    )


def make_estimator(
    model_id: str, *, seed: int, parameters: Mapping[str, Any]
) -> BaseEstimator:
    """Instantiate a deterministic candidate estimator."""

    supplied = dict(parameters)
    if model_id == "linear_model":
        return Ridge(**supplied)
    if model_id == "random_forest":
        return RandomForestRegressor(random_state=seed, **supplied)
    if model_id == "lightgbm":
        try:
            from lightgbm import LGBMRegressor
        except ImportError as exc:  # pragma: no cover - exercised in user runtime
            raise RuntimeError(
                "LightGBM is required; install the pinned project dependencies"
            ) from exc
        return LGBMRegressor(random_state=seed, **supplied)
    raise ValueError(f"unknown model candidate: {model_id}")


def _valid_training_mask(frame: pd.DataFrame, horizon: int) -> pd.Series:
    target = f"delta_hist_h{horizon}"
    valid = f"target_h{horizon}_valid"
    missing = {target, valid} - set(frame.columns)
    if missing:
        raise FeatureContractError(f"missing target columns: {sorted(missing)}")
    return frame[valid].astype(bool) & frame[target].notna()


def fit_candidate(
    frame: pd.DataFrame,
    *,
    model_id: str,
    feature_columns: list[str],
    seed: int,
    parameters: Mapping[str, Any],
) -> FittedCandidate:
    """Fit one candidate for all horizons using train rows only."""

    if model_id not in MODEL_CANDIDATES:
        raise ValueError(f"unknown model candidate: {model_id}")
    train = frame.loc[frame["split"].eq("train")].copy()
    if train.empty:
        raise FeatureContractError("training split is empty")

    preprocessor = make_preprocessor(train, feature_columns, model_id)
    transformed = preprocessor.fit_transform(train[feature_columns])
    if model_id != "linear_model":
        transformed = np.asarray(transformed, dtype=np.float32)
    if model_id == "lightgbm":
        transformed = pd.DataFrame(
            transformed,
            columns=preprocessor.get_feature_names_out(),
        )

    estimators: dict[int, BaseEstimator] = {}
    training_rows: dict[int, int] = {}
    for horizon in HORIZONS:
        mask = _valid_training_mask(train, horizon).to_numpy()
        if not mask.any():
            raise FeatureContractError(f"no valid training targets for {horizon}m")
        estimator = make_estimator(model_id, seed=seed, parameters=parameters)
        target = train.loc[mask, f"delta_hist_h{horizon}"].to_numpy(dtype=np.float64)
        estimator.fit(transformed[mask], target)
        estimators[horizon] = estimator
        training_rows[horizon] = int(mask.sum())

    return FittedCandidate(
        model_id=model_id,
        feature_columns=list(feature_columns),
        preprocessor=preprocessor,
        estimators=estimators,
        training_rows=training_rows,
    )


def fit_baselines(frame: pd.DataFrame) -> FittedBaselines:
    """Fit B3 lookups on training targets; B1 and B2 require no fitted target."""

    train = frame.loc[frame["split"].eq("train")].copy()
    if train.empty:
        raise FeatureContractError("training split is empty")
    missing = set(GROUP_COLUMNS) - set(train.columns)
    if missing:
        raise FeatureContractError(f"missing B3 grouping columns: {sorted(missing)}")

    group_means: dict[int, pd.Series] = {}
    global_means: dict[int, float] = {}
    for horizon in HORIZONS:
        mask = _valid_training_mask(train, horizon)
        eligible = train.loc[mask, [*GROUP_COLUMNS, f"delta_hist_h{horizon}"]]
        group_means[horizon] = eligible.groupby(list(GROUP_COLUMNS), sort=True)[
            f"delta_hist_h{horizon}"
        ].mean()
        global_means[horizon] = float(eligible[f"delta_hist_h{horizon}"].mean())
    return FittedBaselines(group_means=group_means, global_means=global_means)


def active_station_definition(
    frame: pd.DataFrame, *, percentile: float
) -> tuple[set[str], float]:
    """Define ACTIVE stations from observed training activity only."""

    if not 0 <= percentile <= 1:
        raise ValueError("active station percentile must be between 0 and 1")
    required = {"station_id", "rent_count", "return_count", "is_observed", "split"}
    missing = required - set(frame.columns)
    if missing:
        raise FeatureContractError(f"missing ACTIVE columns: {sorted(missing)}")
    train = frame.loc[frame["split"].eq("train") & frame["is_observed"].astype(bool)]
    if train.empty:
        raise FeatureContractError("no observed rows exist in training")
    activity = (
        train.assign(
            total_activity=pd.to_numeric(train["rent_count"], errors="coerce")
            + pd.to_numeric(train["return_count"], errors="coerce")
        )
        .groupby("station_id", sort=True)["total_activity"]
        .sum()
    )
    threshold = float(activity.quantile(percentile))
    stations = set(activity.index[activity.ge(threshold)].astype(str))
    return stations, threshold


def segment_mask(
    frame: pd.DataFrame, segment: str, active_stations: set[str]
) -> pd.Series:
    """Return a mask for the preserved Week 03 evaluation segments."""

    active = frame["station_id"].astype(str).isin(active_stations)
    peak = frame["is_peak"].astype(bool)
    if segment == "ALL":
        return pd.Series(True, index=frame.index)
    if segment == "ACTIVE":
        return active
    if segment == "PEAK":
        return peak
    if segment == "ACTIVE_PEAK":
        return active & peak
    raise ValueError(f"unknown segment: {segment}")


def _timed_predictions(
    predict: Any,
    sample: pd.DataFrame,
    *,
    repeats: int,
) -> float:
    if sample.empty:
        return float("nan")
    predict(sample)
    durations = []
    for _ in range(repeats):
        started = time.perf_counter()
        predict(sample)
        durations.append(time.perf_counter() - started)
    return float(np.median(durations) * 1000 * (1000 / len(sample)))


def inference_sample(frame: pd.DataFrame, *, rows: int = 1000) -> pd.DataFrame:
    """Choose a deterministic, chronologically spread validation sample."""

    validation = frame.loc[frame["split"].eq("validation")]
    if validation.empty:
        raise FeatureContractError("validation split is empty")
    if len(validation) <= rows:
        return validation.copy()
    positions = np.linspace(0, len(validation) - 1, num=rows, dtype=np.int64)
    return validation.iloc[positions].copy()


def evaluate_validation_comparison(
    frame: pd.DataFrame,
    *,
    baselines: FittedBaselines,
    candidates: Mapping[str, FittedCandidate],
    active_percentile: float,
    timing_repeats: int = 5,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Evaluate baselines and candidates on validation, never on test."""

    validation = frame.loc[frame["split"].eq("validation")].copy()
    if validation.empty:
        raise FeatureContractError("validation split is empty")
    active_stations, threshold = active_station_definition(
        frame, percentile=active_percentile
    )
    sample = inference_sample(frame)

    predictions: dict[str, dict[int, np.ndarray]] = {}
    inference_times: dict[str, float] = {}
    for baseline_id in BASELINE_IDS:
        predictions[baseline_id] = baselines.predict_all(validation, baseline_id)
        inference_times[baseline_id] = _timed_predictions(
            lambda value, baseline_id=baseline_id: baselines.predict_all(
                value, baseline_id
            ),
            sample,
            repeats=timing_repeats,
        )
    for model_id in MODEL_CANDIDATES:
        if model_id not in candidates:
            raise FeatureContractError(f"missing fitted candidate: {model_id}")
        predictions[model_id] = candidates[model_id].predict_all(validation)
        inference_times[model_id] = _timed_predictions(
            candidates[model_id].predict_all,
            sample,
            repeats=timing_repeats,
        )

    rows: list[dict[str, Any]] = []
    for model_id in (*BASELINE_IDS, *MODEL_CANDIDATES):
        for segment in SEGMENTS:
            in_segment = segment_mask(validation, segment, active_stations)
            for horizon in HORIZONS:
                target_column = f"delta_hist_h{horizon}"
                valid_column = f"target_h{horizon}_valid"
                prediction = predictions[model_id][horizon]
                eligible = (
                    in_segment.to_numpy()
                    & validation[valid_column].astype(bool).to_numpy()
                    & validation[target_column].notna().to_numpy()
                    & np.isfinite(prediction)
                )
                target = validation[target_column].to_numpy(dtype=np.float64)
                if eligible.any():
                    error = prediction[eligible] - target[eligible]
                    mae = float(np.mean(np.abs(error)))
                    rmse = float(np.sqrt(np.mean(np.square(error))))
                    b1_mae = float(np.mean(np.abs(target[eligible])))
                    improvement = (
                        float((b1_mae - mae) / b1_mae) if b1_mae > 0 else np.nan
                    )
                else:
                    mae = rmse = b1_mae = improvement = np.nan
                rows.append(
                    {
                        "split": "validation",
                        "model_id": model_id,
                        "model": MODEL_DISPLAY_NAMES[model_id],
                        "model_type": (
                            "baseline" if model_id in BASELINE_IDS else "candidate"
                        ),
                        "segment": segment,
                        "horizon_min": horizon,
                        "candidate_rows": int(in_segment.sum()),
                        "evaluated_rows": int(eligible.sum()),
                        "mae": mae,
                        "rmse": rmse,
                        "b1_mae_same_rows": b1_mae,
                        "improvement_vs_b1": improvement,
                        "inference_time_ms_per_1k_rows": inference_times[model_id],
                    }
                )

    metrics = pd.DataFrame(rows)
    evaluation_metadata = {
        "evaluation_split": "validation",
        "test_metrics_generated": False,
        "test_targets_accessed": False,
        "test_reserved_for_week05": True,
        "active_station_percentile": active_percentile,
        "active_station_activity_threshold": threshold,
        "active_station_count": len(active_stations),
        "active_station_ids": sorted(active_stations),
        "inference_timing": {
            "sample_rows": len(sample),
            "repeats": timing_repeats,
            "warmup_runs": 1,
            "statistic": "median wall-clock; preprocessing plus all three horizons",
            "milliseconds_per_1000_rows": inference_times,
        },
    }
    return metrics, evaluation_metadata


def make_wide_comparison_table(metrics: pd.DataFrame) -> pd.DataFrame:
    """Create the required one-row-per-model-and-segment comparison table."""

    required = {
        "model_id",
        "model",
        "model_type",
        "segment",
        "horizon_min",
        "mae",
        "rmse",
        "improvement_vs_b1",
        "inference_time_ms_per_1k_rows",
    }
    missing = required - set(metrics.columns)
    if missing:
        raise FeatureContractError(f"missing metric columns: {sorted(missing)}")

    index = ["model_id", "model", "model_type", "segment"]
    table = metrics[index].drop_duplicates().set_index(index)
    for metric, label in (
        ("mae", "MAE"),
        ("rmse", "RMSE"),
        ("improvement_vs_b1", "Improvement vs B1"),
    ):
        pivoted = metrics.pivot(index=index, columns="horizon_min", values=metric)
        pivoted = pivoted.rename(
            columns={horizon: f"{horizon}m {label}" for horizon in HORIZONS}
        )
        table = table.join(pivoted)

    timing = metrics.groupby(index, sort=False)["inference_time_ms_per_1k_rows"].first()
    table = table.join(timing.rename("Inference ms / 1k rows")).reset_index()
    table = table.rename(
        columns={
            "model_id": "Model ID",
            "model": "Model",
            "model_type": "Model Type",
            "segment": "Segment",
        }
    )
    order = {
        model_id: index
        for index, model_id in enumerate((*BASELINE_IDS, *MODEL_CANDIDATES))
    }
    table["_model_order"] = table["Model ID"].map(order)
    table["_segment_order"] = table["Segment"].map(
        {segment: index for index, segment in enumerate(SEGMENTS)}
    )
    return (
        table.sort_values(["_model_order", "_segment_order"])
        .drop(columns=["_model_order", "_segment_order"])
        .reset_index(drop=True)
    )
