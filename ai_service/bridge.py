from __future__ import annotations

import copy
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import joblib
import yaml

from src.modeling.final_model import sha256_file
from src.modeling.inference import (
    build_prediction_response,
    load_point_in_time_features,
    validate_prediction_request,
)
from src.modeling.runtime_fallback import apply_runtime_feature_fallback
from src.rebalancing.logic import RebalancingConfig, build_rebalancing_plan
from src.recommendation.logic import RecommendationConfig, recommend_stations

LOGGER = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]

PARAMS_PATH = ROOT / "config" / "params.yaml"

MODEL_PATH = ROOT / "models" / "week05" / "final_model.joblib"

MODEL_METADATA_PATH = ROOT / "reports" / "week05" / "final_model_metadata.json"

FALLBACK_BASELINE_PATH = ROOT / "models" / "week11" / "fallback_baselines.joblib"

FALLBACK_METADATA_PATH = ROOT / "reports" / "week11" / "fallback_baseline_metadata.json"

PREDICT_SCRIPT = ROOT / "scripts" / "run_week05_inference.py"

REBALANCING_SCRIPT = ROOT / "scripts" / "run_week06_rebalancing.py"

RECOMMEND_SCRIPT = ROOT / "scripts" / "run_week08_recommendation.py"

STATION_STATUS_PATH = "/api/v1/stations/status"

PREDICT_LOCK = threading.Lock()
PREDICTION_CACHE_LOCK = threading.Lock()
PREDICTION_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


class BridgeConfigurationError(RuntimeError):
    pass


def _backend_base_url() -> str:
    raw = os.getenv(
        "AI_BACKEND_BASE_URL",
        "",
    ).strip()

    if not raw:
        raise BridgeConfigurationError("AI_BACKEND_BASE_URL is not configured")

    return raw.rstrip("/")


class BridgeExecutionError(RuntimeError):
    pass


def _backend_timeout_seconds() -> float:
    raw = os.getenv(
        "AI_BACKEND_TIMEOUT_SEC",
        "5",
    ).strip()

    try:
        value = float(raw)
    except ValueError as exc:
        raise BridgeConfigurationError(
            "AI_BACKEND_TIMEOUT_SEC must be numeric"
        ) from exc

    if value <= 0:
        raise BridgeConfigurationError("AI_BACKEND_TIMEOUT_SEC must be > 0")

    return value


def _fetch_station_inventory(
    station_ids: list[str],
) -> dict[str, Any]:
    url = _backend_base_url() + STATION_STATUS_PATH

    request = Request(
        url,
        headers={
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urlopen(
            request,
            timeout=_backend_timeout_seconds(),
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))

    except HTTPError as exc:
        raise BridgeExecutionError(
            "backend station-status request failed " f"with HTTP {exc.code}"
        ) from exc

    except (URLError, TimeoutError) as exc:
        raise BridgeExecutionError("backend station-status request failed") from exc

    except json.JSONDecodeError as exc:
        raise BridgeExecutionError(
            "backend station-status response " "is not valid JSON"
        ) from exc

    stations = payload.get("stations")

    if not isinstance(stations, list):
        raise BridgeExecutionError(
            "backend station-status response " "does not contain stations array"
        )

    requested = {str(station_id) for station_id in station_ids}

    selected = []

    for item in stations:
        if not isinstance(item, dict):
            continue

        station_id = item.get("station_id")

        if station_id is None:
            continue

        station_id = str(station_id)

        if station_id not in requested:
            continue

        selected.append(
            {
                "station_id": station_id,
                "capacity": item.get("capacity"),
                "bikes_now": item.get("bikes_now"),
                "collected_at": item.get("collected_at"),
            }
        )

    return {
        "stations": selected,
    }


def _timeout_seconds() -> int:
    raw = os.getenv(
        "AI_SUBPROCESS_TIMEOUT_SEC",
        "180",
    )

    try:
        value = int(raw)
    except ValueError as exc:
        raise BridgeConfigurationError(
            "AI_SUBPROCESS_TIMEOUT_SEC must be an integer"
        ) from exc

    if value <= 0:
        raise BridgeConfigurationError("AI_SUBPROCESS_TIMEOUT_SEC must be > 0")

    return value


def _feature_table_path() -> Path:
    raw = os.getenv(
        "AI_FEATURE_TABLE_PATH",
        "",
    ).strip()

    if not raw:
        raise BridgeConfigurationError("AI_FEATURE_TABLE_PATH is not configured")

    path = Path(raw).expanduser()

    if not path.exists():
        raise BridgeConfigurationError("AI_FEATURE_TABLE_PATH does not exist")

    return path


def _write_json(
    path: Path,
    payload: Any,
) -> None:
    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _read_json(
    path: Path,
) -> Any:
    if not path.exists():
        raise BridgeExecutionError("AI runner did not create output JSON")

    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=8)
