from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Mapping, Sequence

EPSILON = 1e-9


@dataclass(frozen=True)
class RebalancingConfig:
    horizons: tuple[int, ...]
    s_min_ratio: float
    s_minimum: int
    e_min_ratio: float
    e_minimum: int
    urgency: dict[int, float]
    demand_weight_min: float
    demand_weight_max: float
    search_radius_km: float
    vehicle_cap: int
    detour_factor: float

    @classmethod
    def from_params(
        cls,
        params: Mapping[str, Any],
    ) -> "RebalancingConfig":
        return cls(
            horizons=tuple(int(value) for value in params["HORIZONS"]),
            s_min_ratio=float(params["S_MIN"]["capacity_ratio"]),
            s_minimum=int(params["S_MIN"]["minimum"]),
            e_min_ratio=float(params["E_MIN"]["capacity_ratio"]),
            e_minimum=int(params["E_MIN"]["minimum"]),
            urgency={
                int(key): float(value) for key, value in params["URGENCY"].items()
            },
            demand_weight_min=float(params["DEMAND_WEIGHT"]["minimum"]),
            demand_weight_max=float(params["DEMAND_WEIGHT"]["maximum"]),
            search_radius_km=float(params["SEARCH_RADIUS_KM"]),
            vehicle_cap=int(params["VEHICLE_CAP"]),
            detour_factor=float(params["DETOUR_FACTOR"]),
        )


@dataclass
class RebalancingResult:
    response: dict[str, Any]
    warnings: list[str]
    diagnostics: dict[str, Any]


def _finite_float(
    value: Any,
) -> float | None:
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
    capacity: float,
    *,
    ratio: float,
    minimum: int,
) -> int:
    return max(
        int(minimum),
        int(math.ceil(ratio * capacity)),
    )


def haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    radius_km = 6371.0088

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )

    return 2 * radius_km * math.asin(min(1.0, math.sqrt(a)))


def _parse_base_time(
    value: Any,
) -> datetime:
    if not isinstance(value, str):
        raise ValueError("prediction base_time must be a string")

    normalized = value

    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("prediction base_time is invalid") from exc

    if parsed.tzinfo is None:
        raise ValueError("prediction base_time must be timezone-aware")

    return parsed


