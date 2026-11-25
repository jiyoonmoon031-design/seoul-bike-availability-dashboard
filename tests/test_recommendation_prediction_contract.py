import json
from pathlib import Path

from ai_service import bridge


def test_recommendation_uses_backend_predictions(monkeypatch):
    calls = []

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

    def fake_run(args):
        calls.append(args)

        input_path = Path(args[args.index("--input") + 1])

        payload = json.loads(input_path.read_text())

        assert payload["candidates"] == [candidate]

        output_path = Path(args[args.index("--output") + 1])

        output_path.write_text(
            json.dumps(
                {
                    "recommendations": [],
                    "warnings": [],
                }
            )
        )

    monkeypatch.setattr(bridge, "run_predict", unexpected_predict)

    monkeypatch.setattr(bridge, "_run", fake_run)

    bridge.run_recommendation(
        {
            "leg": "origin",
            "eta_min": 5,
            "top_n": 3,
            "candidates": [candidate],
        }
    )

    assert len(calls) == 1
    assert str(bridge.RECOMMEND_SCRIPT) in calls[0]
