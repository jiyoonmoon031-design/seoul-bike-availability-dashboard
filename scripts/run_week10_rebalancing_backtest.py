from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from src.evaluation.rebalancing_backtest import (  # noqa: E402
    evaluate_rebalancing_case,
    summarize_backtests,
)
from src.rebalancing.logic import (  # noqa: E402
    RebalancingConfig,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate Week 10 rebalancing " "counterfactual shortage reduction"
        )
    )

    parser.add_argument(
        "--prediction",
        required=True,
        type=Path,
        nargs="+",
    )

    parser.add_argument(
        "--station-context",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--params",
        type=Path,
        default=Path("config/params.yaml"),
    )

    parser.add_argument(
        "--horizons",
        type=int,
        nargs="*",
        choices=(15, 30, 60),
    )

    parser.add_argument(
        "--detail-output",
        type=Path,
        default=Path("reports/week10/" "rebalancing_backtest_detail.csv"),
    )

    parser.add_argument(
        "--station-output",
        type=Path,
        default=Path("reports/week10/" "rebalancing_station_effects.csv"),
    )

    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("reports/week10/" "rebalancing_backtest_summary.csv"),
    )

    parser.add_argument(
        "--summary-json-output",
        type=Path,
        default=Path("reports/week10/" "rebalancing_backtest_summary.json"),
    )

    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_prediction_cases(
    paths: list[Path],
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    for path in paths:
        payload = load_json(path)

        if isinstance(payload, list):
            candidates = payload
        elif isinstance(payload, dict) and isinstance(
            payload.get("cases"),
            list,
        ):
            candidates = payload["cases"]
        else:
            candidates = [payload]

        for candidate in candidates:
            if not isinstance(
                candidate,
                dict,
            ):
                raise ValueError(f"{path}: prediction case " "must be a JSON object")

            cases.append(candidate)

    return cases


def load_station_context(
    path: Path,
) -> list[dict[str, Any]]:
    payload = load_json(path)

    if isinstance(payload, dict):
        records = payload.get("stations")
    else:
        records = payload

    if not isinstance(records, list):
        raise ValueError("station context must be " 'an array or {"stations": [...]}')

    return records


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not rows:
        path.write_text(
            "",
            encoding="utf-8",
        )
        return

    fieldnames = list(rows[0].keys())

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()

    params = yaml.safe_load(args.params.read_text(encoding="utf-8"))

    config = RebalancingConfig.from_params(params)

    horizons = tuple(args.horizons) if args.horizons else config.horizons

    station_contexts = load_station_context(args.station_context)

    prediction_cases = load_prediction_cases(args.prediction)

    case_rows: list[dict[str, Any]] = []
    station_rows: list[dict[str, Any]] = []

    for prediction in prediction_cases:
        for horizon_min in horizons:
            result = evaluate_rebalancing_case(
                prediction,
                station_contexts,
                config=config,
                horizon_min=horizon_min,
            )

            station_rows.extend(result.pop("station_effects"))

            case_rows.append(result)

    summaries = summarize_backtests(case_rows)

    write_csv(
        args.detail_output,
        case_rows,
    )

    write_csv(
        args.station_output,
        station_rows,
    )

    write_csv(
        args.summary_output,
        summaries,
    )

    args.summary_json_output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.summary_json_output.write_text(
        json.dumps(
            {
                "assumptions": [
                    (
                        "All recommended moves are "
                        "assumed completed within "
                        "the selected horizon."
                    ),
                    ("Vehicle routing and actual " "travel time are not simulated."),
                    ("VEHICLE_CAP is the current " "project assumption."),
                ],
                "summary": summaries,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Cases: {len(case_rows)}")
    print(f"Station rows: {len(station_rows)}")
    print(f"Detail: {args.detail_output}")
    print(f"Summary: {args.summary_output}")


if __name__ == "__main__":
    main()
