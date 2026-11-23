from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

import numpy as np
import pandas as pd

KST = "Asia/Seoul"


def _runtime_b3_frame(*, station_id: str, base_time: str) -> pd.DataFrame:
    timestamp = pd.Timestamp(base_time)
    if timestamp.tzinfo is None:
        raise ValueError("runtime fallback base_time must be timezone-aware")
    timestamp = timestamp.tz_convert(KST)
    return pd.DataFrame(
        [
            {
                "station_id": station_id,
                "weekday_index": int(timestamp.weekday()),
                "hour": int(timestamp.hour),
                "minute": int(timestamp.minute),
            }
        ]
    )


def _warning(
    code: str, message: str, *, station_id: str | None, horizon_min: int | None
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "station_id": station_id,
        "horizon_min": horizon_min,
    }


def _valid_inventory(
    inventory: Mapping[str, Mapping[str, Any]], station_id: str
) -> tuple[float, float] | None:
    current = inventory.get(station_id)
    if current is None:
        return None
    try:
        capacity = float(current["capacity"])
        bikes_now = float(current["bikes_now"])
    except (KeyError, TypeError, ValueError):
        return None
    if (
        not np.isfinite(capacity)
        or not np.isfinite(bikes_now)
        or capacity <= 0
        or bikes_now < 0
        or bikes_now > capacity
    ):
        return None
    return capacity, bikes_now


def apply_runtime_feature_fallback(
    *,
    response: Mapping[str, Any],
    request: Mapping[str, Any],
    inventory: Mapping[str, Mapping[str, Any]],
    baselines: Any | None,
) -> dict[str, Any]:
    """Fill FEATURE_ROW_NOT_FOUND stations using runtime B3/B1 fallback."""
    result = deepcopy(dict(response))
    if baselines is None:
        return result

    warnings = list(result.get("warnings", []))
    missing_station_ids = {
        warning.get("station_id")
        for warning in warnings
        if isinstance(warning, Mapping)
        and warning.get("code") == "FEATURE_ROW_NOT_FOUND"
        and warning.get("station_id")
    }
    if not missing_station_ids:
        return result

    horizons = [int(value) for value in request["horizons"]]
    base_time = str(request["base_time"])

    for station in result.get("predictions", []):
        station_id = station.get("station_id")
        if station_id not in missing_station_ids:
            continue
        if station.get("horizon_results"):
            continue

        current = _valid_inventory(inventory, str(station_id))
        if current is None:
            continue
        capacity, bikes_now = current

        runtime_frame = _runtime_b3_frame(
            station_id=str(station_id),
            base_time=base_time,
        )

        try:
            b3_predictions = baselines.predict_all(runtime_frame, "b3_dow_time_mean")
        except Exception:
            b3_predictions = None

        horizon_results: list[dict[str, Any]] = []
        for horizon in horizons:
            fallback_method = "b3_dow_time_mean"
            try:
                if b3_predictions is None:
                    raise ValueError("B3 unavailable")
                delta_net = float(
                    np.asarray(b3_predictions[horizon], dtype=np.float64)[0]
                )
                if not np.isfinite(delta_net):
                    raise ValueError("B3 non-finite")
            except Exception:
                delta_net = 0.0
                fallback_method = "b1_persistence"

            bikes_expected = float(np.clip(bikes_now + delta_net, 0.0, capacity))
            docks_expected = float(capacity - bikes_expected)

            horizon_results.append(
                {
                    "horizon_min": horizon,
                    "prediction_source": "baseline_fallback",
                    "delta_net": delta_net,
                    "bikes_expected": bikes_expected,
                    "docks_expected": docks_expected,
                }
            )

            warnings.append(
                _warning(
                    "BASELINE_FALLBACK",
                    f"exact feature row unavailable; used {fallback_method} runtime fallback",
                    station_id=str(station_id),
                    horizon_min=horizon,
                )
            )

        station["horizon_results"] = horizon_results

    result["warnings"] = warnings
    return result
