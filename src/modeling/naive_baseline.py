"""Week 03 naive baselines and chronological evaluation utilities."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from .feature_engineering import BASE_INTERVAL_MIN, HORIZONS, FeatureContractError

SEGMENTS = ("ALL", "ACTIVE", "PEAK", "ACTIVE_PEAK")
BASELINES = ("persistence", "zero")


def add_naive_predictions(
    frame: pd.DataFrame,
    horizons: Iterable[int] = HORIZONS,
) -> pd.DataFrame:
    """Add persistence and zero predictions without fitting on future data.

    For horizon ``h``, persistence uses the realized target whose window ended
    exactly at the current ``base_time``:

    ``prediction(t, h) = delta_hist_h(t-h)``.
    """

    required = {"station_id", "base_time"}
    for horizon in horizons:
        required.update(
            {f"delta_hist_h{horizon}", f"target_h{horizon}_valid"}
        )
    missing = required - set(frame.columns)
    if missing:
        raise FeatureContractError(f"missing baseline columns: {sorted(missing)}")

    result = frame.copy()
    result["station_id"] = result["station_id"].astype("string")
    result["base_time"] = pd.to_datetime(result["base_time"], errors="coerce")
    if result["base_time"].isna().any():
        raise FeatureContractError("base_time contains invalid timestamps")

    result = result.sort_values(["station_id", "base_time"]).reset_index(drop=True)
    grouped = result.groupby("station_id", sort=False)

    for horizon in horizons:
        if horizon <= 0 or horizon % BASE_INTERVAL_MIN:
            raise ValueError("horizons must be positive multiples of 15 minutes")

        steps = horizon // BASE_INTERVAL_MIN
        target_column = f"delta_hist_h{horizon}"
        valid_column = f"target_h{horizon}_valid"
        prediction_column = f"prediction_persistence_h{horizon}"
        available_column = f"persistence_h{horizon}_available"

        previous_target = grouped[target_column].shift(steps)
        previous_valid = grouped[valid_column].shift(steps).fillna(False).astype(bool)
        previous_time = grouped["base_time"].shift(steps)
        available = previous_valid & previous_time.eq(
            result["base_time"] - pd.Timedelta(minutes=horizon)
        )

        result[prediction_column] = previous_target.where(available)
        result[available_column] = available
        result[f"prediction_zero_h{horizon}"] = 0.0

    return result


def _complete_dates(frame: pd.DataFrame) -> pd.DatetimeIndex:
    date = frame["base_time"].dt.normalize()
    if "source_day_observed" in frame:
        observed = frame["source_day_observed"].astype(bool)
    elif "is_observed" in frame:
        observed = frame["is_observed"].astype(bool)
    else:
        raise FeatureContractError(
            "source_day_observed or is_observed is required for complete-day splits"
        )

    complete = observed.groupby(date).all()
    return pd.DatetimeIndex(complete.index[complete]).sort_values()


def assign_chronological_splits(
    frame: pd.DataFrame,
    validation_days: int,
    test_days: int,
    minimum_history_days: int,
    *,
    enforce_minimum_history: bool = True,
) -> pd.DataFrame:
    """Assign train/validation/test using complete dates only.

    Incomplete source dates remain ``excluded`` and are never silently treated
    as zero-demand dates.
    """

    if min(validation_days, test_days, minimum_history_days) < 0:
        raise ValueError("split day counts cannot be negative")
    if validation_days == 0 or test_days == 0:
        raise ValueError("validation_days and test_days must be positive")

    result = frame.copy()
    result["base_time"] = pd.to_datetime(result["base_time"], errors="coerce")
    if result["base_time"].isna().any():
        raise FeatureContractError("base_time contains invalid timestamps")

    complete_dates = _complete_dates(result)
    required_holdout = validation_days + test_days
    if len(complete_dates) <= required_holdout:
        raise FeatureContractError(
            "not enough complete dates for chronological validation/test splits"
        )

    test_dates = complete_dates[-test_days:]
    validation_dates = complete_dates[-required_holdout:-test_days]
    train_dates = complete_dates[:-required_holdout]

    if enforce_minimum_history and len(train_dates) < minimum_history_days:
        raise FeatureContractError(
            f"training history has {len(train_dates)} complete days; "
            f"minimum is {minimum_history_days}"
        )

    date = result["base_time"].dt.normalize()
    result["split"] = "excluded"
    result.loc[date.isin(train_dates), "split"] = "train"
    result.loc[date.isin(validation_dates), "split"] = "validation"
    result.loc[date.isin(test_dates), "split"] = "test"

    result.attrs["split_metadata"] = {
        "train_start": train_dates.min() if len(train_dates) else pd.NaT,
        "train_end": train_dates.max() if len(train_dates) else pd.NaT,
        "validation_start": validation_dates.min(),
        "validation_end": validation_dates.max(),
        "test_start": test_dates.min(),
        "test_end": test_dates.max(),
        "train_complete_days": len(train_dates),
        "validation_complete_days": len(validation_dates),
        "test_complete_days": len(test_dates),
    }
    return result


def _active_stations(
    frame: pd.DataFrame,
    percentile: float,
) -> tuple[set[str], float]:
    if not 0 <= percentile <= 1:
        raise ValueError("active station percentile must be between 0 and 1")
    required = {"rent_count", "return_count", "is_observed", "split"}
    missing = required - set(frame.columns)
    if missing:
        raise FeatureContractError(
            f"missing ACTIVE segment columns: {sorted(missing)}"
        )

    train = frame.loc[frame["split"].eq("train") & frame["is_observed"].astype(bool)]
    if train.empty:
        raise FeatureContractError("training split is empty")

    activity = (
        train.assign(
            total_activity=train["rent_count"].astype(float)
            + train["return_count"].astype(float)
        )
        .groupby("station_id")["total_activity"]
        .sum()
    )
    threshold = float(activity.quantile(percentile))
    return set(activity.index[activity.ge(threshold)].astype(str)), threshold


def _metric_row(
    candidates: pd.DataFrame,
    eligible: pd.Series,
    prediction_column: str,
    target_column: str,
    *,
    split: str,
    segment: str,
    baseline: str,
    horizon: int | None,
    active_threshold: float,
) -> dict[str, object]:
    evaluated = candidates.loc[eligible, [target_column, prediction_column, "base_time"]]
    if evaluated.empty:
        mae = np.nan
        rmse = np.nan
        zero_rate = np.nan
        date_start = pd.NaT
        date_end = pd.NaT
    else:
        error = (
            evaluated[prediction_column].astype(float)
            - evaluated[target_column].astype(float)
        )
        mae = float(error.abs().mean())
        rmse = float(np.sqrt(np.square(error).mean()))
        zero_rate = float(evaluated[target_column].eq(0).mean())
        date_start = evaluated["base_time"].min()
        date_end = evaluated["base_time"].max()

    return {
        "split": split,
        "scope": "micro" if horizon is None else "horizon",
        "horizon_min": pd.NA if horizon is None else horizon,
        "segment": segment,
        "baseline": baseline,
        "candidate_rows": int(len(candidates)),
        "evaluated_rows": int(eligible.sum()),
        "excluded_rows": int(len(candidates) - eligible.sum()),
        "mae": mae,
        "rmse": rmse,
        "target_zero_rate": zero_rate,
        "evaluation_start": date_start,
        "evaluation_end": date_end,
        "active_station_activity_threshold": active_threshold,
    }


def _segment_mask(
    frame: pd.DataFrame,
    segment: str,
    active_stations: set[str],
) -> pd.Series:
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


def evaluate_naive_baselines(
    frame: pd.DataFrame,
    *,
    active_percentile: float = 0.75,
    splits: Iterable[str] = ("validation", "test"),
    horizons: Iterable[int] = HORIZONS,
) -> pd.DataFrame:
    """Evaluate persistence and zero baselines by horizon and micro average."""

    required = {"station_id", "base_time", "split", "is_peak"}
    missing = required - set(frame.columns)
    if missing:
        raise FeatureContractError(f"missing evaluation columns: {sorted(missing)}")

    horizons = tuple(horizons)
    active_stations, active_threshold = _active_stations(frame, active_percentile)
    rows: list[dict[str, object]] = []

    for split in splits:
        split_frame = frame.loc[frame["split"].eq(split)].copy()
        if split_frame.empty:
            raise FeatureContractError(f"{split} split is empty")

        for segment in SEGMENTS:
            segment_frame = split_frame.loc[
                _segment_mask(split_frame, segment, active_stations)
            ].copy()

            micro_parts: dict[str, list[pd.DataFrame]] = {
                baseline: [] for baseline in BASELINES
            }

            for horizon in horizons:
                target = f"delta_hist_h{horizon}"
                target_valid = f"target_h{horizon}_valid"
                for baseline in BASELINES:
                    prediction = f"prediction_{baseline}_h{horizon}"
                    missing_columns = {
                        target,
                        target_valid,
                        prediction,
                    } - set(segment_frame.columns)
                    if missing_columns:
                        raise FeatureContractError(
                            f"missing evaluation columns: {sorted(missing_columns)}"
                        )

                    eligible = (
                        segment_frame[target_valid].astype(bool)
                        & segment_frame[target].notna()
                        & segment_frame[prediction].notna()
                    )
                    if baseline == "persistence":
                        eligible &= segment_frame[
                            f"persistence_h{horizon}_available"
                        ].astype(bool)

                    rows.append(
                        _metric_row(
                            segment_frame,
                            eligible,
                            prediction,
                            target,
                            split=split,
                            segment=segment,
                            baseline=baseline,
                            horizon=horizon,
                            active_threshold=active_threshold,
                        )
                    )

                    part = segment_frame[["base_time", target, prediction]].rename(
                        columns={target: "target", prediction: "prediction"}
                    )
                    part["eligible"] = eligible.to_numpy()
                    micro_parts[baseline].append(part)

            for baseline in BASELINES:
                parts = micro_parts[baseline]
                micro = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
                if micro.empty:
                    eligible = pd.Series(dtype=bool)
                    candidates = pd.DataFrame(
                        columns=["base_time", "target", "prediction"]
                    )
                else:
                    eligible = micro.pop("eligible").astype(bool)
                    candidates = micro

                rows.append(
                    _metric_row(
                        candidates,
                        eligible,
                        "prediction",
                        "target",
                        split=split,
                        segment=segment,
                        baseline=baseline,
                        horizon=None,
                        active_threshold=active_threshold,
                    )
                )

    result = pd.DataFrame(rows)
    result["horizon_min"] = result["horizon_min"].astype("Int64")
    return result
