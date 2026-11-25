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
from src.modeling.model_comparison import FittedBaselines, FittedCandidate
from src.modeling.runtime_inventory import RuntimeInventory, assess_inventory

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
        raise ValueError(f"prediction request missing fields: {sorted(missing)}")

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
        raise ValueError("base_time must be timezone-aware KST")

    if base_time.utcoffset() != timedelta(hours=9):
        raise ValueError("base_time must include the KST UTC+09:00 offset")

    if (
        base_time.minute % 15 != 0
        or base_time.second != 0
        or base_time.microsecond != 0
    ):
        raise ValueError("base_time must align to a 15-minute model bin")

    station_ids = payload["station_ids"]

    if not isinstance(station_ids, list) or not station_ids:
        raise ValueError("station_ids must be a non-empty array")

    if any(not isinstance(value, str) or not value.strip() for value in station_ids):
        raise ValueError("every station_id must be a non-empty string")

    if len(station_ids) != len(set(station_ids)):
        raise ValueError("station_ids must not contain duplicates")

    horizons = payload["horizons"]

    if not isinstance(horizons, list) or not horizons:
        raise ValueError("horizons must be a non-empty array")

    try:
        horizons = [int(value) for value in horizons]
    except (TypeError, ValueError) as exc:
        raise ValueError("horizons must contain integers") from exc

    unsupported = sorted(set(horizons) - set(SUPPORTED_HORIZONS))

    if unsupported:
        raise ValueError(f"unsupported horizons: {unsupported}")

    if len(horizons) != len(set(horizons)):
        raise ValueError("horizons must not contain duplicates")

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

    schema_names = set(dataset.schema.names)

    identity_missing = {
        "station_id",
        "base_time",
    } - schema_names

    if identity_missing:
        raise ValueError(
            "feature source missing required identity columns: "
            f"{sorted(identity_missing)}"
        )

    # Model-feature schema drift must not terminate the whole
    # request. Load the columns that are still available and let
    # build_prediction_response emit FEATURE_UNAVAILABLE for the
    # affected station prediction.
    available_columns = [
        column for column in required_columns if column in schema_names
    ]

    requested_time = pd.Timestamp(base_time)

    base_field = dataset.schema.field("base_time")

    if not pa.types.is_timestamp(base_field.type):
        raise ValueError("feature source base_time must be timestamp")

    if base_field.type.tz:
        match_time = requested_time.tz_convert(base_field.type.tz).to_pydatetime()
    else:
        match_time = requested_time.tz_convert(KST).tz_localize(None).to_pydatetime()

    expression = ds.field("base_time") == pa.scalar(
        match_time,
        type=base_field.type,
    )

    station_field = dataset.schema.field("station_id")

    station_filter_values = None

    if pa.types.is_string(station_field.type) or pa.types.is_large_string(
        station_field.type
    ):
        station_filter_values = station_ids

    elif pa.types.is_integer(station_field.type):
        try:
            station_filter_values = [int(value) for value in station_ids]
        except ValueError:
            station_filter_values = None

    if station_filter_values is not None:
        expression = expression & (ds.field("station_id").isin(station_filter_values))

    table = dataset.to_table(
        columns=available_columns,
        filter=expression,
    )

    frame = table.to_pandas()

    if frame.empty:
        return frame

    frame["station_id"] = frame["station_id"].astype(str)

    frame = frame.loc[frame["station_id"].isin(station_ids)].copy()

    return frame


def load_inventory(
    path: Path,
) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(payload, dict):
        records = payload.get("stations")
    else:
        records = payload

    if not isinstance(records, list):
        raise ValueError("inventory JSON must be an array or " '{"stations": [...]}')

    result: dict[str, dict[str, Any]] = {}

    for record in records:
        if not isinstance(record, dict):
            raise ValueError("inventory record must be an object")

        required = {
            "station_id",
            "capacity",
            "bikes_now",
        }

        missing = required - set(record)
        if missing:
            raise ValueError(f"inventory record missing: {sorted(missing)}")

        station_id = record["station_id"]

        if not isinstance(station_id, str):
            raise ValueError("inventory station_id must be a string")

        if station_id in result:
            raise ValueError(f"duplicate inventory station_id: {station_id}")

        result[station_id] = {
            "capacity": record["capacity"],
            "bikes_now": record["bikes_now"],
            "collected_at": record.get("collected_at"),
            "source": record.get("source"),
        }

    return result


