"""Leakage-safe Week 03 features built on the Week 02 training table.

The Week 02 table defines ``base_time`` as the left edge of the future target
window. Consequently, activity recorded in the row at ``base_time == t`` is a
target component and cannot be used as a feature for a prediction made at
``t``. All historical activity features below therefore start with shift(1).
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

BASE_INTERVAL_MIN = 15
HORIZONS = (15, 30, 60)
ALLOWED_DISTRICTS = frozenset({"광진구", "성동구"})

IDENTITY_COLUMNS = ("station_id", "base_time", "district")
CURRENT_ACTIVITY_COLUMNS = ("rent_count", "return_count", "delta_hist")
OBSERVATION_COLUMNS = ("source_day_observed", "is_observed")
WEATHER_FEATURE_COLUMNS = (
    "temp_c",
    "precip_mm",
    "humidity_pct",
    "wind_ms",
    "weather_age_min",
    "weather_available",
    "temp_c_missing",
    "precip_mm_missing",
    "humidity_pct_missing",
    "wind_ms_missing",
)
OPTIONAL_STATION_FEATURE_COLUMNS = ("capacity",)

TIME_FEATURE_COLUMNS = (
    "hour",
    "minute",
    "weekday_index",
    "month",
    "day_of_year",
    "is_weekend",
    "is_holiday",
    "is_peak",
    "is_holiday_or_weekend",
    "time_of_day_sin",
    "time_of_day_cos",
    "weekday_sin",
    "weekday_cos",
)

HISTORY_FEATURE_COLUMNS = tuple(
    column
    for window in HORIZONS
    for column in (
        f"rent_prev_{window}m",
        f"return_prev_{window}m",
        f"delta_prev_{window}m",
        f"history_{window}m_available",
    )
) + (
    "rent_mean_prev_24h",
    "return_mean_prev_24h",
    "delta_mean_prev_24h",
    "history_24h_observations",
    "history_24h_available",
    "delta_lag_1d",
    "delta_lag_7d",
    "lag_1d_available",
    "lag_7d_available",
)


class FeatureContractError(ValueError):
    """Raised when an input violates a Week 01-02 data contract."""


def _required_columns() -> set[str]:
    required = {
        *IDENTITY_COLUMNS,
        *CURRENT_ACTIVITY_COLUMNS,
        "is_observed",
        "is_holiday",
    }
    for horizon in HORIZONS:
        required.add(f"delta_hist_h{horizon}")
        required.add(f"target_h{horizon}_valid")
    return required


def _as_bool(series: pd.Series, name: str) -> pd.Series:
    """Return a strict boolean series without treating missing as false."""

    if series.isna().any():
        raise FeatureContractError(f"{name} contains missing values")

    if pd.api.types.is_bool_dtype(series.dtype):
        return series.astype(bool)

    allowed = {0, 1, "0", "1", "true", "false", "True", "False"}
    values = set(series.unique().tolist())
    if not values <= allowed:
        raise FeatureContractError(f"{name} must contain only boolean values")

    return series.map(
        {
            0: False,
            1: True,
            "0": False,
            "1": True,
            "true": True,
            "false": False,
            "True": True,
            "False": False,
        }
    ).astype(bool)


def _kst_timestamp(series: pd.Series, name: str) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    if parsed.isna().any():
        raise FeatureContractError(f"{name} contains invalid timestamps")

    if isinstance(parsed.dtype, pd.DatetimeTZDtype):
        return parsed.dt.tz_convert("Asia/Seoul")
    return parsed.dt.tz_localize("Asia/Seoul")


def _validate_target_contract(frame: pd.DataFrame) -> None:
    grouped = frame.groupby("station_id", sort=False)
    base_time = frame["base_time"]
    observed = frame["is_observed"]

    for horizon in HORIZONS:
        steps = horizon // BASE_INTERVAL_MIN
        valid = pd.Series(True, index=frame.index)
        components: list[pd.Series] = []

        for offset in range(steps):
            component = grouped["delta_hist"].shift(-offset)
            component_observed = grouped["is_observed"].shift(-offset)
            component_time = grouped["base_time"].shift(-offset)
            components.append(component)
            valid &= component_observed.fillna(False).astype(bool)
            valid &= component_time.eq(
                base_time + pd.Timedelta(minutes=offset * BASE_INTERVAL_MIN)
            )

        expected = pd.concat(components, axis=1).sum(axis=1, min_count=steps)
        declared_valid = frame[f"target_h{horizon}_valid"]
        target = frame[f"delta_hist_h{horizon}"]

        if not declared_valid.equals(valid):
            mismatch = int(declared_valid.ne(valid).sum())
            raise FeatureContractError(
                f"target_h{horizon}_valid violates the Week 02 window contract "
                f"for {mismatch} rows"
            )

        if target.loc[~declared_valid].notna().any():
            raise FeatureContractError(
                f"delta_hist_h{horizon} must be null when its target is invalid"
            )

        actual = target.loc[declared_valid].astype(float)
        wanted = expected.loc[declared_valid].astype(float)
        if not np.allclose(actual, wanted, rtol=0.0, atol=1e-9):
            raise FeatureContractError(
                f"delta_hist_h{horizon} does not equal the forward delta sum"
            )

    if not observed.equals(frame["is_observed"]):
        raise AssertionError("observation validation changed row alignment")


def validate_week02_contract(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize the Week 02 input contract."""

    missing = _required_columns() - set(frame.columns)
    if missing:
        raise FeatureContractError(f"missing required columns: {sorted(missing)}")

    result = frame.copy()
    result["station_id"] = result["station_id"].astype("string").str.strip()
    result["base_time"] = pd.to_datetime(result["base_time"], errors="coerce")

    if result["station_id"].isna().any() or result["station_id"].eq("").any():
        raise FeatureContractError("station_id contains missing or empty values")
    if result["base_time"].isna().any():
        raise FeatureContractError("base_time contains invalid timestamps")
    if result["district"].isna().any():
        raise FeatureContractError("district contains missing values")

    invalid_districts = set(result["district"].unique()) - ALLOWED_DISTRICTS
    if invalid_districts:
        raise FeatureContractError(
            f"district is outside the approved scope: {sorted(invalid_districts)}"
        )

    result = result.sort_values(["station_id", "base_time"]).reset_index(drop=True)

    if result.duplicated(["station_id", "base_time"]).any():
        raise FeatureContractError("duplicate station_id × base_time rows")

    aligned = (
        result["base_time"].dt.minute.mod(BASE_INTERVAL_MIN).eq(0)
        & result["base_time"].dt.second.eq(0)
        & result["base_time"].dt.microsecond.eq(0)
    )
    if not aligned.all():
        raise FeatureContractError("base_time is not aligned to 15-minute bins")

    result["is_observed"] = _as_bool(result["is_observed"], "is_observed")
    result["is_holiday"] = _as_bool(result["is_holiday"], "is_holiday")
    if "source_day_observed" in result:
        result["source_day_observed"] = _as_bool(
            result["source_day_observed"], "source_day_observed"
        )

    for horizon in HORIZONS:
        flag = f"target_h{horizon}_valid"
        result[flag] = _as_bool(result[flag], flag)

    observed = result["is_observed"]
    activity = result[list(CURRENT_ACTIVITY_COLUMNS)]
    if activity.loc[observed].isna().any().any():
        raise FeatureContractError("observed rows contain missing activity values")
    if activity.loc[~observed].notna().any().any():
        raise FeatureContractError(
            "unobserved rows must retain null activity instead of zero"
        )

    expected_delta = result["return_count"] - result["rent_count"]
    actual_delta = result["delta_hist"]
    if not np.allclose(
        actual_delta.loc[observed].astype(float),
        expected_delta.loc[observed].astype(float),
        rtol=0.0,
        atol=1e-9,
    ):
        raise FeatureContractError("delta_hist != return_count - rent_count")

    _validate_target_contract(result)
    _validate_weather_contract(result)
    return result


