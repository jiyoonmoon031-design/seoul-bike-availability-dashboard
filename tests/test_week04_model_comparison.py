from __future__ import annotations

import pandas as pd
from pandas.testing import assert_frame_equal

from src.modeling.feature_engineering import (
    build_week03_features,
    get_model_feature_columns,
)
from src.modeling.model_comparison import (
    MODEL_CANDIDATES,
    assign_purged_ratio_splits,
    evaluate_validation_comparison,
    fit_baselines,
    fit_candidate,
    make_wide_comparison_table,
    validate_week03_feature_allowlist,
)
from tests.week03_test_data import make_week02_panel

SMALL_PARAMETERS = {
    "linear_model": {
        "alpha": 1.0,
        "fit_intercept": True,
        "solver": "lsqr",
        "tol": 0.0001,
        "max_iter": 20,
    },
    "random_forest": {
        "n_estimators": 4,
        "max_depth": 4,
        "min_samples_leaf": 2,
        "max_features": 0.75,
        "bootstrap": True,
        "max_samples": 0.5,
        "n_jobs": 1,
    },
    "lightgbm": {
        "objective": "regression_l1",
        "n_estimators": 5,
        "learning_rate": 0.1,
        "num_leaves": 7,
        "min_child_samples": 5,
        "deterministic": True,
        "force_col_wise": True,
        "verbosity": -1,
        "n_jobs": 1,
    },
}


def _split_panel() -> tuple[pd.DataFrame, list[str]]:
    source = make_week02_panel(
        days=12,
        stations=("A", "B"),
        activity_scales=(1, 5),
    )
    features = build_week03_features(source)
    feature_columns = get_model_feature_columns(features)
    split = assign_purged_ratio_splits(features, gap_minutes=60)
    return split.frame, feature_columns


def _fit_all_candidates(
    frame: pd.DataFrame, feature_columns: list[str]
) -> dict[str, object]:
    return {
        model_id: fit_candidate(
            frame,
            model_id=model_id,
            feature_columns=feature_columns,
            seed=42,
            parameters=SMALL_PARAMETERS[model_id],
        )
        for model_id in MODEL_CANDIDATES
    }


def test_purged_split_uses_one_timestamp_partition_for_all_stations() -> None:
    frame, _ = _split_panel()
    by_time = frame.groupby("base_time")["split"].nunique()
    assert by_time.eq(1).all()

    timestamps = {
        split: pd.DatetimeIndex(
            frame.loc[frame["split"].eq(split), "base_time"].drop_duplicates()
        ).sort_values()
        for split in ("train", "validation", "test", "excluded_gap")
    }
    retained = sum(len(timestamps[split]) for split in ("train", "validation", "test"))
    assert len(timestamps["excluded_gap"]) == 8
    assert len(timestamps["train"]) == int(retained * 0.70)
    assert len(timestamps["validation"]) == int(retained * 0.15)
    assert len(timestamps["test"]) == retained - int(retained * 0.70) - int(
        retained * 0.15
    )

    ordered = frame[["base_time", "split"]].drop_duplicates().sort_values("base_time")
    first_validation = ordered.index[ordered["split"].eq("validation")][0]
    first_test = ordered.index[ordered["split"].eq("test")][0]
    assert (
        (ordered.loc[: first_validation - 1, "split"] == "excluded_gap").tail(4).all()
    )
    assert (ordered.loc[: first_test - 1, "split"] == "excluded_gap").tail(4).all()


def test_week03_allowlist_order_is_preserved_and_excludes_audit_columns() -> None:
    frame, feature_columns = _split_panel()
    assert validate_week03_feature_allowlist(frame, feature_columns) == feature_columns
    assert "rent_count" not in feature_columns
    assert "return_count" not in feature_columns
    assert "delta_hist_h15" not in feature_columns


def test_b3_predictions_are_fit_from_train_targets_only() -> None:
    frame, _ = _split_panel()
    baselines = fit_baselines(frame)
    validation = frame.loc[frame["split"].eq("validation")].copy()
    before = baselines.predict_all(validation, "b3_dow_time_mean")
    for horizon in (15, 30, 60):
        validation[f"delta_hist_h{horizon}"] = 999999.0
    after = baselines.predict_all(validation, "b3_dow_time_mean")
    for horizon in (15, 30, 60):
        assert (before[horizon] == after[horizon]).all()


def test_comparison_covers_six_models_four_segments_and_three_horizons() -> None:
    frame, feature_columns = _split_panel()
    baselines = fit_baselines(frame)
    candidates = _fit_all_candidates(frame, feature_columns)
    metrics, metadata = evaluate_validation_comparison(
        frame,
        baselines=baselines,
        candidates=candidates,
        active_percentile=0.75,
        timing_repeats=1,
    )
    table = make_wide_comparison_table(metrics)

    assert len(metrics) == 6 * 4 * 3
    assert len(table) == 6 * 4
    assert set(metrics["split"]) == {"validation"}
    assert set(metrics["segment"]) == {"ALL", "ACTIVE", "PEAK", "ACTIVE_PEAK"}
    assert set(metrics["horizon_min"]) == {15, 30, 60}
    assert metrics["evaluated_rows"].gt(0).all()
    assert metadata["test_targets_accessed"] is False
    assert metadata["test_metrics_generated"] is False
    assert metadata["test_reserved_for_week05"] is True
    for column in (
        "15m MAE",
        "30m MAE",
        "60m MAE",
        "15m RMSE",
        "30m RMSE",
        "60m RMSE",
        "15m Improvement vs B1",
        "30m Improvement vs B1",
        "60m Improvement vs B1",
        "Inference ms / 1k rows",
    ):
        assert column in table


def test_test_target_changes_do_not_change_week04_metrics() -> None:
    frame, feature_columns = _split_panel()
    baselines = fit_baselines(frame)
    candidates = _fit_all_candidates(frame, feature_columns)
    original, _ = evaluate_validation_comparison(
        frame,
        baselines=baselines,
        candidates=candidates,
        active_percentile=0.75,
        timing_repeats=1,
    )

    changed = frame.copy()
    test = changed["split"].eq("test")
    for horizon in (15, 30, 60):
        changed.loc[test, f"delta_hist_h{horizon}"] = -999999.0
        changed.loc[test, f"target_h{horizon}_valid"] = True
    after, _ = evaluate_validation_comparison(
        changed,
        baselines=baselines,
        candidates=candidates,
        active_percentile=0.75,
        timing_repeats=1,
    )

    stable_columns = [
        column
        for column in original.columns
        if column != "inference_time_ms_per_1k_rows"
    ]
    assert_frame_equal(original[stable_columns], after[stable_columns])
