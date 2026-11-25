from ai_service import bridge


def test_recommendation_uses_backend_predictions(monkeypatch):
    candidate = {
        "station_id": "ST-382",
        "station_name": "세종대학교 대양AI센터",
        "capacity": 20,
        "bikes_now": 10,
        "docks_now": 10,
        "distance_m": 120,
        "walk_min": 2,
        "eta_min": 5,
        "horizon_results": [
            {
                "horizon_min": horizon,
                "prediction_source": "baseline_fallback",
                "delta_net": -1.0,
                "bikes_expected": 9.0,
                "docks_expected": 11.0,
            }
            for horizon in (15, 30, 60)
        ],
    }

    def unexpected_predict(*args, **kwargs):
        raise AssertionError("Recommendation must not call prediction again")

    monkeypatch.setattr(bridge, "run_predict", unexpected_predict)
    result = bridge.run_recommendation(
        {
            "leg": "origin",
            "eta_min": 5,
            "top_n": 3,
            "candidates": [candidate],
        }
    )
    assert result["recommendations"][0]["station_id"] == "ST-382"
    assert result["runtime"]["total_ms"] >= 0


def test_recommendation_in_process_is_deterministic_across_twenty_warm_calls():
    payload = {
        "leg": "origin",
        "eta_min": 5,
        "top_n": 3,
        "candidates": [
            {
                "station_id": "ST-1",
                "station_name": "Station 1",
                "capacity": 20,
                "bikes_now": 10,
                "docks_now": 10,
                "distance_m": 120,
                "walk_min": 2,
                "eta_min": 5,
                "horizon_results": [
                    {"horizon_min": horizon, "delta_net": -1.0}
                    for horizon in (15, 30, 60)
                ],
            }
        ],
    }
    station_ids = []
    for _ in range(20):
        result = bridge.run_recommendation(payload)
        station_ids.append(result["recommendations"][0]["station_id"])
    assert station_ids == ["ST-1"] * 20
