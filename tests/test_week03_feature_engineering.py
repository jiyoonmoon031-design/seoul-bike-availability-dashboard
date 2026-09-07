import pandas as pd
import pytest

from src.modeling.feature_engineering import (
    FeatureContractError,
    build_feature_manifest,
    build_week03_features,
    get_model_feature_columns,
)
from tests.week03_test_data import make_week02_panel


def test_features_use_only_activity_before_base_time() -> None:
    source = make_week02_panel(days=2)
    features = build_week03_features(source)
    row = features.loc[features["base_time"].eq(pd.Timestamp("2026-01-01 01:00"))].iloc[
        0
    ]

    assert row["rent_prev_15m"] == 3
    assert row["rent_prev_30m"] == 5
    assert row["rent_prev_60m"] == 6
    assert row["return_prev_15m"] == 0
    assert row["return_prev_30m"] == 3
    assert row["return_prev_60m"] == 6
    assert row["delta_prev_15m"] == -3
    assert row["delta_prev_30m"] == -2
    assert row["delta_prev_60m"] == 0
    assert bool(row["history_60m_available"])


def test_missing_source_day_is_not_converted_to_zero_history() -> None:
    source = make_week02_panel(days=3, missing_dates=("2026-01-02",))
    features = build_week03_features(source)
    row = features.loc[features["base_time"].eq(pd.Timestamp("2026-01-03 00:00"))].iloc[
        0
    ]

    assert pd.isna(row["rent_prev_15m"])
    assert pd.isna(row["delta_prev_60m"])
    assert not bool(row["history_15m_available"])
    assert not bool(row["history_24h_available"])


def test_feature_allowlist_excludes_current_activity_and_targets() -> None:
    features = build_week03_features(make_week02_panel(days=2))
    allowed = set(get_model_feature_columns(features))
    forbidden = {
        "rent_count",
        "return_count",
        "delta_hist",
        "delta_hist_h15",
        "delta_hist_h30",
        "delta_hist_h60",
        "is_observed",
    }

    assert allowed.isdisjoint(forbidden)
    manifest = build_feature_manifest(features).set_index("column")
    assert manifest.loc["delta_hist", "role"] == "audit_only"
    assert manifest.loc["delta_hist_h60", "role"] == "target"
    assert manifest.loc["delta_prev_60m", "role"] == "feature"


def test_future_weather_observation_is_rejected() -> None:
    source = make_week02_panel(days=2)
    source.loc[0, "weather_obs_time"] = pd.Timestamp(
        "2026-01-01 00:15", tz="Asia/Seoul"
    )

    with pytest.raises(FeatureContractError, match="future weather"):
        build_week03_features(source)


def test_target_contract_tampering_is_rejected() -> None:
    source = make_week02_panel(days=2)
    source.loc[0, "delta_hist_h30"] += 1

    with pytest.raises(FeatureContractError, match="forward delta sum"):
        build_week03_features(source)
