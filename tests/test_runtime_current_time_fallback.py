from __future__ import annotations

import numpy as np
import pandas as pd

from src.modeling.runtime_fallback import (
    _runtime_b3_frame,
    apply_runtime_feature_fallback,
)


class FakeBaselines:
    def predict_all(self, frame: pd.DataFrame, baseline_id: str):
        assert baseline_id == "b3_dow_time_mean"
        assert frame.loc[0, "station_id"] == "ST-1660"
        assert frame.loc[0, "weekday_index"] == 6
        assert frame.loc[0, "hour"] == 19
        assert frame.loc[0, "minute"] == 45
        return {
            15: np.array([-0.2]),
            30: np.array([-0.4]),
            60: np.array([-0.8]),
        }


class BrokenBaselines:
    def predict_all(self, frame: pd.DataFrame, baseline_id: str):
        raise RuntimeError("forced B3 failure")


def base_response():
    return {
        "request_id": "runtime-test",
        "base_time": "2026-11-22T19:45:00+09:00",
        "model_version": "week05-random_forest-test",
        "source": "model",
        "predictions": [
            {
                "station_id": "ST-1660",
                "horizon_results": [],
                "capacity": 10,
                "bikes_now": 5,
            }
        ],
        "warnings": [
            {
                "code": "FEATURE_ROW_NOT_FOUND",
                "message": "feature row not found for base_time",
                "station_id": "ST-1660",
                "horizon_min": None,
            }
        ],
    }


def request():
    return {
        "request_id": "runtime-test",
        "base_time": "2026-11-22T19:45:00+09:00",
        "station_ids": ["ST-1660"],
        "horizons": [15, 30, 60],
    }


def inventory():
    return {"ST-1660": {"capacity": 10, "bikes_now": 5}}


def test_runtime_b3_frame_uses_kst_request_time():
    frame = _runtime_b3_frame(station_id="ST-1660", base_time="2026-11-22T10:45:00Z")
    assert frame.to_dict("records") == [
        {
            "station_id": "ST-1660",
            "weekday_index": 6,
            "hour": 19,
            "minute": 45,
        }
    ]


def test_missing_feature_row_gets_b3_runtime_fallback():
    result = apply_runtime_feature_fallback(
        response=base_response(),
        request=request(),
        inventory=inventory(),
        baselines=FakeBaselines(),
    )
    station = result["predictions"][0]
    horizons = {item["horizon_min"]: item for item in station["horizon_results"]}
    assert set(horizons) == {15, 30, 60}
    assert all(
        item["prediction_source"] == "baseline_fallback" for item in horizons.values()
    )
    assert horizons[15]["bikes_expected"] == 4.8
    assert horizons[30]["bikes_expected"] == 4.6
    assert horizons[60]["bikes_expected"] == 4.2
    assert len([w for w in result["warnings"] if w["code"] == "BASELINE_FALLBACK"]) == 3
    for warning in result["warnings"]:
        assert set(warning) == {"code", "message", "station_id", "horizon_min"}


def test_b1_is_final_fallback_when_b3_fails():
    result = apply_runtime_feature_fallback(
        response=base_response(),
        request=request(),
        inventory=inventory(),
        baselines=BrokenBaselines(),
    )
    for item in result["predictions"][0]["horizon_results"]:
        assert item["prediction_source"] == "baseline_fallback"
        assert item["delta_net"] == 0.0
        assert item["bikes_expected"] == 5.0
        assert item["docks_expected"] == 5.0


def test_historical_model_result_is_not_overwritten():
    response = base_response()
    response["predictions"][0]["horizon_results"] = [
        {
            "horizon_min": 30,
            "prediction_source": "model",
            "delta_net": -0.4,
            "bikes_expected": 4.6,
            "docks_expected": 5.4,
        }
    ]
    result = apply_runtime_feature_fallback(
        response=response,
        request=request(),
        inventory=inventory(),
        baselines=FakeBaselines(),
    )
    assert (
        result["predictions"][0]["horizon_results"]
        == response["predictions"][0]["horizon_results"]
    )
