from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any, Mapping
from uuid import UUID
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds

from src.modeling.feature_engineering import HORIZONS
from src.modeling.model_comparison import FittedCandidate

KST = ZoneInfo("Asia/Seoul")
SUPPORTED_HORIZONS = tuple(int(value) for value in HORIZONS)


def validate_prediction_request(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "request_id",
        "base_time",
        "station_ids",
        "horizons",
    }

    missing = required - set(payload)
    if missing:
        raise ValueError(
            f"prediction request missing fields: {sorted(missing)}"
        )

    request_id = str(payload["request_id"])

    try:
        parsed_uuid = UUID(request_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("request_id must be a UUID") from exc

    if parsed_uuid.version != 4:
        raise ValueError("request_id must be UUID v4")

    try:
        base_time = pd.Timestamp(payload["base_time"])
    except Exception as exc:
        raise ValueError("base_time must be a valid datetime") from exc

    if base_time.tzinfo is None:
        raise ValueError(
            "base_time must be timezone-aware KST"
        )

    if base_time.utcoffset() != timedelta(hours=9):
        raise ValueError(
            "base_time must include the KST UTC+09:00 offset"
        )

    if (
        base_time.minute % 15 != 0
        or base_time.second != 0
        or base_time.microsecond != 0
    ):
        raise ValueError(
            "base_time must align to a 15-minute model bin"
        )

    station_ids = payload["station_ids"]

    if not isinstance(station_ids, list) or not station_ids:
        raise ValueError(
            "station_ids must be a non-empty array"
        )

    if any(
        not isinstance(value, str) or not value.strip()
        for value in station_ids
    ):
        raise ValueError(
            "every station_id must be a non-empty string"
        )

    if len(station_ids) != len(set(station_ids)):
        raise ValueError(
            "station_ids must not contain duplicates"
        )

    horizons = payload["horizons"]

    if not isinstance(horizons, list) or not horizons:
        raise ValueError(
            "horizons must be a non-empty array"
        )

    try:
        horizons = [int(value) for value in horizons]
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "horizons must contain integers"
        ) from exc

    unsupported = sorted(
        set(horizons) - set(SUPPORTED_HORIZONS)
    )

    if unsupported:
        raise ValueError(
            f"unsupported horizons: {unsupported}"
        )

    if len(horizons) != len(set(horizons)):
        raise ValueError(
            "horizons must not contain duplicates"
        )

    return {
        "request_id": request_id,
        "base_time": base_time.isoformat(),
        "station_ids": list(station_ids),
        "horizons": horizons,
    }


def load_point_in_time_features(
    path: Path,
    *,
    feature_columns: list[str],
    station_ids: list[str],
    base_time: str,
) -> pd.DataFrame:
    dataset = ds.dataset(
        str(path),
        format="parquet",
    )

    required_columns = list(
        dict.fromkeys(
            [
                "station_id",
                "base_time",
                *feature_columns,
            ]
        )
    )

    missing = (
        set(required_columns)
        - set(dataset.schema.names)
    )

    if missing:
        raise ValueError(
            f"feature source missing columns: {sorted(missing)}"
        )

    requested_time = pd.Timestamp(base_time)

    base_field = dataset.schema.field(
        "base_time"
    )

    if not pa.types.is_timestamp(
        base_field.type
    ):
        raise ValueError(
            "feature source base_time must be timestamp"
        )

    if base_field.type.tz:
        match_time = (
            requested_time
            .tz_convert(base_field.type.tz)
            .to_pydatetime()
        )
    else:
        match_time = (
            requested_time
            .tz_convert(KST)
            .tz_localize(None)
            .to_pydatetime()
        )

    expression = (
        ds.field("base_time")
        == pa.scalar(
            match_time,
            type=base_field.type,
        )
    )

    station_field = dataset.schema.field(
        "station_id"
    )

    station_filter_values = None

    if (
        pa.types.is_string(station_field.type)
        or pa.types.is_large_string(
            station_field.type
        )
    ):
        station_filter_values = station_ids

    elif pa.types.is_integer(
        station_field.type
    ):
        try:
            station_filter_values = [
                int(value)
                for value in station_ids
            ]
        except ValueError:
            station_filter_values = None

    if station_filter_values is not None:
        expression = expression & (
            ds.field("station_id").isin(
                station_filter_values
            )
        )

    table = dataset.to_table(
        columns=required_columns,
        filter=expression,
    )

    frame = table.to_pandas()

    if frame.empty:
        return frame

    frame["station_id"] = (
        frame["station_id"]
        .astype(str)
    )

    frame = frame.loc[
        frame["station_id"].isin(
            station_ids
        )
    ].copy()

    return frame


def load_inventory(
    path: Path,
) -> dict[str, dict[str, Any]]:
    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    if isinstance(payload, dict):
        records = payload.get("stations")
    else:
        records = payload

    if not isinstance(records, list):
        raise ValueError(
            "inventory JSON must be an array or "
            '{"stations": [...]}'
        )

    result: dict[str, dict[str, Any]] = {}

    for record in records:
        if not isinstance(record, dict):
            raise ValueError(
                "inventory record must be an object"
            )

        required = {
            "station_id",
            "capacity",
            "bikes_now",
        }

        missing = required - set(record)
        if missing:
            raise ValueError(
                f"inventory record missing: {sorted(missing)}"
            )

        station_id = record["station_id"]

        if not isinstance(station_id, str):
            raise ValueError(
                "inventory station_id must be a string"
            )

        if station_id in result:
            raise ValueError(
                f"duplicate inventory station_id: {station_id}"
            )

        result[station_id] = {
            "capacity": record["capacity"],
            "bikes_now": record["bikes_now"],
        }

    return result


