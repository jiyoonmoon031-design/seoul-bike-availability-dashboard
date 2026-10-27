from fastapi.testclient import (
    TestClient,
)

import ai_service.app as app_module

from ai_service.schemas import (
    PredictionRequest,
)


VALID_REQUEST = {
    "request_id": (
        "550e8400-e29b-41d4-a716-446655440000"
    ),
    "base_time": (
        "2026-10-15T08:30:00+09:00"
    ),
    "station_ids": [
        "ST-0001",
        "ST-0002",
    ],
    "horizons": [
        15,
        30,
        60,
    ],
}


def test_prediction_schema_has_only_public_fields():
    schema = (
        PredictionRequest
        .model_json_schema()
    )

    assert set(
        schema["properties"]
    ) == {
        "request_id",
        "base_time",
        "station_ids",
        "horizons",
    }

    assert (
        schema.get(
            "additionalProperties"
        )
        is False
    )


def test_predict_accepts_original_contract(
    monkeypatch,
):
    captured = {}

    def fake_predict(payload):
        captured.update(payload)

        return {
            "request_id":
                payload["request_id"],
            "predictions": [],
            "warnings": [],
        }

    monkeypatch.setattr(
        app_module,
        "run_predict",
        fake_predict,
    )

    client = TestClient(
        app_module.app
    )

    response = client.post(
        "/predict",
        json=VALID_REQUEST,
    )

    assert response.status_code == 200

    assert set(
        captured
    ) == {
        "request_id",
        "base_time",
        "station_ids",
        "horizons",
    }

    assert captured[
        "horizons"
    ] == [
        15,
        30,
        60,
    ]


def test_old_predict_envelope_is_rejected():
    client = TestClient(
        app_module.app
    )

    response = client.post(
        "/predict",
        json={
            "request": {},
            "inventory": {},
        },
    )

    assert response.status_code == 422


def test_naive_base_time_is_rejected():
    payload = dict(
        VALID_REQUEST
    )

    payload["base_time"] = (
        "2026-10-15T08:30:00"
    )

    client = TestClient(
        app_module.app
    )

    response = client.post(
        "/predict",
        json=payload,
    )

    assert response.status_code == 422
