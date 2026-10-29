from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]

PARAMS_PATH = ROOT / "config" / "params.yaml"

MODEL_PATH = ROOT / "models" / "week05" / "final_model.joblib"

MODEL_METADATA_PATH = ROOT / "reports" / "week05" / "final_model_metadata.json"

PREDICT_SCRIPT = ROOT / "scripts" / "run_week05_inference.py"

REBALANCING_SCRIPT = ROOT / "scripts" / "run_week06_rebalancing.py"

RECOMMEND_SCRIPT = ROOT / "scripts" / "run_week08_recommendation.py"

PREDICT_LOCK = threading.Lock()


class BridgeConfigurationError(RuntimeError):
    pass


class BridgeExecutionError(RuntimeError):
    pass


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


def _inventory_path() -> Path:
    raw = os.getenv(
        "AI_INVENTORY_PATH",
        "",
    ).strip()

    if not raw:
        raise BridgeConfigurationError("AI_INVENTORY_PATH " "is not configured")

    path = Path(raw).expanduser()

    if not path.exists():
        raise BridgeConfigurationError("AI_INVENTORY_PATH " "does not exist")

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

    inventory_raw = os.getenv(
        "AI_INVENTORY_PATH",
        "",
    ).strip()

    feature_exists = bool(feature_raw and Path(feature_raw).expanduser().exists())

    inventory_exists = bool(inventory_raw and Path(inventory_raw).expanduser().exists())

    predict_ready = all(
        [
            PREDICT_SCRIPT.exists(),
            MODEL_PATH.exists(),
            MODEL_METADATA_PATH.exists(),
            feature_exists,
            inventory_exists,
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
                "inventory_adapter_present": inventory_exists,
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
    feature_table = _feature_table_path()

    inventory_path = _inventory_path()

    with PREDICT_LOCK:
        with tempfile.TemporaryDirectory(prefix="seoul-bike-predict-") as directory:
            base = Path(directory)

            request_path = base / "request.json"

            output_path = base / "output.json"

            _write_json(
                request_path,
                payload,
            )

            _run(
                [
                    sys.executable,
                    str(PREDICT_SCRIPT),
                    "--request",
                    str(request_path),
                    "--feature-table",
                    str(feature_table),
                    "--inventory",
                    str(inventory_path),
                    "--output",
                    str(output_path),
                ]
            )

            return _read_json(output_path)


def run_rebalancing(
    payload: dict[str, Any],
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="seoul-bike-rebalance-") as directory:
        base = Path(directory)

        prediction_path = base / "prediction.json"
        context_path = base / "station_context.json"
        output_path = base / "output.json"
        diagnostics_path = base / "diagnostics.json"

        _write_json(
            prediction_path,
            payload["prediction_response"],
        )

        _write_json(
            context_path,
            payload["station_contexts"],
        )

        _run(
            [
                sys.executable,
                str(REBALANCING_SCRIPT),
                "--prediction",
                str(prediction_path),
                "--station-context",
                str(context_path),
                "--horizon",
                str(payload["horizon_min"]),
                "--top-n",
                str(payload["top_n"]),
                "--params",
                str(PARAMS_PATH),
                "--output",
                str(output_path),
                "--diagnostics-output",
                str(diagnostics_path),
            ]
        )

        result = _read_json(output_path)

        if diagnostics_path.exists():
            diagnostics = _read_json(diagnostics_path)

            warning_count = diagnostics.get(
                "warning_count",
                0,
            )

            if warning_count:
                LOGGER.warning(
                    "rebalancing warnings=%s",
                    warning_count,
                )

        return result


def run_recommendation(
    payload: dict[str, Any],
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="seoul-bike-recommend-") as directory:
        base = Path(directory)

        input_path = base / "input.json"
        output_path = base / "output.json"

        _write_json(
            input_path,
            {"candidates": payload["candidates"]},
        )

        _run(
            [
                sys.executable,
                str(RECOMMEND_SCRIPT),
                "--input",
                str(input_path),
                "--leg",
                payload["leg"],
                "--eta-min",
                str(payload["eta_min"]),
                "--top-n",
                str(payload["top_n"]),
                "--params",
                str(PARAMS_PATH),
                "--output",
                str(output_path),
            ]
        )

        result = _read_json(output_path)

        warnings = result.pop(
            "warnings",
            [],
        )

        if warnings:
            LOGGER.warning(
                "recommendation warnings=%s",
                warnings,
            )

        return result
