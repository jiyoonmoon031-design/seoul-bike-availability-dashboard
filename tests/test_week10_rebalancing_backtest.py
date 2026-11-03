import pytest

from src.evaluation.rebalancing_backtest import (
    evaluate_rebalancing_case,
    summarize_backtests,
)
from src.rebalancing.logic import (
    RebalancingConfig,
)


def config():
    return RebalancingConfig.from_params(
        {
            "HORIZONS": [15, 30, 60],
            "S_MIN": {
                "capacity_ratio": 0.20,
                "minimum": 1,
            },
            "E_MIN": {
                "capacity_ratio": 0.20,
                "minimum": 1,
            },
            "URGENCY": {
                15: 4.0,
                30: 2.0,
                60: 1.0,
            },
            "DEMAND_WEIGHT": {
                "minimum": 0.5,
                "maximum": 2.0,
            },
            "SEARCH_RADIUS_KM": 2.0,
            "VEHICLE_CAP": 20,
            "DETOUR_FACTOR": 1.3,
        }
    )


def station_prediction(
    station_id,
    bikes_expected,
):
    capacity = 10

    return {
        "station_id": station_id,
        "capacity": capacity,
        "bikes_now": bikes_expected,
        "horizon_results": [
            {
                "horizon_min": horizon,
                "delta_net": 0.0,
                "bikes_expected": bikes_expected,
                "docks_expected": (capacity - bikes_expected),
            }
            for horizon in (15, 30, 60)
        ],
    }


def prediction_response(
    stations,
):
    return {
        "request_id": "week10-test",
        "base_time": ("2026-11-02T09:00:00+09:00"),
        "model_version": "week10-test-model",
        "source": "model",
        "predictions": stations,
        "warnings": [],
    }


def context(
    station_id,
    lat,
    lon,
):
    return {
        "station_id": station_id,
        "station_name": station_id,
        "latitude": lat,
        "longitude": lon,
        "same_dow_time_mean_rent": 3.0,
    }


def test_rebalancing_reduces_shortage():
    prediction = prediction_response(
        [
            station_prediction("D", 0.0),
            station_prediction("S", 9.0),
        ]
    )

    result = evaluate_rebalancing_case(
        prediction,
        [
            context(
                "D",
                37.5500,
                127.0500,
            ),
            context(
                "S",
                37.5510,
                127.0510,
            ),
        ],
        config=config(),
        horizon_min=30,
    )

    assert result["shortage_score_before"] == pytest.approx(2.0)
    assert result["shortage_score_after"] == pytest.approx(0.0)
    assert result["shortage_reduction_rate"] == pytest.approx(1.0)
    assert result["shortage_station_count_before"] == 1
    assert result["shortage_station_count_after"] == 0
    assert result["move_qty_total"] == 2


def test_zero_shortage_has_no_rate():
    prediction = prediction_response(
        [
            station_prediction("N", 5.0),
        ]
    )

    result = evaluate_rebalancing_case(
        prediction,
        [
            context(
                "N",
                37.5500,
                127.0500,
            ),
        ],
        config=config(),
        horizon_min=30,
    )

    assert result["shortage_score_before"] == 0.0
    assert result["shortage_score_after"] == 0.0
    assert result["shortage_reduction_rate"] is None


def test_all_shortages_are_counted():
    prediction = prediction_response(
        [
            station_prediction("D1", 0.0),
            station_prediction("D2", 0.0),
        ]
    )

    result = evaluate_rebalancing_case(
        prediction,
        [
            context(
                "D1",
                37.5500,
                127.0500,
            ),
            context(
                "D2",
                37.5600,
                127.0600,
            ),
        ],
        config=config(),
        horizon_min=30,
    )

    assert result["shortage_station_count_before"] == 2
    assert result["shortage_score_before"] == pytest.approx(4.0)
    assert result["shortage_score_after"] == pytest.approx(4.0)


def test_summary_groups_by_horizon():
    records = [
        {
            "horizon_min": 15,
            "shortage_score_before": 4.0,
            "shortage_score_after": 2.0,
            "shortage_reduction_rate": 0.5,
            "shortage_station_count_before": 2,
            "shortage_station_count_after": 1,
            "shortage_station_count_reduction": 1,
            "move_match_count": 1,
            "move_qty_total": 2,
        },
        {
            "horizon_min": 15,
            "shortage_score_before": 6.0,
            "shortage_score_after": 3.0,
            "shortage_reduction_rate": 0.5,
            "shortage_station_count_before": 3,
            "shortage_station_count_after": 2,
            "shortage_station_count_reduction": 1,
            "move_match_count": 2,
            "move_qty_total": 3,
        },
    ]

    result = summarize_backtests(records)

    assert len(result) == 1
    assert result[0]["case_count"] == 2
    assert result[0]["shortage_score_before_total"] == pytest.approx(10.0)
    assert result[0]["shortage_score_after_total"] == pytest.approx(5.0)
    assert result[0]["shortage_reduction_rate"] == pytest.approx(0.5)
