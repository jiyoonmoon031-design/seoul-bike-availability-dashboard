from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.validation.recommendation_report import write_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the Week 09 hold-out recommendation report."
    )
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--figure", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    write_report(args.metrics, args.metadata, args.report, args.figure)


if __name__ == "__main__":
    main()
