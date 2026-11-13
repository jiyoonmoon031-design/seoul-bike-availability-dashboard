from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Mapping, Sequence

from src.rebalancing.logic import (
    RebalancingConfig,
    build_rebalancing_plan,
)

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
    capacity: float,
    *,
    ratio: float,
    minimum: int,
) -> int:
    return max(
        int(minimum),
        int(math.ceil(ratio * capacity)),
    )


def _context_map(
    station_contexts: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}

    for context in station_contexts:
        station_id = context.get("station_id")

        if isinstance(station_id, str) and station_id:
            result[station_id] = context

    return result


def _horizon_result(
    prediction: Mapping[str, Any],
    horizon_min: int,
) -> Mapping[str, Any] | None:
    values = prediction.get("horizon_results")

    if not isinstance(values, list):
        return None

    for value in values:
        if not isinstance(value, Mapping):
            continue

        raw_horizon = value.get("horizon_min")

        try:
            candidate = int(raw_horizon)
        except (TypeError, ValueError):
            continue

        if candidate == horizon_min:
            return value

    return None


def _eligible_station_rows(
    prediction_response: Mapping[str, Any],
    station_contexts: Sequence[Mapping[str, Any]],
    *,
    config: RebalancingConfig,
    horizon_min: int,
) -> tuple[list[dict[str, Any]], int]:
    predictions = prediction_response.get("predictions")

    if not isinstance(predictions, list):
        raise ValueError("prediction response must contain a predictions array")

    contexts = _context_map(station_contexts)
    rows: list[dict[str, Any]] = []
    skipped = 0

    for prediction in predictions:
        if not isinstance(prediction, Mapping):
            skipped += 1
            continue

        station_id = prediction.get("station_id")

        if not isinstance(station_id, str) or not station_id:
            skipped += 1
            continue

        context = contexts.get(station_id)

        if context is None:
            skipped += 1
            continue

        latitude = _finite_float(context.get("latitude"))
        longitude = _finite_float(context.get("longitude"))

        if latitude is None or longitude is None:
            skipped += 1
            continue

        capacity = _finite_float(prediction.get("capacity"))

        if capacity is None or capacity <= 0:
            skipped += 1
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
            skipped += 1
            continue

        selected = _horizon_result(
            prediction,
            horizon_min,
        )

        if selected is None:
            skipped += 1
            continue

        bikes_expected = _finite_float(selected.get("bikes_expected"))
        docks_expected = _finite_float(selected.get("docks_expected"))

        if bikes_expected is None or docks_expected is None:
            skipped += 1
            continue

        shortage = max(
            0.0,
            s_min - bikes_expected,
        )

        overflow = max(
            0.0,
            e_min - docks_expected,
        )

        if shortage > EPSILON and overflow > EPSILON:
            skipped += 1
            continue

        rows.append(
            {
                "station_id": station_id,
                "capacity": capacity,
                "s_min": s_min,
                "e_min": e_min,
                "bikes_expected": bikes_expected,
                "docks_expected": docks_expected,
                "shortage_before": shortage,
            }
        )

    return rows, skipped


