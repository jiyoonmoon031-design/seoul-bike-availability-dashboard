from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any, Mapping, Sequence

from src.rebalancing.logic import RebalancingConfig, haversine_km

EPSILON = 1e-9


def _finite_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(number):
        return None

    return number


def _minimum_level(
    rack_count: float,
    *,
    ratio: float,
    minimum: int,
) -> int:
    return max(
        int(minimum),
        int(math.ceil(ratio * rack_count)),
    )


def _demand_weights(
    prepared: Sequence[dict[str, Any]],
    config: RebalancingConfig,
) -> tuple[dict[str, float], float | None, list[str]]:
    warnings: list[str] = []
    observed: dict[str, float] = {}

    for station in prepared:
        value = _finite_float(station.get("same_dow_time_mean_rent"))

        if value is not None and value >= 0:
            observed[station["station_id"]] = value

    if not observed:
        warnings.append("demand weight input unavailable; " "using neutral weight 1.0")

        return (
            {station["station_id"]: 1.0 for station in prepared},
            None,
            warnings,
        )

    area_mean = sum(observed.values()) / len(observed)

    if area_mean <= EPSILON:
        warnings.append("area mean demand is zero; " "using neutral weight 1.0")

        return (
            {station["station_id"]: 1.0 for station in prepared},
            area_mean,
            warnings,
        )

    weights: dict[str, float] = {}

    for station in prepared:
        station_id = station["station_id"]
        value = observed.get(station_id)

        if value is None:
            weights[station_id] = 1.0
            warnings.append(
                f"{station_id}: demand mean missing; " "using neutral weight 1.0"
            )
            continue

        raw = value / area_mean

        weights[station_id] = min(
            config.demand_weight_max,
            max(
                config.demand_weight_min,
                raw,
            ),
        )

    return weights, area_mean, warnings