def _display_number(
    value: float,
) -> int | float:
    number = float(value)

    if number.is_integer():
        return int(number)

    return number


def build_prediction_response(
    *,
    candidate: FittedCandidate,
    request: Mapping[str, Any],
    feature_frame: pd.DataFrame,
    inventory: Mapping[
        str,
        Mapping[str, Any],
    ],
    model_version: str,
) -> dict[str, Any]:
    request = validate_prediction_request(
        request
    )

    frame = feature_frame.copy()

    if not frame.empty:
        if "station_id" not in frame:
            raise ValueError(
                "feature frame missing station_id"
            )

        frame["station_id"] = (
            frame["station_id"]
            .astype(str)
        )

    missing_features = (
        set(candidate.feature_columns)
        - set(frame.columns)
    )

    if missing_features and not frame.empty:
        raise ValueError(
            "feature frame missing model features: "
            f"{sorted(missing_features)}"
        )

    station_rows: dict[
        str,
        pd.DataFrame,
    ] = {}

    warnings: list[str] = []
    valid_station_ids: list[str] = []
    valid_rows: list[pd.DataFrame] = []
    valid_inventory: dict[
        str,
        tuple[float, float],
    ] = {}

    for station_id in request[
        "station_ids"
    ]:
        matching = frame.loc[
            frame["station_id"].eq(
                station_id
            )
        ]

        station_rows[station_id] = matching

        if matching.empty:
            warnings.append(
                f"{station_id}: feature row not found "
                "for base_time"
            )
            continue

        if len(matching) != 1:
            warnings.append(
                f"{station_id}: expected exactly one "
                "feature row for base_time"
            )
            continue

        current = inventory.get(station_id)

        if current is None:
            warnings.append(
                f"{station_id}: current inventory "
                "not available"
            )
            continue

        try:
            capacity = float(
                current["capacity"]
            )
            bikes_now = float(
                current["bikes_now"]
            )
        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            warnings.append(
                f"{station_id}: invalid current inventory"
            )
            continue

        if (
            not np.isfinite(capacity)
            or not np.isfinite(bikes_now)
            or capacity <= 0
            or bikes_now < 0
            or bikes_now > capacity
        ):
            warnings.append(
                f"{station_id}: current inventory "
                "outside valid range"
            )
            continue

        valid_station_ids.append(
            station_id
        )

        valid_rows.append(
            matching.iloc[[0]]
        )

        valid_inventory[station_id] = (
            capacity,
            bikes_now,
        )

    prediction_lookup: dict[
        str,
        dict[int, float],
    ] = {}

    if valid_rows:
        model_frame = pd.concat(
            valid_rows,
            ignore_index=True,
        )

        predicted = candidate.predict_all(
            model_frame
        )

        for position, station_id in enumerate(
            valid_station_ids
        ):
            prediction_lookup[
                station_id
            ] = {}

            for horizon in request[
                "horizons"
            ]:
                value = float(
                    predicted[horizon][position]
                )

                if not np.isfinite(value):
                    warnings.append(
                        f"{station_id}: non-finite "
                        f"{horizon}m prediction"
                    )
                    continue

                prediction_lookup[
                    station_id
                ][horizon] = value

    response_predictions = []

    for station_id in request[
        "station_ids"
    ]:
        entry: dict[str, Any] = {
            "station_id": station_id,
            "horizon_results": [],
        }

        current = inventory.get(station_id)

        if current is not None:
            try:
                entry["capacity"] = (
                    _display_number(
                        float(
                            current[
                                "capacity"
                            ]
                        )
                    )
                )
                entry["bikes_now"] = (
                    _display_number(
                        float(
                            current[
                                "bikes_now"
                            ]
                        )
                    )
                )
            except (
                KeyError,
                TypeError,
                ValueError,
            ):
                pass

        if station_id in prediction_lookup:
            capacity, bikes_now = (
                valid_inventory[
                    station_id
                ]
            )

            results = []

            for horizon in request[
                "horizons"
            ]:
                if (
                    horizon
                    not in prediction_lookup[
                        station_id
                    ]
                ):
                    continue

                delta_net = (
                    prediction_lookup[
                        station_id
                    ][horizon]
                )

                bikes_expected = float(
                    np.clip(
                        bikes_now
                        + delta_net,
                        0.0,
                        capacity,
                    )
                )

                docks_expected = (
                    capacity
                    - bikes_expected
                )

                results.append(
                    {
                        "horizon_min": horizon,
                        "delta_net": delta_net,
                        "bikes_expected":
                            bikes_expected,
                        "docks_expected":
                            docks_expected,
                    }
                )

            entry[
                "horizon_results"
            ] = results

        response_predictions.append(
            entry
        )

    return {
        "request_id": request[
            "request_id"
        ],
        "base_time": request[
            "base_time"
        ],
        "model_version": model_version,
        "source": "model",
        "predictions":
            response_predictions,
        "warnings": warnings,
    }