def evaluate_rebalancing_case(
    prediction_response: Mapping[str, Any],
    station_contexts: Sequence[Mapping[str, Any]],
    *,
    config: RebalancingConfig,
    horizon_min: int,
) -> dict[str, Any]:
    if horizon_min not in config.horizons:
        raise ValueError(f"unsupported horizon: {horizon_min}")

    predictions = prediction_response.get("predictions")

    if not isinstance(predictions, list):
        raise ValueError("prediction response must contain a predictions array")

    plan = build_rebalancing_plan(
        prediction_response,
        station_contexts,
        config=config,
        horizon_min=horizon_min,
        top_n=max(1, len(predictions)),
    )

    rows, skipped_station_count = _eligible_station_rows(
        prediction_response,
        station_contexts,
        config=config,
        horizon_min=horizon_min,
    )

    inbound: dict[str, float] = defaultdict(float)
    outbound: dict[str, float] = defaultdict(float)

    move_matches = plan.response.get(
        "move_matches",
        [],
    )

    if not isinstance(move_matches, list):
        raise ValueError("rebalancing response move_matches must be an array")

    move_qty_total = 0.0

    for match in move_matches:
        if not isinstance(match, Mapping):
            continue

        from_station_id = match.get("from_station_id")
        to_station_id = match.get("to_station_id")
        move_qty = _finite_float(match.get("move_qty"))

        if (
            not isinstance(from_station_id, str)
            or not isinstance(to_station_id, str)
            or move_qty is None
            or move_qty <= 0
        ):
            continue

        outbound[from_station_id] += move_qty
        inbound[to_station_id] += move_qty
        move_qty_total += move_qty

    shortage_score_before = 0.0
    shortage_score_after = 0.0
    shortage_station_count_before = 0
    shortage_station_count_after = 0
    station_effects: list[dict[str, Any]] = []

    base_time = prediction_response.get("base_time")

    for row in rows:
        station_id = row["station_id"]
        shortage_before = float(row["shortage_before"])

        adjusted_bikes = (
            float(row["bikes_expected"])
            + inbound.get(station_id, 0.0)
            - outbound.get(station_id, 0.0)
        )

        shortage_after = max(
            0.0,
            float(row["s_min"]) - adjusted_bikes,
        )

        shortage_score_before += shortage_before
        shortage_score_after += shortage_after

        if shortage_before > EPSILON:
            shortage_station_count_before += 1

        if shortage_after > EPSILON:
            shortage_station_count_after += 1

        station_effects.append(
            {
                "base_time": base_time,
                "horizon_min": horizon_min,
                "station_id": station_id,
                "capacity": row["capacity"],
                "s_min": row["s_min"],
                "bikes_expected_before": row["bikes_expected"],
                "inbound_qty": inbound.get(
                    station_id,
                    0.0,
                ),
                "outbound_qty": outbound.get(
                    station_id,
                    0.0,
                ),
                "bikes_expected_after": adjusted_bikes,
                "shortage_before": shortage_before,
                "shortage_after": shortage_after,
                "shortage_reduction": (shortage_before - shortage_after),
            }
        )

    shortage_reduction = shortage_score_before - shortage_score_after

    shortage_reduction_rate = None

    if shortage_score_before > EPSILON:
        shortage_reduction_rate = shortage_reduction / shortage_score_before

    return {
        "base_time": base_time,
        "model_version": prediction_response.get("model_version"),
        "horizon_min": horizon_min,
        "evaluated_station_count": len(rows),
        "skipped_station_count": skipped_station_count,
        "shortage_score_before": shortage_score_before,
        "shortage_score_after": shortage_score_after,
        "shortage_reduction": shortage_reduction,
        "shortage_reduction_rate": (shortage_reduction_rate),
        "shortage_station_count_before": (shortage_station_count_before),
        "shortage_station_count_after": (shortage_station_count_after),
        "shortage_station_count_reduction": (
            shortage_station_count_before - shortage_station_count_after
        ),
        "move_match_count": len(
            plan.response.get(
                "move_matches",
                [],
            )
        ),
        "move_qty_total": move_qty_total,
        "warning_count": len(plan.warnings),
        "vehicle_capacity": (plan.diagnostics.get("vehicle_capacity")),
        "vehicle_capacity_used": (plan.diagnostics.get("vehicle_capacity_used")),
        "station_effects": station_effects,
    }


def summarize_backtests(
    records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[int, list[Mapping[str, Any]]] = defaultdict(list)

    for record in records:
        grouped[int(record["horizon_min"])].append(record)

    summaries: list[dict[str, Any]] = []

    for horizon_min in sorted(grouped):
        group = grouped[horizon_min]

        before_total = sum(float(item["shortage_score_before"]) for item in group)
        after_total = sum(float(item["shortage_score_after"]) for item in group)
        reduction_total = before_total - after_total

        aggregate_rate = None

        if before_total > EPSILON:
            aggregate_rate = reduction_total / before_total

        case_rates = [
            float(item["shortage_reduction_rate"])
            for item in group
            if item.get("shortage_reduction_rate") is not None
        ]

        summaries.append(
            {
                "horizon_min": horizon_min,
                "case_count": len(group),
                "shortage_score_before_total": (before_total),
                "shortage_score_after_total": (after_total),
                "shortage_reduction_total": (reduction_total),
                "shortage_reduction_rate": (aggregate_rate),
                "mean_case_reduction_rate": (
                    sum(case_rates) / len(case_rates) if case_rates else None
                ),
                "shortage_station_count_before_total": sum(
                    int(item["shortage_station_count_before"]) for item in group
                ),
                "shortage_station_count_after_total": sum(
                    int(item["shortage_station_count_after"]) for item in group
                ),
                "shortage_station_count_reduction_total": sum(
                    int(item["shortage_station_count_reduction"]) for item in group
                ),
                "move_match_count_total": sum(
                    int(item["move_match_count"]) for item in group
                ),
                "move_qty_total": sum(float(item["move_qty_total"]) for item in group),
            }
        )

    return summaries
