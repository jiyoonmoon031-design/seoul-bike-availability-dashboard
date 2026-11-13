import pytest

from src.evaluation.oracle_rebalancing import (
    evaluate_oracle_case,
)
from src.rebalancing.logic import (
    RebalancingConfig,
)


def config():
    return RebalancingConfig.from_params(
        {
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
    )


def station(
    station_id,
    lat,
    lon,
    future,
    demand=3.0,
):
    return {
        "station_id": station_id,
        "station_name": station_id,
        "district": "광진구",
        "latitude": lat,
        "longitude": lon,
        "rack_count": 20,
        "bikes_now": 10,
        "same_dow_time_mean_rent": (demand),
        "future_bikes_by_horizon": (future),
    }


def test_oracle_accepts_over_rack_supply():
    from datetime import datetime

    result = evaluate_oracle_case(
        [
            station(
                "D",
                37.55,
                127.05,
                {
                    15: 5,
                    30: 1,
                    60: 0,
                },
            ),
            station(
                "S",
                37.551,
                127.051,
                {
                    15: 25,
                    30: 25,
                    60: 25,
                },
            ),
        ],
        base_time=datetime(
            2026,
            9,
            1,
            8,
            0,
        ),
        config=config(),
        horizon_min=30,
    )

    detail = result["detail"]

    assert detail["shortage_score_before"] == pytest.approx(3.0)

    assert detail["shortage_score_after"] == pytest.approx(0.0)

    assert detail["move_qty_total"] == pytest.approx(3.0)

    assert detail["over_rack_station_count_before"] == 1


def test_demand_weight_matches_week06():
    from datetime import datetime

    result = evaluate_oracle_case(
        [
            station(
                "HIGH",
                37.55,
                127.05,
                {
                    15: 0,
                    30: 0,
                    60: 0,
                },
                demand=6.0,
            ),
            station(
                "LOW",
                37.56,
                127.06,
                {
                    15: 0,
                    30: 0,
                    60: 0,
                },
                demand=3.0,
            ),
        ],
        base_time=datetime(
            2026,
            9,
            1,
            8,
            0,
        ),
        config=config(),
        horizon_min=30,
    )

    effects = {row["station_id"]: row for row in result["station_effects"]}

    assert effects["HIGH"]["demand_weight"] == pytest.approx(6.0 / 4.5)

    assert effects["LOW"]["demand_weight"] == pytest.approx(3.0 / 4.5)
