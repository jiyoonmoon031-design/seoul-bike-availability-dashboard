from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Literal

Leg = Literal["origin", "destination"]


@dataclass(frozen=True)
class RecommendationConfig:
    max_walk_m: float
    avail_stable_target: float
    distance_weight: float
    availability_weight: float
    horizons: tuple[int, ...]

    @classmethod
    def from_params(cls, params: dict[str, Any]) -> "RecommendationConfig":
        weights = params["RECOMMENDATION_WEIGHT"]

        return cls(
            max_walk_m=float(params["MAX_WALK_M"]),
            avail_stable_target=float(params["AVAIL_STABLE_TARGET"]),
            distance_weight=float(weights["distance"]),
            availability_weight=float(weights["availability"]),
            horizons=tuple(int(value) for value in params["HORIZONS"]),
        )


@dataclass(frozen=True)
class RecommendationResult:
    response: dict[str, Any]
    warnings: list[str]


def _finite_number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    if not isfinite(result):
        return None

    return result


def interpolate_delta(
    eta_min: float,
    horizon_results: list[dict[str, Any]],
) -> tuple[float, dict[str, Any]]:
    """Interpolate predicted net inventory delta at ETA.

    Anchors are fixed at:
      (0, 0), (15, delta_15), (30, delta_30), (60, delta_60)

    ETA above the final horizon is clamped to the final delta.
    """

    eta = _finite_number(eta_min)

    if eta is None or eta < 0:
        raise ValueError("eta_min must be a finite non-negative number")

    delta_by_horizon: dict[int, float] = {}

    for item in horizon_results:
        horizon = item.get("horizon_min")
        delta = _finite_number(item.get("delta_net"))

        if horizon is None or delta is None:
            continue

        delta_by_horizon[int(horizon)] = delta

    required = (15, 30, 60)

    missing = [horizon for horizon in required if horizon not in delta_by_horizon]

    if missing:
        raise ValueError(
            "missing prediction horizon(s): "
            + ", ".join(str(value) for value in missing)
        )

    anchors = [
        (0.0, 0.0),
        (15.0, delta_by_horizon[15]),
        (30.0, delta_by_horizon[30]),
        (60.0, delta_by_horizon[60]),
    ]

    if eta >= 60:
        return (
            delta_by_horizon[60],
            {
                "method": "clamp",
                "anchors": [60, 60],
                "value_at": eta,
            },
        )

    for (left_h, left_delta), (right_h, right_delta) in zip(
        anchors,
        anchors[1:],
    ):
        if left_h <= eta <= right_h:
            ratio = (eta - left_h) / (right_h - left_h)

            interpolated = left_delta + ratio * (right_delta - left_delta)

            return (
                interpolated,
                {
                    "method": "interpolation",
                    "anchors": [int(left_h), int(right_h)],
                    "value_at": eta,
                },
            )

    raise RuntimeError("unable to map eta to prediction horizon")


def _distance_score(
    distance_m: float,
    max_walk_m: float,
) -> float:
    return 1.0 - min(max(distance_m, 0.0) / max_walk_m, 1.0)


def _availability_score(
    available: float,
    target: float,
) -> float:
    return min(max(available, 0.0) / target, 1.0)


def recommend_stations(
    candidates: list[dict[str, Any]],
    *,
    leg: Leg,
    eta_min: float,
    config: RecommendationConfig,
    top_n: int = 3,
) -> RecommendationResult:
    if leg not in ("origin", "destination"):
        raise ValueError("leg must be origin or destination")

    if top_n < 1:
        raise ValueError("top_n must be >= 1")

    if config.max_walk_m <= 0:
        raise ValueError("max_walk_m must be > 0")

    if config.avail_stable_target <= 0:
        raise ValueError("avail_stable_target must be > 0")

    total_weight = config.distance_weight + config.availability_weight

    if total_weight <= 0:
        raise ValueError("recommendation weights must sum to > 0")

    recommendations: list[dict[str, Any]] = []
    warnings: list[str] = []
    effective_horizon: dict[str, Any] | None = None

    for candidate in candidates:
        station_id = candidate.get("station_id")

        if not isinstance(station_id, str) or not station_id:
            warnings.append("candidate with invalid station_id skipped")
            continue

        station_name = candidate.get("station_name")

        distance_m = _finite_number(candidate.get("distance_m"))
        capacity = _finite_number(candidate.get("capacity"))
        bikes_now = _finite_number(candidate.get("bikes_now"))
        walk_min = _finite_number(candidate.get("walk_min"))

        if (
            distance_m is None
            or capacity is None
            or bikes_now is None
            or walk_min is None
            or capacity <= 0
            or bikes_now < 0
        ):
            warnings.append(f"{station_id}: invalid distance/inventory context skipped")
            continue

        horizon_results = candidate.get("horizon_results")

        if not isinstance(horizon_results, list):
            warnings.append(f"{station_id}: horizon_results missing")
            continue

        try:
            delta_eta, horizon_info = interpolate_delta(
                eta_min,
                horizon_results,
            )
        except ValueError as exc:
            warnings.append(f"{station_id}: {exc}")
            continue

        effective_horizon = horizon_info

        prediction_sources = {
            str(item.get("prediction_source"))
            for item in horizon_results
            if item.get("prediction_source")
        }
        prediction_source = (
            next(iter(prediction_sources))
            if len(prediction_sources) == 1
            else "mixed" if prediction_sources else "unknown"
        )

        runtime_ceiling = max(capacity, bikes_now)
        bikes_expected = min(max(bikes_now + delta_eta, 0.0), runtime_ceiling)
        docks_expected = max(capacity - bikes_expected, 0.0)
        overflow_now = max(bikes_now - capacity, 0.0)
        overflow_expected = max(bikes_expected - capacity, 0.0)

        available = bikes_expected if leg == "origin" else docks_expected

        distance_component = config.distance_weight * _distance_score(
            distance_m,
            config.max_walk_m,
        )

        availability_component = config.availability_weight * _availability_score(
            available,
            config.avail_stable_target,
        )

        score = distance_component + availability_component

        recommendations.append(
            {
                "station_id": station_id,
                "station_name": station_name,
                "distance_m": round(distance_m, 3),
                "walk_min": round(walk_min, 3),
                "bikes_now": round(bikes_now, 3),
                "docks_now": round(max(capacity - bikes_now, 0.0), 3),
                "overflow_now": round(overflow_now, 3),
                "bikes_expected": round(bikes_expected, 3),
                "docks_expected": round(docks_expected, 3),
                "overflow_expected": round(overflow_expected, 3),
                "prediction_source": prediction_source,
                "score": round(score, 6),
                "score_breakdown": {
                    "distance": round(distance_component, 6),
                    "availability": round(
                        availability_component,
                        6,
                    ),
                },
            }
        )

    availability_field = "bikes_expected" if leg == "origin" else "docks_expected"

    recommendations.sort(
        key=lambda item: (
            -item["score"],
            -item[availability_field],
            item["distance_m"],
            item["station_id"],
        )
    )

    top = recommendations[:top_n]

    for rank, item in enumerate(top, start=1):
        item["rank"] = rank

    response = {
        "leg": leg,
        "eta_min": eta_min,
        "effective_horizon": (
            effective_horizon
            if effective_horizon is not None
            else {
                "method": "unavailable",
                "anchors": [],
                "value_at": eta_min,
            }
        ),
        "recommendations": top,
    }

    return RecommendationResult(
        response=response,
        warnings=warnings,
    )
