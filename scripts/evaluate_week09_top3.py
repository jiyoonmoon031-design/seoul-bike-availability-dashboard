from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.validation.recommendation import evaluate_top3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate Week 09 Top-3 rent/return availability hit rates."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    raise ValueError("input must be CSV or Parquet")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    result = evaluate_top3(read_table(args.input))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    result.metrics.to_csv(args.output_dir / "top3_hit_rate.csv", index=False)
    result.request_results.to_csv(
        args.output_dir / "top3_request_results.csv",
        index=False,
    )
    metadata = {
        **result.metadata,
        "input_path": str(args.input),
        "input_sha256": sha256(args.input),
        "minimum_threshold": 1,
        "stable_threshold": 2,
        "target_hit_rate": 0.90,
    }
    (args.output_dir / "evaluation_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
