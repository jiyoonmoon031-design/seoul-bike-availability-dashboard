import pytest

from src.recommendation.logic import (
    RecommendationConfig,
    interpolate_delta,
    recommend_stations,
)


def config():
    return RecommendationConfig(
        max_walk_m=800,
        avail_stable_target=3,
        distance_weight=0.5,
        availability_weight=0.5,
        horizons=(15, 30, 60),
    )


def candidate(
    station_id,
    *,
    distance=400,
    walk=6,
    capacity=20,
    bikes=5,
    deltas=(-3, -5, -7),
):
    return {
        "station_id": station_id,
        "station_name": station_id,
        "distance_m": distance,
        "walk_min": walk,
        "capacity": capacity,
        "bikes_now": bikes,
        "horizon_results": [
            {
                "horizon_min": 15,
                "delta_net": deltas[0],
            },
            {
                "horizon_min": 30,
                "delta_net": deltas[1],
            },
            {
                "horizon_min": 60,
                "delta_net": deltas[2],
            },
        ],
    }


def test_interpolate_zero_to_15():
    value, info = interpolate_delta(
        7.5,
        candidate("S")["horizon_results"],
    )

    assert value == pytest.approx(-1.5)
    assert info["anchors"] == [0, 15]
    assert info["method"] == "interpolation"


def test_interpolate_15_to_30():
    value, info = interpolate_delta(
        22.5,
        candidate("S")["horizon_results"],
    )

    assert value == pytest.approx(-4.0)
    assert info["anchors"] == [15, 30]


def test_eta_above_60_clamps():
    value, info = interpolate_delta(
        75,
        candidate("S")["horizon_results"],
    )

    assert value == pytest.approx(-7)
    assert info["method"] == "clamp"
    assert info["anchors"] == [60, 60]


def test_origin_uses_future_bikes_not_current_bikes():
    result = recommend_stations(
        [
            candidate(
                "A",
                bikes=10,
                deltas=(-9, -9, -9),
            ),
            candidate(
                "B",
                bikes=4,
                deltas=(0, 0, 0),
            ),
        ],
        leg="origin",
        eta_min=15,
        config=config(),
    )

    recs = result.response["recommendations"]

    assert recs[0]["station_id"] == "B"
    assert recs[0]["bikes_now"] == pytest.approx(4)
    assert recs[0]["bikes_expected"] == pytest.approx(4)

    a = next(item for item in recs if item["station_id"] == "A")

    assert a["bikes_now"] == pytest.approx(10)
    assert a["bikes_expected"] == pytest.approx(1)


def test_destination_uses_future_docks():
    result = recommend_stations(
        [
            candidate(
                "FULL",
                capacity=20,
                bikes=19,
                deltas=(1, 1, 1),
            ),
            candidate(
                "SPACE",
                capacity=20,
                bikes=15,
                deltas=(0, 0, 0),
            ),
        ],
        leg="destination",
        eta_min=15,
        config=config(),
    )

    assert result.response["recommendations"][0]["station_id"] == "SPACE"


def test_distance_score_zero_at_800m():
    result = recommend_stations(
        [
            candidate(
                "A",
                distance=800,
                bikes=10,
                deltas=(0, 0, 0),
            )
        ],
        leg="origin",
        eta_min=15,
        config=config(),
    )

    breakdown = result.response["recommendations"][0]["score_breakdown"]

    assert breakdown["distance"] == pytest.approx(0)


def test_availability_component_caps_at_weight():
    result = recommend_stations(
        [
            candidate(
                "A",
                bikes=10,
                deltas=(0, 0, 0),
            )
        ],
        leg="origin",
        eta_min=15,
        config=config(),
    )

    breakdown = result.response["recommendations"][0]["score_breakdown"]

    assert breakdown["availability"] == pytest.approx(0.5)


def test_top3_sorted_by_score():
    result = recommend_stations(
        [
            candidate("A", distance=100, bikes=5, deltas=(0, 0, 0)),
            candidate("B", distance=300, bikes=5, deltas=(0, 0, 0)),
            candidate("C", distance=500, bikes=5, deltas=(0, 0, 0)),
            candidate("D", distance=700, bikes=5, deltas=(0, 0, 0)),
        ],
        leg="origin",
        eta_min=15,
        config=config(),
        top_n=3,
    )

    recs = result.response["recommendations"]

    assert [item["station_id"] for item in recs] == [
        "A",
        "B",
        "C",
    ]
    assert [item["rank"] for item in recs] == [1, 2, 3]


def test_missing_horizon_skips_with_warning():
    broken = candidate("BROKEN")
    broken["horizon_results"] = broken["horizon_results"][:2]

    result = recommend_stations(
        [broken],
        leg="origin",
        eta_min=15,
        config=config(),
    )

    assert result.response["recommendations"] == []
    assert len(result.warnings) == 1
