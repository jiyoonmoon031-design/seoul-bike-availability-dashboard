import numpy as np
import pandas as pd
import pytest

from src.modeling.inference import (
    build_prediction_response,
    validate_prediction_request,
)


class FakeCandidate:
    model_id = "random_forest"
    feature_columns = [
        "station_id",
        "feature_x",
    ]

    def predict_all(self, frame):
        assert list(frame["station_id"]) == ["ST-0001"]

        return {
            15: np.array([-3.2]),
            30: np.array([-6.5]),
            60: np.array([12.0]),
        }


def valid_request():
    return {
        "request_id": "550e8400-e29b-41d4-a716-446655440000",
        "base_time": "2026-10-15T08:30:00+09:00",
        "station_ids": [
            "ST-0001",
            "ST-9999",
        ],
        "horizons": [
            15,
            30,
            60,
        ],
    }


def test_request_requires_kst_timezone():
    payload = valid_request()
    payload["base_time"] = "2026-10-15T08:30:00"

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        validate_prediction_request(payload)


def test_request_rejects_unsupported_horizon():
    payload = valid_request()
    payload["horizons"] = [
        15,
        45,
    ]

    with pytest.raises(
        ValueError,
        match="unsupported horizons",
    ):
        validate_prediction_request(payload)


def test_prediction_response_contract_and_clipping():
    frame = pd.DataFrame(
        {
            "station_id": [
                "ST-0001",
            ],
            "feature_x": [
                1.0,
            ],
        }
    )

    inventory = {
        "ST-0001": {
            "capacity": 20,
            "bikes_now": 12,
        },
        "ST-9999": {
            "capacity": 20,
            "bikes_now": 5,
        },
    }

    response = build_prediction_response(
        candidate=FakeCandidate(),
        request=valid_request(),
        feature_frame=frame,
        inventory=inventory,
        model_version=("week05-random_forest-test"),
    )

    assert response["source"] == "model"
    assert response["model_version"] == "week05-random_forest-test"

    assert len(response["predictions"]) == 2

    station = response["predictions"][0]

    results = {item["horizon_min"]: item for item in station["horizon_results"]}

    assert results[15]["bikes_expected"] == pytest.approx(8.8)

    assert results[15]["docks_expected"] == pytest.approx(11.2)

    assert results[30]["bikes_expected"] == pytest.approx(5.5)

    assert results[60]["bikes_expected"] == pytest.approx(20.0)

    assert results[60]["docks_expected"] == pytest.approx(0.0)

    missing = response["predictions"][1]

    assert missing["station_id"] == "ST-9999"

    assert missing["horizon_results"] == []

    assert results[15]["prediction_source"] == "model"
    assert results[30]["prediction_source"] == "model"
    assert results[60]["prediction_source"] == "model"

    assert any(
        warning["code"] == "FEATURE_ROW_NOT_FOUND"
        and warning.get("station_id") == "ST-9999"
        for warning in response["warnings"]
    )
