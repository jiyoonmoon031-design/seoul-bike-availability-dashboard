import ai_service.bridge as bridge


def test_missing_horizon_results_are_enriched(
    monkeypatch,
):
    captured = {}

    def fake_predict(payload):
        captured.update(payload)

        return {
            "predictions": [
                {
                    "station_id": "ST-1760",
                    "capacity": 12,
                    "bikes_now": 4,
                    "horizon_results": [
                        {
                            "horizon_min": 15,
                            "prediction_source": "baseline_fallback",
                            "delta_net": -0.5,
                            "bikes_expected": 3.5,
                            "docks_expected": 8.5,
                        },
                        {
                            "horizon_min": 30,
                            "prediction_source": "baseline_fallback",
                            "delta_net": -1.0,
                            "bikes_expected": 3.0,
                            "docks_expected": 9.0,
                        },
                        {
                            "horizon_min": 60,
                            "prediction_source": "baseline_fallback",
                            "delta_net": -1.5,
                            "bikes_expected": 2.5,
                            "docks_expected": 9.5,
                        },
                    ],
                }
            ],
            "warnings": [
                {
                    "code": "FEATURE_ROW_NOT_FOUND",
                    "message": "feature row not found",
                    "station_id": "ST-1760",
                    "horizon_min": None,
                }
            ],
        }

    monkeypatch.setattr(
        bridge,
        "run_predict",
        fake_predict,
    )

    candidates = [
        {
            "station_id": "ST-1760",
            "station_name": "test station",
            "distance_m": 200.0,
            "capacity": 12,
            "bikes_now": 4,
            "horizon_results": [],
        }
    ]

    result = bridge._enrich_recommendation_candidates(candidates)

    assert captured["station_ids"] == ["ST-1760"]

    assert captured["horizons"] == [
        15,
        30,
        60,
    ]

    assert captured["base_time"].endswith("+09:00")

    station = result[0]

    assert len(station["horizon_results"]) == 3

    assert station["capacity"] == 12
    assert station["bikes_now"] == 4
    assert station["docks_now"] == 8

    assert all(
        item["prediction_source"] == "baseline_fallback"
        for item in station["horizon_results"]
    )