def _validate_weather_contract(frame: pd.DataFrame) -> None:
    if "weather_station_id" in frame:
        station_ids = set(
            pd.to_numeric(frame["weather_station_id"], errors="coerce")
            .dropna()
            .astype(int)
            .unique()
        )
        if station_ids - {421}:
            raise FeatureContractError(
                f"weather station must be AWS 421; found {sorted(station_ids)}"
            )

    if "weather_obs_time" not in frame:
        return

    available = frame["weather_obs_time"].notna()
    if "weather_available" in frame:
        declared = frame["weather_available"].fillna(False).astype(bool)
        if (declared & ~available).any():
            raise FeatureContractError(
                "weather_available is true without weather_obs_time"
            )

    if not available.any():
        return

    base_kst = _kst_timestamp(frame.loc[available, "base_time"], "base_time")
    weather_kst = _kst_timestamp(
        frame.loc[available, "weather_obs_time"], "weather_obs_time"
    )
    if weather_kst.gt(base_kst).any():
        raise FeatureContractError(
            "future weather observation detected after prediction base_time"
        )

    age = (base_kst - weather_kst).dt.total_seconds().div(60)
    if age.gt(60).any():
        raise FeatureContractError(
            "weather observation exceeds the Week 02 60-minute as-of tolerance"
        )