def _display_number(
    value: float,
) -> int | float:
    number = float(value)

    if number.is_integer():
        return int(number)

    return number


def _warning(
    code: str,
    message: str,
    *,
    station_id: str | None = None,
    horizon_min: int | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "station_id": station_id,
        "horizon_min": (int(horizon_min) if horizon_min is not None else None),
    }


def _predict_model_horizons(
    candidate: FittedCandidate,
    row: pd.DataFrame,
    horizons: list[int],
) -> tuple[dict[int, float], dict[int, str]]:
    """Run model inference while isolating horizon-level estimator failures."""

    values: dict[int, float] = {}
    errors: dict[int, str] = {}

    preprocessor = getattr(candidate, "preprocessor", None)
    estimators = getattr(candidate, "estimators", None)

    # Real FittedCandidate path.
    #
    # Transform only once per station, then call each horizon estimator
    # independently. This prevents one failed estimator from suppressing
    # otherwise valid horizons.
    if preprocessor is not None and isinstance(estimators, Mapping):
        try:
            transformed = preprocessor.transform(row[candidate.feature_columns])

            if candidate.model_id == "lightgbm":
                transformed = pd.DataFrame(
                    np.asarray(transformed, dtype=np.float32),
                    columns=preprocessor.get_feature_names_out(),
                )

        except Exception as exc:
            reason = (
                "model feature preprocessing failed: " f"{type(exc).__name__}: {exc}"
            )
            return {}, {horizon: reason for horizon in horizons}

        for horizon in horizons:
            try:
                estimator = estimators[horizon]

                raw = np.asarray(
                    estimator.predict(transformed),
                    dtype=np.float64,
                ).reshape(-1)

                if raw.size != 1:
                    raise ValueError(
                        "expected exactly one prediction "
                        f"for {horizon}m, got {raw.size}"
                    )

                value = float(raw[0])

                if not np.isfinite(value):
                    raise ValueError(f"non-finite {horizon}m prediction")

                values[horizon] = value

            except Exception as exc:
                errors[horizon] = f"{type(exc).__name__}: {exc}"

        return values, errors

    # Compatibility path for existing test doubles.
    try:
        predicted = candidate.predict_all(row)
    except Exception as exc:
        reason = "model inference failed: " f"{type(exc).__name__}: {exc}"
        return {}, {horizon: reason for horizon in horizons}

    for horizon in horizons:
        try:
            if horizon not in predicted:
                raise KeyError(f"{horizon}m prediction not returned")

            raw = np.asarray(
                predicted[horizon],
                dtype=np.float64,
            ).reshape(-1)

            if raw.size != 1:
                raise ValueError(
                    "expected exactly one prediction " f"for {horizon}m, got {raw.size}"
                )

            value = float(raw[0])

            if not np.isfinite(value):
                raise ValueError(f"non-finite {horizon}m prediction")

            values[horizon] = value

        except Exception as exc:
            errors[horizon] = f"{type(exc).__name__}: {exc}"

    return values, errors