def _load_json_cached(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@lru_cache(maxsize=4)
def _load_joblib_verified(path: str, expected_sha256: str) -> Any:
    artifact = Path(path)
    if sha256_file(artifact) != expected_sha256:
        raise BridgeConfigurationError(f"artifact checksum mismatch: {artifact.name}")
    return joblib.load(artifact)


@lru_cache(maxsize=1)
def _params() -> dict[str, Any]:
    return yaml.safe_load(PARAMS_PATH.read_text(encoding="utf-8"))


def _inventory_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = payload.get("stations")
    if not isinstance(records, list):
        raise BridgeExecutionError("inventory payload does not contain stations")
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict) or record.get("station_id") is None:
            continue
        station_id = str(record["station_id"])
        result[station_id] = {
            "capacity": record.get("capacity"),
            "bikes_now": record.get("bikes_now"),
            "collected_at": record.get("collected_at"),
            "source": record.get("source", "backend_station_status"),
        }
    return result


def _cache_key(
    request: dict[str, Any], inventory: dict[str, dict[str, Any]], model_version: str
) -> str:
    stations = []
    for station_id in request["station_ids"]:
        current = inventory.get(station_id, {})
        stations.append(
            (
                station_id,
                current.get("capacity"),
                current.get("bikes_now"),
                current.get("collected_at"),
            )
        )
    return json.dumps(
        {
            "model_version": model_version,
            "base_time": request["base_time"],
            "horizons": request["horizons"],
            "stations": stations,
        },
        sort_keys=True,
        default=str,
    )


def _cache_ttl_seconds() -> float:
    raw = os.getenv("AI_PREDICTION_CACHE_TTL_SEC", "30")
    try:
        return max(0.0, float(raw))
    except ValueError as exc:
        raise BridgeConfigurationError(
            "AI_PREDICTION_CACHE_TTL_SEC must be numeric"
        ) from exc


def _predict_in_process(
    payload: dict[str, Any], inventory_payload: dict[str, Any], feature_table: Path
) -> dict[str, Any]:
    request = validate_prediction_request(payload)
    metadata = _load_json_cached(str(MODEL_METADATA_PATH))
    feature_names = _load_json_cached(str(ROOT / "reports/week05/feature_names.json"))
    raw_feature_order = list(feature_names["raw_feature_order"])
    inventory = _inventory_map(inventory_payload)

    cache_key = _cache_key(request, inventory, metadata["model_version"])
    now = time.monotonic()
    with PREDICTION_CACHE_LOCK:
        cached = PREDICTION_CACHE.get(cache_key)
        if cached and now - cached[0] <= _cache_ttl_seconds():
            response = copy.deepcopy(cached[1])
            response["request_id"] = request["request_id"]
            response["runtime"] = {"cache_hit": True}
            return response

    feature_started = time.perf_counter()
    frame = load_point_in_time_features(
        feature_table,
        feature_columns=raw_feature_order,
        station_ids=request["station_ids"],
        base_time=request["base_time"],
    )
    feature_ms = (time.perf_counter() - feature_started) * 1000

    model_loaded = False
    if frame.empty:
        candidate = SimpleNamespace(feature_columns=raw_feature_order)
    else:
        candidate = _load_joblib_verified(
            str(MODEL_PATH), metadata["model_artifact"]["sha256"]
        )
        model_loaded = True

    baselines = None
    if FALLBACK_BASELINE_PATH.exists() and FALLBACK_METADATA_PATH.exists():
        fallback_metadata = _load_json_cached(str(FALLBACK_METADATA_PATH))
        baselines = _load_joblib_verified(
            str(FALLBACK_BASELINE_PATH),
            fallback_metadata["artifact"]["sha256"],
        )

    inference_started = time.perf_counter()
    response = build_prediction_response(
        candidate=candidate,
        request=request,
        feature_frame=frame,
        inventory=inventory,
        model_version=metadata["model_version"],
        baselines=baselines,
    )
    response = apply_runtime_feature_fallback(
        response=response,
        request=request,
        inventory=inventory,
        baselines=baselines,
    )
    inference_ms = (time.perf_counter() - inference_started) * 1000
    response["runtime"] = {
        "cache_hit": False,
        "feature_read_ms": round(feature_ms, 3),
        "inference_ms": round(inference_ms, 3),
        "primary_model_loaded": model_loaded,
    }

    with PREDICTION_CACHE_LOCK:
        if len(PREDICTION_CACHE) >= 128:
            oldest = min(PREDICTION_CACHE, key=lambda key: PREDICTION_CACHE[key][0])
            PREDICTION_CACHE.pop(oldest, None)
        PREDICTION_CACHE[cache_key] = (now, copy.deepcopy(response))
    return response


