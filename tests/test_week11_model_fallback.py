import numpy as np
import pandas as pd
import pytest

from src.modeling.inference import build_prediction_response


class PassthroughPreprocessor:
    def transform(self, frame):
        return frame[["feature_x"]].to_numpy(dtype=np.float32)

    def get_feature_names_out(self):
        return np.array(["feature_x"])


class StaticEstimator:
    def __init__(self, value=None, error=None):
        self.value = value
        self.error = error

    def predict(self, transformed):
        if self.error is not None:
            raise self.error

        return np.array([self.value], dtype=np.float64)


class IsolatedCandidate:
    model_id = "random_forest"
    feature_columns = ["station_id", "feature_x"]

    def __init__(
        self,
        *,
        value_15=1.0,
        value_30=2.0,
        value_60=3.0,
        error_15=None,
        error_30=None,
        error_60=None,
    ):
        self.preprocessor = PassthroughPreprocessor()

        self.estimators = {
            15: StaticEstimator(value_15, error_15),
            30: StaticEstimator(value_30, error_30),
            60: StaticEstimator(value_60, error_60),
        }


class FakeBaselines:
    def __init__(self, values):
        self.values = values

    def predict_all(self, frame, baseline_id):
        assert baseline_id == "b3_dow_time_mean"

        return {
            horizon: np.array([value], dtype=np.float64)
            for horizon, value in self.values.items()
        }


def request(horizons=None):
    return {
        "request_id": "550e8400-e29b-41d4-a716-446655440000",
        "base_time": "2026-10-15T08:30:00+09:00",
        "station_ids": ["ST-0001"],
        "horizons": horizons or [15, 30, 60],
    }


def frame():
    return pd.DataFrame(
        {
            "station_id": ["ST-0001"],
            "feature_x": [1.0],
        }
    )


def inventory():
    return {
        "ST-0001": {
            "capacity": 20,
            "bikes_now": 10,
        }
    }


def horizon_map(response):
    return {
        item["horizon_min"]: item
        for item in response["predictions"][0]["horizon_results"]
    }


def test_normal_model_predictions_keep_model_source():
    response = build_prediction_response(
        candidate=IsolatedCandidate(
            value_15=1.0,
            value_30=-2.0,
            value_60=3.0,
        ),
        request=request(),
        feature_frame=frame(),
        inventory=inventory(),
        model_version="week11-test",
    )

    results = horizon_map(response)

    assert results[15]["prediction_source"] == "model"
    assert results[30]["prediction_source"] == "model"
    assert results[60]["prediction_source"] == "model"

    assert results[15]["bikes_expected"] == pytest.approx(11.0)
    assert results[30]["bikes_expected"] == pytest.approx(8.0)
    assert results[60]["bikes_expected"] == pytest.approx(13.0)

    assert response["warnings"] == []


def test_single_horizon_failure_uses_b3_without_dropping_other_horizons():
    response = build_prediction_response(
        candidate=IsolatedCandidate(
            value_15=1.0,
            error_30=RuntimeError("30m estimator failure"),
            value_60=-2.0,
        ),
        request=request(),
        feature_frame=frame(),
        inventory=inventory(),
        model_version="week11-test",
        baselines=FakeBaselines(
            {
                15: 9.0,
                30: -4.0,
                60: 9.0,
            }
        ),
    )

    results = horizon_map(response)

    assert results[15]["prediction_source"] == "model"
    assert results[15]["delta_net"] == pytest.approx(1.0)

    assert results[30]["prediction_source"] == "baseline_fallback"
    assert results[30]["delta_net"] == pytest.approx(-4.0)
    assert results[30]["bikes_expected"] == pytest.approx(6.0)

    assert results[60]["prediction_source"] == "model"
    assert results[60]["delta_net"] == pytest.approx(-2.0)

    warnings = response["warnings"]

    assert len(warnings) == 1
    assert warnings[0]["code"] == "BASELINE_FALLBACK"
    assert warnings[0]["station_id"] == "ST-0001"
    assert warnings[0]["horizon_min"] == 30
    assert "b3_dow_time_mean" in warnings[0]["message"]


def test_non_finite_model_prediction_uses_b3():
    response = build_prediction_response(
        candidate=IsolatedCandidate(
            value_15=np.nan,
            value_30=1.0,
            value_60=1.0,
        ),
        request=request([15]),
        feature_frame=frame(),
        inventory=inventory(),
        model_version="week11-test",
        baselines=FakeBaselines(
            {
                15: 2.5,
                30: 0.0,
                60: 0.0,
            }
        ),
    )

    result = horizon_map(response)[15]

    assert result["prediction_source"] == "baseline_fallback"
    assert result["delta_net"] == pytest.approx(2.5)
    assert result["bikes_expected"] == pytest.approx(12.5)

    warning = response["warnings"][0]

    assert warning["code"] == "BASELINE_FALLBACK"
    assert warning["horizon_min"] == 15


