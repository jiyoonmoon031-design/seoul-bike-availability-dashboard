from __future__ import annotations

from typing import Any

from src.llm.contracts import (
    OperatorBriefingPayload,
    UserRecommendationPayload,
)


def _station_name(
    station_id: str,
    station_names: dict[str, str],
) -> str:
    name = station_names.get(station_id)

    if not name:
        raise ValueError(f"station name missing: " f"{station_id}")

    return name


def build_operator_payload(
    rebalancing_response: dict[str, Any],
    station_names: dict[str, str],
) -> dict[str, Any]:
    shortages = []

    for item in rebalancing_response.get(
        "shortage_top",
        [],
    ):
        station_name = item.get("station_name") or _station_name(
            item["station_id"],
            station_names,
        )

        shortages.append(
            {
                "station_name": station_name,
                "bikes_expected": item["bikes_expected"],
                "s_min": item["s_min"],
                "risk_time": item["risk_time"],
            }
        )

    moves = []

    for item in rebalancing_response.get(
        "move_matches",
        [],
    ):
        moves.append(
            {
                "from_station_name": _station_name(
                    item["from_station_id"],
                    station_names,
                ),
                "to_station_name": _station_name(
                    item["to_station_id"],
                    station_names,
                ),
                "move_qty": item["move_qty"],
            }
        )

    payload = OperatorBriefingPayload(
        base_time=rebalancing_response["base_time"],
        horizon_min=rebalancing_response["horizon_min"],
        shortage_top=shortages,
        move_matches=moves,
    )

    return payload.model_dump()


def build_user_payload(
    recommendation_response: dict[str, Any],
) -> dict[str, Any]:
    candidates = []

    for item in recommendation_response.get(
        "recommendations",
        [],
    ):
        candidates.append(
            {
                "rank": item["rank"],
                "station_name": item["station_name"],
                "distance_m": item["distance_m"],
                "bikes_expected": item["bikes_expected"],
                "docks_expected": item["docks_expected"],
            }
        )

    payload = UserRecommendationPayload(
        leg=recommendation_response["leg"],
        eta_min=recommendation_response["eta_min"],
        candidates=candidates,
    )

    return payload.model_dump()
