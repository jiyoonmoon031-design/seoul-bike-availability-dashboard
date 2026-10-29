import pandas as pd

from scripts.reproduce_week05_final_metrics import compare_metrics


def test_compare_metrics_accepts_serialization_tolerance() -> None:
    row = {
        "split": "test",
        "model_id": "random_forest",
        "segment": "ALL",
        "horizon_min": 15,
        "evaluated_rows": 10,
        "mae": 1.0,
        "rmse": 2.0,
        "b1_mae_same_rows": 1.5,
        "improvement_vs_b1": 1 / 3,
    }
    reproduced = pd.DataFrame([row])
    expected = pd.DataFrame([{**row, "mae": 1.0 + 1e-12}])

    comparison, maximum = compare_metrics(reproduced, expected, 1e-10)

    assert comparison["within_tolerance"].all()
    assert maximum < 1e-10
