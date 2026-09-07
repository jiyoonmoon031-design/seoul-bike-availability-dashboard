import pandas as pd

from src.modeling.feature_engineering import build_week03_features
from src.modeling.naive_baseline import (
    add_naive_predictions,
    assign_chronological_splits,
    evaluate_naive_baselines,
)
from tests.week03_test_data import make_week02_panel


def test_persistence_uses_target_window_ending_at_base_time() -> None:
    source = build_week03_features(make_week02_panel(days=2))
    predictions = add_naive_predictions(source)
    current = predictions.loc[
        predictions["base_time"].eq(pd.Timestamp("2026-01-01 01:00"))
    ].iloc[0]
    prior_h30 = predictions.loc[
        predictions["base_time"].eq(pd.Timestamp("2026-01-01 00:30")),
        "delta_hist_h30",
    ].iloc[0]

    assert current["prediction_persistence_h30"] == prior_h30
    assert bool(current["persistence_h30_available"])
    assert current["prediction_zero_h30"] == 0


def test_chronological_split_uses_complete_days_only() -> None:
    source = build_week03_features(
        make_week02_panel(days=9, missing_dates=("2026-01-04",))
    )
    predictions = add_naive_predictions(source)
    split = assign_chronological_splits(
        predictions,
        validation_days=2,
        test_days=2,
        minimum_history_days=2,
    )

    assert set(
        split.loc[
            split["base_time"].dt.normalize().eq(pd.Timestamp("2026-01-04")),
            "split",
        ]
    ) == {"excluded"}
    assert split.attrs["split_metadata"]["train_complete_days"] == 4
    assert split.attrs["split_metadata"]["validation_complete_days"] == 2
    assert split.attrs["split_metadata"]["test_complete_days"] == 2


def test_baseline_metrics_cover_horizons_micro_and_segments() -> None:
    source = build_week03_features(
        make_week02_panel(
            days=8,
            stations=("A", "B"),
            activity_scales=(1, 10),
        )
    )
    predictions = add_naive_predictions(source)
    split = assign_chronological_splits(
        predictions,
        validation_days=2,
        test_days=2,
        minimum_history_days=2,
    )
    metrics = evaluate_naive_baselines(split, active_percentile=0.75)

    assert len(metrics) == 64
    assert set(metrics["scope"]) == {"horizon", "micro"}
    assert set(metrics["segment"]) == {"ALL", "ACTIVE", "PEAK", "ACTIVE_PEAK"}
    assert set(metrics["baseline"]) == {"persistence", "zero"}
    assert set(metrics["split"]) == {"validation", "test"}
    assert metrics["evaluated_rows"].gt(0).all()