def _fallback_delta(
    *,
    baselines: FittedBaselines | None,
    row: pd.DataFrame,
    horizon: int,
) -> tuple[float, str]:
    """Return B3 fallback when available, otherwise B1 persistence."""

    if baselines is not None:
        try:
            predicted = baselines.predict_all(
                row,
                "b3_dow_time_mean",
            )

            raw = np.asarray(
                predicted[horizon],
                dtype=np.float64,
            ).reshape(-1)

            if raw.size != 1:
                raise ValueError("B3 expected exactly one prediction")

            value = float(raw[0])

            if np.isfinite(value):
                return value, "b3_dow_time_mean"

        except Exception:
            # B1 is deliberately the final deterministic safety net.
            pass

    return 0.0, "b1_persistence"


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
    baselines: FittedBaselines | None = None,
) -> dict[str, Any]:
    request = validate_prediction_request(request)

    frame = feature_frame.copy()

    if not frame.empty:
        if "station_id" not in frame:
            raise ValueError("feature frame missing station_id")

        frame["station_id"] = frame["station_id"].astype(str)

    missing_model_features = (
        set(candidate.feature_columns) - set(frame.columns)
        if not frame.empty
        else set()
    )

    warnings: list[dict[str, Any]] = []

    valid_station_ids: list[str] = []
    valid_rows: dict[str, pd.DataFrame] = {}
    valid_inventory: dict[str, RuntimeInventory] = {}
    reference_time = pd.Timestamp(request["base_time"]).to_pydatetime()

    for station_id in request["station_ids"]:
        if frame.empty:
            matching = frame
        else:
            matching = frame.loc[frame["station_id"].eq(station_id)]

        if matching.empty:
            warnings.append(
                _warning(
                    "FEATURE_ROW_NOT_FOUND",
                    "feature row not found for base_time",
                    station_id=station_id,
                    horizon_min=None,
                )
            )
            continue

        if len(matching) != 1:
            warnings.append(
                _warning(
                    "FEATURE_UNAVAILABLE",
                    ("expected exactly one feature row " "for base_time."),
                    station_id=station_id,
                )
            )
            continue

        if missing_model_features:
            warnings.append(
                _warning(
                    "FEATURE_UNAVAILABLE",
                    (
                        "required model feature columns are "
                        "unavailable: "
                        f"{sorted(missing_model_features)}"
                    ),
                    station_id=station_id,
                )
            )
            continue

        assessed = assess_inventory(
            station_id,
            inventory.get(station_id),
            reference_time=reference_time,
        )
        if assessed.warning_code:
            warnings.append(
                _warning(
                    assessed.warning_code,
                    assessed.warning_message or "Inventory warning",
                    station_id=station_id,
                )
            )
        if not assessed.usable:
            continue

        valid_station_ids.append(station_id)
        valid_rows[station_id] = matching.iloc[[0]].copy()
        valid_inventory[station_id] = assessed

    prediction_lookup: dict[
        str,
        dict[int, tuple[float, str]],
    ] = {}

    for station_id in valid_station_ids:
        row = valid_rows[station_id]

        model_values, model_errors = _predict_model_horizons(
            candidate,
            row,
            request["horizons"],
        )

        station_predictions: dict[
            int,
            tuple[float, str],
        ] = {}

        for horizon in request["horizons"]:
            if horizon in model_values:
                station_predictions[horizon] = (
                    model_values[horizon],
                    "model",
                )
                continue

            delta_net, fallback_method = _fallback_delta(
                baselines=baselines,
                row=row,
                horizon=horizon,
            )

            reason = model_errors.get(
                horizon,
                "primary model prediction unavailable",
            )

            warnings.append(
                _warning(
                    "BASELINE_FALLBACK",
                    (f"{reason}; used {fallback_method} " "fallback."),
                    station_id=station_id,
                    horizon_min=horizon,
                )
            )

            station_predictions[horizon] = (
                delta_net,
                "baseline_fallback",
            )

        prediction_lookup[station_id] = station_predictions

    response_predictions = []

    for station_id in request["station_ids"]:
        entry: dict[str, Any] = {
            "station_id": station_id,
            "horizon_results": [],
        }

        current = inventory.get(station_id)

        if current is not None:
            try:
                if current.get("capacity") is not None:
                    entry["capacity"] = _display_number(float(current["capacity"]))

                if current.get("bikes_now") is not None:
                    entry["bikes_now"] = _display_number(float(current["bikes_now"]))

            except (TypeError, ValueError):
                pass

            assessed = assess_inventory(
                station_id,
                current,
                reference_time=reference_time,
            )
            entry.update(assessed.provenance())

        if station_id in prediction_lookup:
            assessed = valid_inventory[station_id]

            results = []

            for horizon in request["horizons"]:
                if horizon not in prediction_lookup[station_id]:
                    continue

                delta_net, prediction_source = prediction_lookup[station_id][horizon]

                projection = assessed.project(delta_net)

                results.append(
                    {
                        "horizon_min": horizon,
                        "prediction_source": prediction_source,
                        "delta_net": delta_net,
                        **projection,
                    }
                )

            entry["horizon_results"] = results

        response_predictions.append(entry)

    return {
        "request_id": request["request_id"],
        "base_time": request["base_time"],
        "model_version": model_version,
        # Kept temporarily for backwards compatibility with
        # the existing Week 05 consumer/tests. Horizon-level
        # prediction_source is the v0.2 source contract.
        "source": "model",
        "predictions": response_predictions,
        "warnings": warnings,
    }
