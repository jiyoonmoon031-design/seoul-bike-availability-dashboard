from datetime import datetime, timedelta, timezone

import pytest

from src.modeling.runtime_inventory import assess_inventory

NOW = datetime(2026, 11, 25, 8, 0, tzinfo=timezone(timedelta(hours=9)))


@pytest.mark.parametrize(
    ("record", "status", "usable"),
    [
        ({"capacity": 10, "bikes_now": 4}, "valid", True),
        ({"capacity": 10, "bikes_now": 0}, "valid", True),
        ({"capacity": 10, "bikes_now": 10}, "valid", True),
        ({"capacity": 10, "bikes_now": 12}, "overflow", True),
        ({"capacity": 10, "bikes_now": -1}, "invalid_inventory", False),
        ({"capacity": None, "bikes_now": 1}, "invalid_capacity", False),
    ],
)
def test_inventory_states(record, status, usable):
    result = assess_inventory("ST-1", record)
    assert result.status == status
    assert result.usable is usable


def test_missing_station_is_distinct():
    result = assess_inventory("ST-MISSING", None)
    assert result.status == "missing_station"
    assert result.warning_code == "MISSING_INVENTORY"


def test_overflow_preserves_observation_and_nonnegative_docks():
    result = assess_inventory("ST-OVER", {"capacity": 10, "bikes_now": 13})
    assert result.observed_inventory == 13
    assert result.overflow == 3
    assert result.available_docks == 0
    projected = result.project(-1)
    assert projected == {
        "bikes_expected": 12,
        "docks_expected": 0,
        "overflow_expected": 2,
    }


def test_stale_snapshot_is_not_usable():
    result = assess_inventory(
        "ST-STALE",
        {
            "capacity": 10,
            "bikes_now": 4,
            "collected_at": (NOW - timedelta(minutes=16)).isoformat(),
        },
        reference_time=NOW,
        require_timestamp=True,
    )
    assert result.status == "stale"
    assert result.warning_code == "STALE_INVENTORY"


def test_invalid_timestamp_is_distinct():
    result = assess_inventory(
        "ST-BAD-TIME",
        {"capacity": 10, "bikes_now": 4, "collected_at": "not-a-time"},
        reference_time=NOW,
        require_timestamp=True,
    )
    assert result.status == "invalid_timestamp"
    assert result.warning_code == "INVALID_INVENTORY_TIMESTAMP"


def test_mixed_batch_can_be_classified_without_cross_station_failure():
    records = {
        "OK": {"capacity": 10, "bikes_now": 2},
        "OVER": {"capacity": 10, "bikes_now": 11},
        "NEG": {"capacity": 10, "bikes_now": -1},
    }
    results = {key: assess_inventory(key, value) for key, value in records.items()}
    assert {key for key, value in results.items() if value.usable} == {"OK", "OVER"}