def _history_window(
    frame: pd.DataFrame,
    value_column: str,
    steps: int,
) -> tuple[pd.Series, pd.Series]:
    grouped = frame.groupby("station_id", sort=False)
    components: list[pd.Series] = []
    available = pd.Series(True, index=frame.index)

    for offset in range(1, steps + 1):
        value = grouped[value_column].shift(offset)
        observed = grouped["is_observed"].shift(offset)
        timestamp = grouped["base_time"].shift(offset)
        components.append(value)
        available &= observed.fillna(False).astype(bool)
        available &= timestamp.eq(
            frame["base_time"] - pd.Timedelta(minutes=offset * BASE_INTERVAL_MIN)
        )

    total = pd.concat(components, axis=1).sum(axis=1, min_count=steps)
    return total.where(available), available


def _lag_feature(
    frame: pd.DataFrame,
    value_column: str,
    steps: int,
) -> tuple[pd.Series, pd.Series]:
    grouped = frame.groupby("station_id", sort=False)
    value = grouped[value_column].shift(steps)
    observed = grouped["is_observed"].shift(steps).fillna(False).astype(bool)
    timestamp = grouped["base_time"].shift(steps)
    available = observed & timestamp.eq(
        frame["base_time"] - pd.Timedelta(minutes=steps * BASE_INTERVAL_MIN)
    )
    return value.where(available), available


def _add_time_features(frame: pd.DataFrame) -> None:
    base_time = frame["base_time"]
    minute_of_day = base_time.dt.hour * 60 + base_time.dt.minute
    weekday_index = base_time.dt.weekday

    expected_weekend = weekday_index.ge(5)
    expected_peak = minute_of_day.between(7 * 60, 9 * 60 - 1) | minute_of_day.between(
        18 * 60, 20 * 60 - 1
    )

    if "is_weekend" in frame:
        declared_weekend = _as_bool(frame["is_weekend"], "is_weekend")
        if not declared_weekend.equals(expected_weekend):
            raise FeatureContractError("is_weekend disagrees with base_time")

    if "is_peak" in frame:
        declared_peak = _as_bool(frame["is_peak"], "is_peak")
        if not declared_peak.equals(expected_peak):
            raise FeatureContractError("is_peak disagrees with PEAK_HOURS contract")

    frame["hour"] = base_time.dt.hour.astype("int8")
    frame["minute"] = base_time.dt.minute.astype("int8")
    frame["weekday_index"] = weekday_index.astype("int8")
    frame["month"] = base_time.dt.month.astype("int8")
    frame["day_of_year"] = base_time.dt.dayofyear.astype("int16")
    frame["is_weekend"] = expected_weekend
    frame["is_peak"] = expected_peak
    frame["is_holiday_or_weekend"] = frame["is_holiday"] | expected_weekend

    time_angle = 2 * np.pi * minute_of_day / (24 * 60)
    weekday_angle = 2 * np.pi * weekday_index / 7
    frame["time_of_day_sin"] = np.sin(time_angle)
    frame["time_of_day_cos"] = np.cos(time_angle)
    frame["weekday_sin"] = np.sin(weekday_angle)
    frame["weekday_cos"] = np.cos(weekday_angle)


