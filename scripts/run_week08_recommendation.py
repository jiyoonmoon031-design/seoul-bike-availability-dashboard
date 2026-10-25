from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.recommendation.logic import (
    RecommendationConfig,
    recommend_stations,
)


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--leg",
        choices=["origin", "destination"],
        required=True,
    )
    parser.add_argument(
        "--eta-min",
        type=float,
        required=True,
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=3,
    )
    parser.add_argument(
        "--params",
        type=Path,
        default=Path("config/params.yaml"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )

    return parser.parse_args()


def main():
    args = parse_args()

    params = yaml.safe_load(args.params.read_text(encoding="utf-8"))

    payload = json.loads(args.input.read_text(encoding="utf-8"))

    config = RecommendationConfig.from_params(params)

    result = recommend_stations(
        payload["candidates"],
        leg=args.leg,
        eta_min=args.eta_min,
        config=config,
        top_n=args.top_n,
    )

    output = {
        **result.response,
        "warnings": result.warnings,
    }

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
