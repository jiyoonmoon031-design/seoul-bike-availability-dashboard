import pandas as pd

from src.modeling.final_model import (
    build_parameter_trials,
    choose_final_model,
)


def test_parameter_trials_are_deterministic_and_keep_baseline_first():
    kwargs = {
        "fixed": {"n_jobs": -1},
        "search_space": {
            "n_estimators": [10, 20, 30],
            "max_depth": [5, 10],
        },
        "n_trials": 4,
        "seed": 42,
        "baseline_parameters": {
            "n_estimators": 10,
            "max_depth": 5,
        },
    }

    first = build_parameter_trials(**kwargs)
    second = build_parameter_trials(**kwargs)

    assert first == second
    assert first[0]["n_estimators"] == 10
    assert first[0]["max_depth"] == 5
    assert first[0]["n_jobs"] == -1
    assert len(first) == 4


def test_final_model_selection_uses_primary_before_inference():
    finalists = [
        {
            "model_id": "random_forest",
            "primary_active_peak_30m_mae": 2.20,
            "secondary_all_horizon_mean_mae": 1.20,
            "inference_time_ms_per_1k_rows": 300.0,
        },
        {
            "model_id": "lightgbm",
            "primary_active_peak_30m_mae": 2.25,
            "secondary_all_horizon_mean_mae": 1.10,
            "inference_time_ms_per_1k_rows": 100.0,
        },
    ]

    winner = choose_final_model(
        finalists,
        preferred_inference_max=200,
    )

    assert winner["model_id"] == "random_forest"
    assert winner["inference_preference_met"] is False


def test_secondary_metric_breaks_primary_tie():
    finalists = [
        {
            "model_id": "random_forest",
            "primary_active_peak_30m_mae": 2.20,
            "secondary_all_horizon_mean_mae": 1.30,
            "inference_time_ms_per_1k_rows": 100.0,
        },
        {
            "model_id": "lightgbm",
            "primary_active_peak_30m_mae": 2.20,
            "secondary_all_horizon_mean_mae": 1.20,
            "inference_time_ms_per_1k_rows": 190.0,
        },
    ]

    winner = choose_final_model(
        finalists,
        preferred_inference_max=200,
    )

    assert winner["model_id"] == "lightgbm"