def _context_map(
    station_contexts: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    result: dict[
        str,
        Mapping[str, Any],
    ] = {}

    for record in station_contexts:
        station_id = record.get("station_id")

        if not isinstance(station_id, str) or not station_id.strip():
            raise ValueError("station context station_id " "must be a non-empty string")

        if station_id in result:
            raise ValueError(f"duplicate station context: " f"{station_id}")

        result[station_id] = record

    return result


def _horizon_result_map(
    prediction: Mapping[str, Any],
) -> dict[int, Mapping[str, Any]]:
    rows = prediction.get(
        "horizon_results",
        [],
    )

    if not isinstance(rows, list):
        return {}

    result: dict[
        int,
        Mapping[str, Any],
    ] = {}

    for row in rows:
        if not isinstance(row, Mapping):
            continue

        try:
            horizon = int(row["horizon_min"])
        except (KeyError, TypeError, ValueError):
            continue

        result[horizon] = row

    return result


def _demand_weights(
    prepared: Sequence[dict[str, Any]],
    config: RebalancingConfig,
) -> tuple[
    dict[str, float],
    float | None,
    list[str],
]:
    warnings: list[str] = []
    observed: dict[str, float] = {}

    for station in prepared:
        value = _finite_float(station["context"].get("same_dow_time_mean_rent"))

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

    return (
        weights,
        area_mean,
        warnings,
    )


def build_rebalancing_plan(
    prediction_response: Mapping[str, Any],
    station_contexts: Sequence[Mapping[str, Any]],
    *,
    config: RebalancingConfig,
    horizon_min: int,
    top_n: int = 10,
) -> RebalancingResult:
    if horizon_min not in config.horizons:
        raise ValueError(f"unsupported horizon: {horizon_min}")

    if top_n < 1:
        raise ValueError("top_n must be >= 1")

    base_time = _parse_base_time(prediction_response.get("base_time"))

    predictions = prediction_response.get("predictions")

    if not isinstance(predictions, list):
        raise ValueError("prediction response must contain " "a predictions array")

    contexts = _context_map(station_contexts)

    warnings: list[str] = []
    prepared: list[dict[str, Any]] = []

    for prediction in predictions:
        if not isinstance(
            prediction,
            Mapping,
        ):
            continue

        station_id = prediction.get("station_id")

        if not isinstance(station_id, str) or not station_id:
            warnings.append("prediction with invalid " "station_id skipped")
            continue

        context = contexts.get(station_id)

        if context is None:
            warnings.append(f"{station_id}: station context " "missing")
            continue

        capacity = _finite_float(prediction.get("capacity"))

        if capacity is None or capacity <= 0:
            warnings.append(f"{station_id}: capacity is " "null, invalid, or zero")
            continue

        latitude = _finite_float(context.get("latitude"))
        longitude = _finite_float(context.get("longitude"))

        if latitude is None or longitude is None:
            warnings.append(f"{station_id}: coordinates missing")
            continue

        s_min = _minimum_level(
            capacity,
            ratio=config.s_min_ratio,
            minimum=config.s_minimum,
        )

        e_min = _minimum_level(
            capacity,
            ratio=config.e_min_ratio,
            minimum=config.e_minimum,
        )

        if s_min + e_min > capacity:
            warnings.append(
                f"{station_id}: S_min + E_min " "exceeds capacity; station skipped"
            )
            continue

        result_by_horizon = _horizon_result_map(prediction)

        selected = result_by_horizon.get(horizon_min)

        if selected is None:
            warnings.append(f"{station_id}: {horizon_min}m " "prediction missing")
            continue

        bikes_expected = _finite_float(selected.get("bikes_expected"))

        if (
            bikes_expected is None
            or bikes_expected < 0
            or bikes_expected > capacity + EPSILON
        ):
            warnings.append(f"{station_id}: invalid " "bikes_expected")
            continue

        docks_expected = capacity - bikes_expected

        reported_docks = _finite_float(selected.get("docks_expected"))

        if reported_docks is not None and abs(reported_docks - docks_expected) > 1e-6:
            warnings.append(
                f"{station_id}: docks_expected "
                "was inconsistent with capacity; "
                "recomputed"
            )

        prepared.append(
            {
                "station_id": station_id,
                "station_name": str(
                    context.get(
                        "station_name",
                        station_id,
                    )
                ),
                "latitude": latitude,
                "longitude": longitude,
                "capacity": capacity,
                "s_min": s_min,
                "e_min": e_min,
                "bikes_expected": bikes_expected,
                "docks_expected": docks_expected,
                "result_by_horizon": result_by_horizon,
                "context": context,
            }
        )

    (
        demand_weights,
        area_demand_mean,
        demand_warnings,
    ) = _demand_weights(
        prepared,
        config,
    )

    warnings.extend(demand_warnings)

    states: list[dict[str, Any]] = []

    for station in prepared:
        risk_horizon: int | None = None

        for horizon in sorted(config.horizons):
            row = station["result_by_horizon"].get(horizon)

            if row is None:
                continue

            expected = _finite_float(row.get("bikes_expected"))

            if expected is not None and expected < station["s_min"]:
                risk_horizon = horizon
                break

        shortage = max(
            0.0,
            station["s_min"] - station["bikes_expected"],
        )

        overflow = max(
            0.0,
            station["e_min"] - station["docks_expected"],
        )

        if shortage > EPSILON and overflow > EPSILON:
            warnings.append(
                f"{station['station_id']}: "
                "shortage and saturation "
                "simultaneously detected; skipped"
            )
            continue

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
                station["bikes_expected"] - station["s_min"],
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
                "shortage": shortage,
                "overflow": overflow,
                "urgency": urgency,
                "demand_weight": demand_weight,
                "priority_score": priority_score,
                "supply_slack": supply_slack,
                "risk_horizon": risk_horizon,
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
        (state for state in states if state["overflow"] > EPSILON),
        key=lambda item: (
            -item["supply_slack"],
            item["station_id"],
        ),
    )

    remaining_supply = {
        item["station_id"]: item["supply_slack"] for item in surplus_states
    }

    remaining_shortage = {
        item["station_id"]: item["shortage"] for item in shortage_states
    }

    vehicle_remaining = int(config.vehicle_cap)

    move_matches: list[dict[str, Any]] = []

    for demand in shortage_states:
        if vehicle_remaining < 1:
            break

        demand_id = demand["station_id"]

        candidates: list[
            tuple[
                dict[str, Any],
                float,
            ]
        ] = []

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

            direct_distance = haversine_km(
                demand["latitude"],
                demand["longitude"],
                supply["latitude"],
                supply["longitude"],
            )

            estimated_distance = direct_distance * config.detour_factor

            if estimated_distance <= config.search_radius_km + EPSILON:
                candidates.append(
                    (
                        supply,
                        estimated_distance,
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
                    "from_station_id": supply_id,
                    "to_station_id": demand_id,
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

    shortage_top = [
        {
            "station_id": item["station_id"],
            "station_name": item["station_name"],
            "lat": item["latitude"],
            "lon": item["longitude"],
            "bikes_expected": item["bikes_expected"],
            "s_min": item["s_min"],
            "shortage": item["shortage"],
            "urgency": item["urgency"],
            "demand_weight": item["demand_weight"],
            "priority_score": item["priority_score"],
            "risk_time": item["risk_time"],
        }
        for item in shortage_states[:top_n]
    ]

    surplus_top = [
        {
            "station_id": item["station_id"],
            "docks_expected": item["docks_expected"],
            "supply_slack": item["supply_slack"],
        }
        for item in surplus_states[:top_n]
    ]

    unmatched = sum(1 for value in remaining_shortage.values() if value >= 1.0)

    response = {
        "base_time": prediction_response["base_time"],
        "horizon_min": horizon_min,
        "shortage_top": shortage_top,
        "surplus_top": surplus_top,
        "move_matches": move_matches,
    }

    diagnostics = {
        "model_version": prediction_response.get("model_version"),
        "shortage_station_count": len(shortage_states),
        "saturation_station_count": len(surplus_states),
        "move_match_count": len(move_matches),
        "unmatched_shortage_count": unmatched,
        "vehicle_capacity": config.vehicle_cap,
        "vehicle_capacity_used": config.vehicle_cap - vehicle_remaining,
        "vehicle_capacity_remaining": vehicle_remaining,
        "search_radius_km": config.search_radius_km,
        "detour_factor": config.detour_factor,
        "area_same_dow_time_mean_rent": area_demand_mean,
        "warning_count": len(warnings),
    }

    return RebalancingResult(
        response=response,
        warnings=warnings,
        diagnostics=diagnostics,
    )