def _run(
    args: list[str],
) -> None:
    process = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=_timeout_seconds(),
        check=False,
    )

    if process.returncode == 0:
        return

    LOGGER.error(
        "AI runner failed: rc=%s stderr=%s",
        process.returncode,
        process.stderr[-3000:],
    )

    raise BridgeExecutionError("AI runner execution failed")


def health_status() -> dict[str, Any]:
    feature_raw = os.getenv(
        "AI_FEATURE_TABLE_PATH",
        "",
    ).strip()

    backend_raw = os.getenv(
        "AI_BACKEND_BASE_URL",
        "",
    ).strip()

    feature_exists = bool(feature_raw and Path(feature_raw).expanduser().exists())

    backend_configured = bool(backend_raw)

    predict_ready = all(
        [
            PREDICT_SCRIPT.exists(),
            MODEL_PATH.exists(),
            MODEL_METADATA_PATH.exists(),
            feature_exists,
            backend_configured,
        ]
    )

    rebalancing_ready = all(
        [
            REBALANCING_SCRIPT.exists(),
            PARAMS_PATH.exists(),
        ]
    )

    recommendation_ready = all(
        [
            RECOMMEND_SCRIPT.exists(),
            PARAMS_PATH.exists(),
        ]
    )

    return {
        "service": "seoul-bike-ai",
        "status": (
            "ready"
            if (predict_ready and rebalancing_ready and recommendation_ready)
            else "degraded"
        ),
        "ready": (predict_ready and rebalancing_ready and recommendation_ready),
        "components": {
            "predict": {
                "ready": predict_ready,
                "model_present": MODEL_PATH.exists(),
                "metadata_present": MODEL_METADATA_PATH.exists(),
                "feature_table_present": feature_exists,
                "backend_station_status_configured": backend_configured,
            },
            "rebalancing": {
                "ready": rebalancing_ready,
            },
            "recommendation": {
                "ready": recommendation_ready,
            },
        },
    }


def run_predict(
    payload: dict[str, Any],
) -> dict[str, Any]:
    started = time.perf_counter()
    feature_table = _feature_table_path()

    station_ids = [
        str(station_id)
        for station_id in payload.get(
            "station_ids",
            [],
        )
    ]

    inventory_started = time.perf_counter()
    inventory_payload = _fetch_station_inventory(station_ids)
    inventory_ms = (time.perf_counter() - inventory_started) * 1000

    fallback_artifact_exists = FALLBACK_BASELINE_PATH.exists()
    fallback_metadata_exists = FALLBACK_METADATA_PATH.exists()
    if fallback_artifact_exists != fallback_metadata_exists:
        raise BridgeConfigurationError(
            "Week 11 fallback artifact and metadata must either both exist or both be absent"
        )

    with PREDICT_LOCK:
        result = _predict_in_process(payload, inventory_payload, feature_table)

    runtime = result.setdefault("runtime", {})
    runtime["inventory_fetch_ms"] = round(inventory_ms, 3)
    runtime["total_ms"] = round((time.perf_counter() - started) * 1000, 3)
    return result


def run_rebalancing(
    payload: dict[str, Any],
) -> dict[str, Any]:
    started = time.perf_counter()
    result = build_rebalancing_plan(
        payload["prediction_response"],
        payload["station_contexts"],
        config=RebalancingConfig.from_params(_params()),
        horizon_min=int(payload["horizon_min"]),
        top_n=int(payload["top_n"]),
    )
    if result.warnings:
        LOGGER.warning("rebalancing warnings=%s", len(result.warnings))
    response = dict(result.response)
    response["runtime"] = {
        "total_ms": round((time.perf_counter() - started) * 1000, 3),
        "warning_count": len(result.warnings),
    }
    return response


def run_recommendation(
    payload: dict[str, Any],
) -> dict[str, Any]:
    started = time.perf_counter()
    result = recommend_stations(
        payload["candidates"],
        leg=payload["leg"],
        eta_min=float(payload["eta_min"]),
        config=RecommendationConfig.from_params(_params()),
        top_n=int(payload["top_n"]),
    )
    if result.warnings:
        LOGGER.warning("recommendation warnings=%s", result.warnings)
    response = dict(result.response)
    response["runtime"] = {
        "total_ms": round((time.perf_counter() - started) * 1000, 3),
        "warning_count": len(result.warnings),
    }
    return response
