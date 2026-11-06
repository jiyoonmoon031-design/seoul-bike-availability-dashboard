import pandas as pd
import pytest

from src.validation.recommendation import evaluate_top3


def rows():
    records = []
    scenarios = [
        ("rent-15", 15, "rent", [0, 1, 4]),
        ("rent-30", 30, "origin", [0, 0, 1]),
        ("rent-60", 60, "rent", [0, 0, 0]),
        ("return-15", 15, "return", [0, 2, 5]),
        ("return-30", 30, "destination", [0, 0, 1]),
        ("return-60", 60, "return", [0, 0, 0]),
    ]
    for request_id, horizon, mode, available_values in scenarios:
        for rank, available in enumerate(available_values, start=1):
            capacity = 10
            actual_bikes = (
                available if mode in {"rent", "origin"} else capacity - available
            )
            records.append(
                {
                    "request_id": request_id,
                    "base_time": "2026-07-01T08:00:00+09:00",
                    "origin_station_id": "ORIGIN",
                    "horizon_min": horizon,
                    "mode": mode,
                    "candidate_station_id": f"{request_id}-{rank}",
                    "rank": rank,
                    "actual_bikes": actual_bikes,
                    "capacity": capacity,
                }
            )
    return pd.DataFrame(records)


def test_horizon_hit_rates_for_minimum_threshold():
    result = evaluate_top3(rows())
    metrics = result.metrics
    minimum_rent = metrics[
        (metrics["scope"] == "horizon")
        & (metrics["mode"] == "rent")
        & (metrics["availability_threshold"] == 1)
    ]
    assert minimum_rent["hit_rate"].tolist() == [1.0, 1.0, 0.0]


def test_stable_threshold_is_evaluated_separately():
    result = evaluate_top3(rows())
    micro = result.metrics[
        (result.metrics["scope"] == "micro")
        & (result.metrics["mode"] == "rent")
        & (result.metrics["availability_threshold"] == 2)
    ].iloc[0]
    assert micro["eligible_requests"] == 3
    assert micro["hits"] == 1
    assert micro["hit_rate"] == pytest.approx(1 / 3)


def test_destination_uses_empty_docks():
    result = evaluate_top3(rows())
    request = result.request_results[
        (result.request_results["request_id"] == "return-15")
        & (result.request_results["availability_threshold"] == 2)
    ].iloc[0]
    assert request["max_actual_available"] == 5
    assert bool(request["hit"])


def test_invalid_inventory_is_rejected():
    invalid = rows()
    invalid.loc[0, "actual_bikes"] = 11
    with pytest.raises(ValueError, match="actual_bikes"):
        evaluate_top3(invalid)
