import pytest

from src.rebalancing.logic import (
    RebalancingConfig,
    build_rebalancing_plan,
)

BASE_TIME = "2026-10-08T08:00:00+09:00"


def params():
    return {
        "HORIZONS": [
            15,
            30,
            60,
        ],
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


def config():
    return RebalancingConfig.from_params(params())


def station_prediction(
    station_id,
    capacity,
    expected,
):
    return {
        "station_id": station_id,
        "capacity": capacity,
        "bikes_now": (capacity / 2 if capacity else 0),
        "horizon_results": [
            {
                "horizon_min": horizon,
                "delta_net": 0.0,
                "bikes_expected": expected[horizon],
                "docks_expected": capacity - expected[horizon],
            }
            for horizon in (15, 30, 60)
        ],
    }


def prediction_response(
    stations,
):
    return {
        "request_id": "test-request",
        "base_time": BASE_TIME,
        "model_version": ("week05-random_forest-test"),
        "source": "model",
        "predictions": stations,
        "warnings": [],
    }


def context(
    station_id,
    *,
    lat,
    lon,
    demand=3.0,
):
    return {
        "station_id": station_id,
        "station_name": f"Station {station_id}",
        "latitude": lat,
        "longitude": lon,
        "same_dow_time_mean_rent": demand,
    }


def test_priority_and_basic_greedy_match():
    response = prediction_response(
        [
            station_prediction(
                "D",
                20,
                {
                    15: 5,
                    30: 2,
                    60: 1,
                },
            ),
            station_prediction(
                "S",
                20,
                {
                    15: 19,
                    30: 19,
                    60: 19,
                },
            ),
        ]
    )

    result = build_rebalancing_plan(
        response,
        [
            context(
                "D",
                lat=37.5500,
                lon=127.0500,
            ),
            context(
                "S",
                lat=37.5510,
                lon=127.0510,
            ),
        ],
        config=config(),
        horizon_min=30,
    )

    shortage = result.response["shortage_top"][0]

    assert shortage["station_id"] == "D"

    assert shortage["s_min"] == 4

    assert shortage["shortage"] == pytest.approx(2.0)

    assert shortage["urgency"] == pytest.approx(2.0)

    assert shortage["demand_weight"] == pytest.approx(1.0)

    assert shortage["priority_score"] == pytest.approx(4.0)

    assert shortage["risk_time"] == ("2026-10-08T08:30:00+09:00")

    assert result.response["move_matches"][0]["move_qty"] == 2


def test_zero_capacity_is_skipped_with_warning():
    response = prediction_response(
        [
            station_prediction(
                "BAD",
                0,
                {
                    15: 0,
                    30: 0,
                    60: 0,
                },
            )
        ]
    )

    result = build_rebalancing_plan(
        response,
        [
            context(
                "BAD",
                lat=37.55,
                lon=127.05,
            )
        ],
        config=config(),
        horizon_min=30,
    )

    assert result.response["shortage_top"] == []

    assert any("capacity" in warning for warning in result.warnings)


def test_no_supplier_within_radius_returns_empty_matches():
    response = prediction_response(
        [
            station_prediction(
                "D",
                20,
                {
                    15: 0,
                    30: 0,
                    60: 0,
                },
            ),
            station_prediction(
                "S",
                20,
                {
                    15: 19,
                    30: 19,
                    60: 19,
                },
            ),
        ]
    )

    result = build_rebalancing_plan(
        response,
        [
            context(
                "D",
                lat=37.55,
                lon=127.05,
            ),
            context(
                "S",
                lat=37.80,
                lon=127.30,
            ),
        ],
        config=config(),
        horizon_min=30,
    )

    assert result.response["move_matches"] == []


def test_supply_slack_below_one_is_not_matched():
    custom = params()

    custom["S_MIN"] = {
        "capacity_ratio": 0.95,
        "minimum": 1,
    }

    custom["E_MIN"] = {
        "capacity_ratio": 0.05,
        "minimum": 1,
    }

    response = prediction_response(
        [
            station_prediction(
                "D",
                20,
                {
                    15: 18,
                    30: 18,
                    60: 18,
                },
            ),
            station_prediction(
                "S",
                20,
                {
                    15: 19.5,
                    30: 19.5,
                    60: 19.5,
                },
            ),
        ]
    )

    result = build_rebalancing_plan(
        response,
        [
            context(
                "D",
                lat=37.55,
                lon=127.05,
            ),
            context(
                "S",
                lat=37.551,
                lon=127.051,
            ),
        ],
        config=(RebalancingConfig.from_params(custom)),
        horizon_min=30,
    )

    assert result.response["surplus_top"][0]["supply_slack"] == (pytest.approx(0.5))

    assert result.response["move_matches"] == []


def test_vehicle_capacity_caps_total_move_at_twenty():
    response = prediction_response(
        [
            station_prediction(
                "D",
                200,
                {
                    15: 0,
                    30: 0,
                    60: 0,
                },
            ),
            station_prediction(
                "S",
                200,
                {
                    15: 190,
                    30: 190,
                    60: 190,
                },
            ),
        ]
    )

    result = build_rebalancing_plan(
        response,
        [
            context(
                "D",
                lat=37.55,
                lon=127.05,
            ),
            context(
                "S",
                lat=37.551,
                lon=127.051,
            ),
        ],
        config=config(),
        horizon_min=30,
    )

    moved = sum(item["move_qty"] for item in result.response["move_matches"])

    assert moved == 20

    assert result.diagnostics["vehicle_capacity_remaining"] == 0

    assert result.diagnostics["unmatched_shortage_count"] == 1


def test_greedy_prefers_larger_supply_slack_before_distance():
    response = prediction_response(
        [
            station_prediction(
                "D",
                100,
                {
                    15: 10,
                    30: 10,
                    60: 10,
                },
            ),
            station_prediction(
                "S_BIG",
                100,
                {
                    15: 90,
                    30: 90,
                    60: 90,
                },
            ),
            station_prediction(
                "S_NEAR",
                100,
                {
                    15: 85,
                    30: 85,
                    60: 85,
                },
            ),
        ]
    )

    result = build_rebalancing_plan(
        response,
        [
            context(
                "D",
                lat=37.55,
                lon=127.05,
            ),
            context(
                "S_BIG",
                lat=37.55,
                lon=127.060,
            ),
            context(
                "S_NEAR",
                lat=37.55,
                lon=127.053,
            ),
        ],
        config=config(),
        horizon_min=30,
    )

    assert result.response["move_matches"][0]["from_station_id"] == ("S_BIG")


def test_incompatible_minimum_thresholds_are_skipped():
    response = prediction_response(
        [
            station_prediction(
                "TINY",
                1,
                {
                    15: 0.5,
                    30: 0.5,
                    60: 0.5,
                },
            )
        ]
    )

    result = build_rebalancing_plan(
        response,
        [
            context(
                "TINY",
                lat=37.55,
                lon=127.05,
            )
        ],
        config=config(),
        horizon_min=30,
    )

    assert result.response["shortage_top"] == []

    assert result.response["surplus_top"] == []

    assert any("S_min + E_min" in warning for warning in result.warnings)


def test_demand_weight_clipping_affects_priority_order():
    response = prediction_response(
        [
            station_prediction(
                "D_HIGH",
                20,
                {
                    15: 2,
                    30: 2,
                    60: 2,
                },
            ),
            station_prediction(
                "D_LOW",
                20,
                {
                    15: 2,
                    30: 2,
                    60: 2,
                },
            ),
            station_prediction(
                "S",
                20,
                {
                    15: 19,
                    30: 19,
                    60: 19,
                },
            ),
        ]
    )

    result = build_rebalancing_plan(
        response,
        [
            context(
                "D_HIGH",
                lat=37.5500,
                lon=127.0500,
                demand=10.0,
            ),
            context(
                "D_LOW",
                lat=37.5505,
                lon=127.0505,
                demand=1.0,
            ),
            context(
                "S",
                lat=37.5510,
                lon=127.0510,
                demand=1.0,
            ),
        ],
        config=config(),
        horizon_min=30,
    )

    high = result.response["shortage_top"][0]

    low = result.response["shortage_top"][1]

    assert high["station_id"] == "D_HIGH"
    assert low["station_id"] == "D_LOW"

    assert high["demand_weight"] == pytest.approx(2.0)

    assert low["demand_weight"] == pytest.approx(0.5)

    assert high["priority_score"] > low["priority_score"]


def test_over_capacity_prediction_is_available_as_rebalancing_supply():
    response = prediction_response(
        [
            station_prediction(
                "OVER",
                10,
                {15: 13, 30: 12, 60: 11},
            )
        ]
    )
    result = build_rebalancing_plan(
        response,
        [context("OVER", lat=37.55, lon=127.05)],
        config=config(),
        horizon_min=30,
    )
    assert result.response["surplus_top"][0]["station_id"] == "OVER"
    assert result.response["surplus_top"][0]["docks_expected"] == 0
    assert result.response["surplus_top"][0]["supply_slack"] == 10
