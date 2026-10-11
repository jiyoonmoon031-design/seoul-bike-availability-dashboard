from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rebalancing.logic import (  # noqa: E402
    RebalancingConfig,
    build_rebalancing_plan,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a Week 06 operator "
            "rebalancing recommendation "
            "from model predictions"
        )
    )

    parser.add_argument(
        "--prediction",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--station-context",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--horizon",
        required=True,
        type=int,
        choices=(15, 30, 60),
    )

    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
    )

    parser.add_argument(
        "--params",
        type=Path,
        default=Path("config/params.yaml"),
    )

    parser.add_argument(
        "--output",
        type=Path,
    )

    parser.add_argument(
        "--diagnostics-output",
        type=Path,
    )

    return parser.parse_args()


def load_station_context(
    path: Path,
) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(payload, dict):
        records = payload.get("stations")
    else:
        records = payload

    if not isinstance(records, list):
        raise ValueError("station context must be " 'an array or {"stations": [...]}')

    return records


def write_json(
    path: Path,
    payload: object,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()

    params = yaml.safe_load(args.params.read_text(encoding="utf-8"))

    config = RebalancingConfig.from_params(params)

    prediction = json.loads(args.prediction.read_text(encoding="utf-8"))

    station_contexts = load_station_context(args.station_context)

    result = build_rebalancing_plan(
        prediction,
        station_contexts,
        config=config,
        horizon_min=args.horizon,
        top_n=args.top_n,
    )

    if args.output:
        write_json(
            args.output,
            result.response,
        )
    else:
        print(
            json.dumps(
                result.response,
                ensure_ascii=False,
                indent=2,
            )
        )

    diagnostics = {
        "warnings": result.warnings,
        **result.diagnostics,
    }

    if args.diagnostics_output:
        write_json(
            args.diagnostics_output,
            diagnostics,
        )
    elif result.warnings:
        print(
            json.dumps(
                diagnostics,
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