def evaluate_oracle_case(
    stations: Sequence[Mapping[str, Any]],
    *,
    base_time: datetime,
    config: RebalancingConfig,
    horizon_min: int,
    distance_lookup: (
        Mapping[
            tuple[str, str],
            float,
        ]
        | None
    ) = None,
) -> dict[str, Any]:
    if horizon_min not in config.horizons:
        raise ValueError(f"unsupported horizon: {horizon_min}")

    warnings: list[str] = []
    prepared: list[dict[str, Any]] = []

    for station in stations:
        station_id = station.get("station_id")

        if not isinstance(station_id, str):
            continue

        rack_count = _finite_float(station.get("rack_count"))

        latitude = _finite_float(station.get("latitude"))
        longitude = _finite_float(station.get("longitude"))

        if (
            rack_count is None
            or rack_count <= 0
            or latitude is None
            or longitude is None
        ):
            warnings.append(f"{station_id}: invalid metadata")
            continue

        s_min = _minimum_level(
            rack_count,
            ratio=config.s_min_ratio,
            minimum=config.s_minimum,
        )

        e_min = _minimum_level(
            rack_count,
            ratio=config.e_min_ratio,
            minimum=config.e_minimum,
        )

        if s_min + e_min > rack_count:
            warnings.append(
                f"{station_id}: S_min + E_min " "exceeds rack count; skipped"
            )
            continue

        future_raw = station.get("future_bikes_by_horizon")

        if not isinstance(future_raw, Mapping):
            continue

        future_by_horizon: dict[int, float] = {}

        for key, value in future_raw.items():
            try:
                horizon = int(key)
            except (TypeError, ValueError):
                continue

            number = _finite_float(value)

            if number is None or number < 0:
                continue

            future_by_horizon[horizon] = number

        selected = future_by_horizon.get(horizon_min)

        if selected is None:
            continue

        prepared.append(
            {
                "station_id": station_id,
                "station_name": str(
                    station.get(
                        "station_name",
                        station_id,
                    )
                ),
                "district": station.get("district"),
                "latitude": latitude,
                "longitude": longitude,
                "rack_count": rack_count,
                "bikes_now": _finite_float(station.get("bikes_now")),
                "s_min": s_min,
                "e_min": e_min,
                "future_bikes": selected,
                "future_bikes_by_horizon": (future_by_horizon),
                "same_dow_time_mean_rent": (
                    _finite_float(station.get("same_dow_time_mean_rent"))
                ),
            }
        )

    demand_weights, area_mean, demand_warnings = _demand_weights(
        prepared,
        config,
    )

    warnings.extend(demand_warnings)

    states: list[dict[str, Any]] = []

    for station in prepared:
        future_bikes = station["future_bikes"]
        rack_count = station["rack_count"]

        future_empty_racks = max(
            0.0,
            rack_count - future_bikes,
        )

        shortage = max(
            0.0,
            station["s_min"] - future_bikes,
        )

        overflow = max(
            0.0,
            station["e_min"] - future_empty_racks,
        )

        risk_horizon: int | None = None

        for horizon in sorted(config.horizons):
            value = station["future_bikes_by_horizon"].get(horizon)

            if value is not None and value < station["s_min"]:
                risk_horizon = horizon
                break

        urgency = (
            config.urgency.get(
                risk_horizon,
                0.0,
            )
            if risk_horizon is not None
            else 0.0
        )

        demand_weight = demand_weights[station["station_id"]]

        priority_score = shortage * urgency * demand_weight

        supply_slack = (
            max(
                0.0,
                future_bikes - station["s_min"],
            )
            if overflow > EPSILON
            else 0.0
        )

        risk_time = None

        if risk_horizon is not None:
            risk_time = (base_time + timedelta(minutes=risk_horizon)).isoformat()

        states.append(
            {
                **station,
                "future_empty_racks": (future_empty_racks),
                "shortage": shortage,
                "overflow": overflow,
                "urgency": urgency,
                "demand_weight": (demand_weight),
                "priority_score": (priority_score),
                "supply_slack": (supply_slack),
                "risk_horizon": (risk_horizon),
                "risk_time": risk_time,
            }
        )

    shortage_states = sorted(
        (state for state in states if state["shortage"] > EPSILON),
        key=lambda item: (
            -item["priority_score"],
            -item["shortage"],
            item["station_id"],
        ),
    )

    surplus_states = sorted(
        (
            state
            for state in states
            if state["overflow"] > EPSILON and state["supply_slack"] > EPSILON
        ),
        key=lambda item: (
            -item["supply_slack"],
            item["station_id"],
        ),
    )

    remaining_supply = {
        item["station_id"]: (item["supply_slack"]) for item in surplus_states
    }

    remaining_shortage = {
        item["station_id"]: (item["shortage"]) for item in shortage_states
    }

    vehicle_remaining = int(config.vehicle_cap)

    move_matches: list[dict[str, Any]] = []

    for demand in shortage_states:
        if vehicle_remaining < 1:
            break

        demand_id = demand["station_id"]

        candidates: list[tuple[dict[str, Any], float]] = []

        for supply in surplus_states:
            supply_id = supply["station_id"]

            if (
                remaining_supply.get(
                    supply_id,
                    0.0,
                )
                < 1.0
            ):
                continue

            if distance_lookup is None:
                distance_km = (
                    haversine_km(
                        demand["latitude"],
                        demand["longitude"],
                        supply["latitude"],
                        supply["longitude"],
                    )
                    * config.detour_factor
                )
            else:
                distance_km = distance_lookup.get(
                    (
                        demand_id,
                        supply_id,
                    ),
                    math.inf,
                )

            if distance_km <= config.search_radius_km + EPSILON:
                candidates.append(
                    (
                        supply,
                        distance_km,
                    )
                )

        candidates.sort(
            key=lambda item: (
                -remaining_supply[item[0]["station_id"]],
                item[1],
                item[0]["station_id"],
            )
        )

        for supply, distance_km in candidates:
            if vehicle_remaining < 1:
                break

            shortage_left = remaining_shortage[demand_id]

            if shortage_left < 1.0:
                break

            supply_id = supply["station_id"]

            supply_left = remaining_supply[supply_id]

            movable = min(
                shortage_left,
                supply_left,
                float(vehicle_remaining),
            )

            move_qty = int(math.floor(movable + EPSILON))

            if move_qty < 1:
                continue

            move_matches.append(
                {
                    "from_station_id": (supply_id),
                    "to_station_id": (demand_id),
                    "distance_km": round(
                        distance_km,
                        3,
                    ),
                    "move_qty": move_qty,
                }
            )

            remaining_supply[supply_id] -= move_qty

            remaining_shortage[demand_id] -= move_qty

            vehicle_remaining -= move_qty

    inbound: dict[str, float] = {}
    outbound: dict[str, float] = {}

    for move in move_matches:
        from_id = move["from_station_id"]
        to_id = move["to_station_id"]
        qty = float(move["move_qty"])

        outbound[from_id] = (
            outbound.get(
                from_id,
                0.0,
            )
            + qty
        )

        inbound[to_id] = (
            inbound.get(
                to_id,
                0.0,
            )
            + qty
        )

    station_effects: list[dict[str, Any]] = []

    shortage_before_total = 0.0
    shortage_after_total = 0.0

    shortage_count_before = 0
    shortage_count_after = 0

    over_rack_count = 0

    for state in states:
        station_id = state["station_id"]

        before = state["future_bikes"]

        after = (
            before
            + inbound.get(
                station_id,
                0.0,
            )
            - outbound.get(
                station_id,
                0.0,
            )
        )

        shortage_before = state["shortage"]

        shortage_after = max(
            0.0,
            state["s_min"] - after,
        )

        shortage_before_total += shortage_before
        shortage_after_total += shortage_after

        if shortage_before > EPSILON:
            shortage_count_before += 1

        if shortage_after > EPSILON:
            shortage_count_after += 1

        over_rack = before > state["rack_count"] + EPSILON

        if over_rack:
            over_rack_count += 1

        in_qty = inbound.get(
            station_id,
            0.0,
        )
        out_qty = outbound.get(
            station_id,
            0.0,
        )

        if (
            shortage_before > EPSILON
            or shortage_after > EPSILON
            or in_qty > EPSILON
            or out_qty > EPSILON
        ):
            station_effects.append(
                {
                    "station_id": (station_id),
                    "station_name": (state["station_name"]),
                    "district": (state["district"]),
                    "rack_count": (state["rack_count"]),
                    "s_min": (state["s_min"]),
                    "e_min": (state["e_min"]),
                    "future_bikes_before": (before),
                    "future_empty_racks_before": (state["future_empty_racks"]),
                    "over_rack_before": (over_rack),
                    "inbound_qty": in_qty,
                    "outbound_qty": out_qty,
                    "future_bikes_after": (after),
                    "shortage_before": (shortage_before),
                    "shortage_after": (shortage_after),
                    "shortage_reduction": (shortage_before - shortage_after),
                    "demand_weight": (state["demand_weight"]),
                    "priority_score": (state["priority_score"]),
                }
            )

    shortage_reduction = shortage_before_total - shortage_after_total

    shortage_reduction_rate = (
        shortage_reduction / shortage_before_total
        if shortage_before_total > EPSILON
        else None
    )

    detail = {
        "base_time": (base_time.isoformat()),
        "model_version": ("oracle-snapshot-upper-bound"),
        "horizon_min": horizon_min,
        "evaluated_station_count": (len(states)),
        "skipped_station_count": (len(stations) - len(states)),
        "shortage_score_before": (shortage_before_total),
        "shortage_score_after": (shortage_after_total),
        "shortage_reduction": (shortage_reduction),
        "shortage_reduction_rate": (shortage_reduction_rate),
        "shortage_station_count_before": (shortage_count_before),
        "shortage_station_count_after": (shortage_count_after),
        "shortage_station_count_reduction": (
            shortage_count_before - shortage_count_after
        ),
        "saturation_station_count_before": (len(surplus_states)),
        "over_rack_station_count_before": (over_rack_count),
        "move_match_count": (len(move_matches)),
        "move_qty_total": float(sum(move["move_qty"] for move in move_matches)),
        "warning_count": len(warnings),
        "vehicle_capacity": (config.vehicle_cap),
        "vehicle_capacity_used": (config.vehicle_cap - vehicle_remaining),
        "area_same_dow_time_mean_rent": (area_mean),
    }

    return {
        "detail": detail,
        "station_effects": (station_effects),
        "move_matches": move_matches,
        "warnings": warnings,
    }