def _add_history_features(frame: pd.DataFrame) -> None:
    for window in HORIZONS:
        steps = window // BASE_INTERVAL_MIN
        rent, available = _history_window(frame, "rent_count", steps)
        returns, return_available = _history_window(frame, "return_count", steps)
        delta, delta_available = _history_window(frame, "delta_hist", steps)

        combined_available = available & return_available & delta_available
        frame[f"rent_prev_{window}m"] = rent.where(combined_available)
        frame[f"return_prev_{window}m"] = returns.where(combined_available)
        frame[f"delta_prev_{window}m"] = delta.where(combined_available)
        frame[f"history_{window}m_available"] = combined_available

    day_steps = 24 * 60 // BASE_INTERVAL_MIN
    grouped = frame.groupby("station_id", sort=False)
    station_key = frame["station_id"]

    shifted_observed = grouped["is_observed"].shift(1).fillna(False).astype("int8")
    observation_count = (
        shifted_observed.groupby(station_key, sort=False)
        .rolling(day_steps, min_periods=1)
        .sum()
        .reset_index(level=0, drop=True)
        .reindex(frame.index)
    )
    day_continuous = grouped["base_time"].shift(day_steps).eq(
        frame["base_time"] - pd.Timedelta(days=1)
    ) & grouped["base_time"].shift(1).eq(
        frame["base_time"] - pd.Timedelta(minutes=BASE_INTERVAL_MIN)
    )
    day_available = observation_count.eq(day_steps) & day_continuous

    for source, output in (
        ("rent_count", "rent_mean_prev_24h"),
        ("return_count", "return_mean_prev_24h"),
        ("delta_hist", "delta_mean_prev_24h"),
    ):
        shifted = grouped[source].shift(1)
        mean = (
            shifted.groupby(station_key, sort=False)
            .rolling(day_steps, min_periods=day_steps)
            .mean()
            .reset_index(level=0, drop=True)
            .reindex(frame.index)
        )
        frame[output] = mean.where(day_available)

    frame["history_24h_observations"] = observation_count.astype("int16")
    frame["history_24h_available"] = day_available

    lag_1d, lag_1d_available = _lag_feature(frame, "delta_hist", day_steps)
    lag_7d, lag_7d_available = _lag_feature(frame, "delta_hist", 7 * day_steps)
    frame["delta_lag_1d"] = lag_1d
    frame["delta_lag_7d"] = lag_7d
    frame["lag_1d_available"] = lag_1d_available
    frame["lag_7d_available"] = lag_7d_available


def build_week03_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a validated table enriched with Week 03 model features.

    Current-window activity and future targets remain in the returned table as
    audit/evaluation fields. Use :func:`get_model_feature_columns` to obtain the
    explicit leakage-safe feature allowlist for model training.
    """

    result = validate_week02_contract(frame)
    _add_time_features(result)
    _add_history_features(result)
    return result


def get_model_feature_columns(frame: pd.DataFrame) -> list[str]:
    """Return the ordered, leakage-safe Week 03 feature allowlist."""

    candidates: Iterable[str] = (
        "station_id",
        "district",
        *OPTIONAL_STATION_FEATURE_COLUMNS,
        *TIME_FEATURE_COLUMNS,
        *HISTORY_FEATURE_COLUMNS,
        *WEATHER_FEATURE_COLUMNS,
    )
    return [column for column in candidates if column in frame.columns]


def build_feature_manifest(frame: pd.DataFrame) -> pd.DataFrame:
    """Describe which columns are features, targets, identities, or audit data."""

    model_features = set(get_model_feature_columns(frame))
    identity = set(IDENTITY_COLUMNS)
    targets = {
        column
        for column in frame.columns
        if column.startswith("delta_hist_h") or column.startswith("target_h")
    }
    audit = (
        set(CURRENT_ACTIVITY_COLUMNS)
        | set(OBSERVATION_COLUMNS)
        | {
            "weather_obs_time",
            "weather_station_id",
            "date",
            "weekday",
            "season",
            "station_name",
        }
    )

    rows = []
    for column in frame.columns:
        if column in targets:
            role = "target"
            available_at = "after target window"
        elif column in model_features:
            role = "feature"
            available_at = "at or before base_time"
        elif column in identity:
            role = "identity"
            available_at = "at base_time"
        elif column in audit:
            role = "audit_only"
            available_at = "not allowed as model input"
        else:
            role = "passthrough"
            available_at = "review before model use"
        rows.append(
            {
                "column": column,
                "role": role,
                "available_at": available_at,
            }
        )

    return pd.DataFrame(rows)