def test_b1_persistence_is_final_fallback_when_b3_is_unavailable():
    response = build_prediction_response(
        candidate=IsolatedCandidate(
            error_15=RuntimeError("model unavailable"),
            error_30=RuntimeError("model unavailable"),
            error_60=RuntimeError("model unavailable"),
        ),
        request=request(),
        feature_frame=frame(),
        inventory=inventory(),
        model_version="week11-test",
        baselines=None,
    )

    results = horizon_map(response)

    for horizon in (15, 30, 60):
        assert results[horizon]["prediction_source"] == "baseline_fallback"
        assert results[horizon]["delta_net"] == pytest.approx(0.0)
        assert results[horizon]["bikes_expected"] == pytest.approx(10.0)
        assert results[horizon]["docks_expected"] == pytest.approx(10.0)

    assert len(response["warnings"]) == 3

    assert all(
        warning["code"] == "BASELINE_FALLBACK" for warning in response["warnings"]
    )

    assert all(
        "b1_persistence" in warning["message"] for warning in response["warnings"]
    )


def test_b3_non_finite_value_falls_through_to_b1():
    response = build_prediction_response(
        candidate=IsolatedCandidate(
            error_30=RuntimeError("model unavailable"),
        ),
        request=request([30]),
        feature_frame=frame(),
        inventory=inventory(),
        model_version="week11-test",
        baselines=FakeBaselines(
            {
                15: 0.0,
                30: np.nan,
                60: 0.0,
            }
        ),
    )

    result = horizon_map(response)[30]

    assert result["prediction_source"] == "baseline_fallback"
    assert result["delta_net"] == pytest.approx(0.0)
    assert result["bikes_expected"] == pytest.approx(10.0)

    assert "b1_persistence" in response["warnings"][0]["message"]


def test_missing_feature_column_is_station_failure_not_silent_imputation():
    missing_column_frame = pd.DataFrame(
        {
            "station_id": ["ST-0001"],
        }
    )

    response = build_prediction_response(
        candidate=IsolatedCandidate(),
        request=request(),
        feature_frame=missing_column_frame,
        inventory=inventory(),
        model_version="week11-test",
    )

    station = response["predictions"][0]

    assert station["horizon_results"] == []

    assert response["warnings"] == [
        {
            "code": "FEATURE_UNAVAILABLE",
            "message": (
                "required model feature columns are unavailable: " "['feature_x']"
            ),
            "station_id": "ST-0001",
        }
    ]


def test_fallback_result_is_still_clipped_to_capacity():
    response = build_prediction_response(
        candidate=IsolatedCandidate(
            error_60=RuntimeError("model unavailable"),
        ),
        request=request([60]),
        feature_frame=frame(),
        inventory=inventory(),
        model_version="week11-test",
        baselines=FakeBaselines(
            {
                15: 0.0,
                30: 0.0,
                60: 1000.0,
            }
        ),
    )

    result = horizon_map(response)[60]

    assert result["prediction_source"] == "baseline_fallback"
    assert result["delta_net"] == pytest.approx(1000.0)
    assert result["bikes_expected"] == pytest.approx(20.0)
    assert result["docks_expected"] == pytest.approx(0.0)


def test_feature_loader_preserves_row_when_model_column_is_missing(
    tmp_path,
):
    from src.modeling.inference import (
        load_point_in_time_features,
    )

    source = pd.DataFrame(
        {
            "station_id": ["ST-0001"],
            "base_time": [
                pd.Timestamp(
                    "2026-10-15 08:30:00",
                    tz="Asia/Seoul",
                )
            ],
            "feature_x": [1.0],
        }
    )

    path = tmp_path / "features.parquet"
    source.to_parquet(path, index=False)

    loaded = load_point_in_time_features(
        path,
        feature_columns=[
            "feature_x",
            "feature_y",
        ],
        station_ids=["ST-0001"],
        base_time="2026-10-15T08:30:00+09:00",
    )

    assert len(loaded) == 1
    assert loaded.iloc[0]["station_id"] == "ST-0001"
    assert "feature_x" in loaded.columns
    assert "feature_y" not in loaded.columns
