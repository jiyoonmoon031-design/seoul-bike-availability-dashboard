from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Mapping


DEFAULT_MAX_AGE = timedelta(minutes=15)
DEFAULT_FUTURE_TOLERANCE = timedelta(minutes=2)


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        result = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if result.tzinfo is None or result.utcoffset() is None:
        return None
    return result


@dataclass(frozen=True)
class RuntimeInventory:
    station_id: str
    registered_capacity: float | None
    observed_inventory: float | None
    collected_at: datetime | None
    source: str | None
    status: str
    usable: bool
    warning_code: str | None = None
    warning_message: str | None = None

    @property
    def overflow(self) -> float:
        if self.registered_capacity is None or self.observed_inventory is None:
            return 0.0
        return max(0.0, self.observed_inventory - self.registered_capacity)

    @property
    def available_docks(self) -> float:
        if self.registered_capacity is None or self.observed_inventory is None:
            return 0.0
        return max(0.0, self.registered_capacity - self.observed_inventory)

    def project(self, delta_net: float) -> dict[str, float]:
        if not self.usable or self.observed_inventory is None:
            raise ValueError("inventory is not usable")
        if self.registered_capacity is None:
            raise ValueError("registered capacity is unavailable")
        runtime_ceiling = max(self.registered_capacity, self.observed_inventory)
        expected = min(
            max(0.0, self.observed_inventory + float(delta_net)),
            runtime_ceiling,
        )
        return {
            "bikes_expected": expected,
            "docks_expected": max(0.0, self.registered_capacity - expected),
            "overflow_expected": max(0.0, expected - self.registered_capacity),
        }

    def provenance(self) -> dict[str, Any]:
        return {
            "registered_capacity": self.registered_capacity,
            "observed_inventory": self.observed_inventory,
            "overflow_bikes": self.overflow,
            "available_docks_now": self.available_docks,
            "inventory_collected_at": (
                self.collected_at.isoformat() if self.collected_at else None
            ),
            "inventory_source": self.source,
            "inventory_status": self.status,
        }


def assess_inventory(
    station_id: str,
    record: Mapping[str, Any] | None,
    *,
    reference_time: datetime | None = None,
    max_age: timedelta = DEFAULT_MAX_AGE,
    future_tolerance: timedelta = DEFAULT_FUTURE_TOLERANCE,
    require_timestamp: bool = False,
) -> RuntimeInventory:
    """Validate runtime inventory without applying the historical clip policy.

    A positive overflow is a usable observation. It means the observed inventory
    exceeds the registered rack count; it does not prove that the observation is
    corrupt. Missing, negative, non-finite, stale, or invalid-time observations
    remain unusable.
    """
    if record is None:
        return RuntimeInventory(
            station_id, None, None, None, None, "missing_station", False,
            "MISSING_INVENTORY", "Realtime station inventory is unavailable",
        )

    capacity = _number(record.get("registered_capacity", record.get("capacity")))
    bikes = _number(record.get("observed_inventory", record.get("bikes_now")))
    source_raw = record.get("inventory_source", record.get("source"))
    source = str(source_raw) if source_raw is not None else None

    if capacity is None or capacity <= 0:
        return RuntimeInventory(
            station_id, capacity, bikes, None, source, "invalid_capacity", False,
            "INVALID_CAPACITY", "Registered station capacity is missing or invalid",
        )
    if bikes is None or bikes < 0:
        return RuntimeInventory(
            station_id, capacity, bikes, None, source, "invalid_inventory", False,
            "INVALID_INVENTORY", "Observed bike inventory is missing or invalid",
        )

    raw_collected_at = record.get("inventory_collected_at", record.get("collected_at"))
    collected_at = _timestamp(raw_collected_at)
    if raw_collected_at is not None and collected_at is None:
        return RuntimeInventory(
            station_id, capacity, bikes, None, source, "invalid_timestamp", False,
            "INVALID_INVENTORY_TIMESTAMP", "Inventory timestamp is invalid",
        )
    if require_timestamp and collected_at is None:
        return RuntimeInventory(
            station_id, capacity, bikes, None, source, "missing_timestamp", False,
            "MISSING_INVENTORY_TIMESTAMP", "Inventory timestamp is unavailable",
        )

    if reference_time is not None and collected_at is not None:
        if reference_time.tzinfo is None or reference_time.utcoffset() is None:
            raise ValueError("reference_time must be timezone-aware")
        age = reference_time - collected_at.astimezone(reference_time.tzinfo)
        if age > max_age:
            return RuntimeInventory(
                station_id, capacity, bikes, collected_at, source, "stale", False,
                "STALE_INVENTORY", "Inventory snapshot is older than the runtime limit",
            )
        if age < -future_tolerance:
            return RuntimeInventory(
                station_id, capacity, bikes, collected_at, source, "future_timestamp", False,
                "INVALID_INVENTORY_TIMESTAMP", "Inventory timestamp is in the future",
            )

    status = "overflow" if bikes > capacity else "valid"
    code = "INVENTORY_OVER_CAPACITY" if status == "overflow" else None
    message = (
        "Observed bikes exceed registered capacity; raw inventory is preserved"
        if status == "overflow"
        else None
    )
    return RuntimeInventory(
        station_id, capacity, bikes, collected_at, source, status, True, code, message
    )
