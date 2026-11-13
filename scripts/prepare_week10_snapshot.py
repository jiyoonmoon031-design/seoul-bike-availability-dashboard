from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--snapshot",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--feature-table",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--metadata-output",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    feature_ids = set(
        pd.read_parquet(
            args.feature_table,
            columns=["station_id"],
        )["station_id"]
        .astype(str)
        .str.strip()
        .unique()
    )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    writer = None

    total_rows = 0
    output_rows = 0
    invalid_time = 0
    negative_bikes = 0
    nonpositive_capacity = 0
    bikes_gt_rack_count = 0

    station_ids = set()

    min_time = None
    max_time = None

    try:
        for chunk in pd.read_csv(
            args.snapshot,
            sep="\t",
            encoding="utf-16",
            chunksize=250_000,
        ):
            chunk.columns = [
                str(column).replace("\ufeff", "").strip() for column in chunk.columns
            ]

            total_rows += len(chunk)

            chunk["station_id"] = chunk["station_id"].astype(str).str.strip()

            chunk["collected_at"] = pd.to_datetime(
                chunk["collected_at"],
                errors="coerce",
            )

            chunk["bikes_available"] = pd.to_numeric(
                chunk["bikes_available"],
                errors="coerce",
            )

            chunk["capacity"] = pd.to_numeric(
                chunk["capacity"],
                errors="coerce",
            )

            invalid_time += int(chunk["collected_at"].isna().sum())

            negative_bikes += int((chunk["bikes_available"] < 0).sum())

            nonpositive_capacity += int((chunk["capacity"] <= 0).sum())

            bikes_gt_rack_count += int(
                (chunk["bikes_available"] > chunk["capacity"]).sum()
            )

            chunk = chunk.loc[chunk["station_id"].isin(feature_ids)].copy()

            chunk = chunk.loc[
                chunk["collected_at"].notna()
                & chunk["bikes_available"].notna()
                & chunk["capacity"].notna()
                & chunk["bikes_available"].ge(0)
                & chunk["capacity"].gt(0)
            ].copy()

            chunk["rack_count"] = chunk["capacity"]

            chunk["empty_racks"] = (
                chunk["rack_count"] - chunk["bikes_available"]
            ).clip(lower=0)

            chunk["snapshot_time"] = chunk["collected_at"].dt.floor("5min")

            chunk = chunk[
                [
                    "snapshot_time",
                    "collected_at",
                    "station_id",
                    "bikes_available",
                    "capacity",
                    "rack_count",
                    "empty_racks",
                ]
            ]

            output_rows += len(chunk)

            station_ids.update(chunk["station_id"].unique())

            cmin = chunk["snapshot_time"].min()

            cmax = chunk["snapshot_time"].max()

            if pd.notna(cmin):
                min_time = (
                    cmin
                    if min_time is None
                    else min(
                        min_time,
                        cmin,
                    )
                )

            if pd.notna(cmax):
                max_time = (
                    cmax
                    if max_time is None
                    else max(
                        max_time,
                        cmax,
                    )
                )

            table = pa.Table.from_pandas(
                chunk,
                preserve_index=False,
            )

            if writer is None:
                writer = pq.ParquetWriter(
                    args.output,
                    table.schema,
                    compression="zstd",
                )

            writer.write_table(table)

    finally:
        if writer is not None:
            writer.close()

    metadata = {
        "source": str(args.snapshot),
        "encoding": "UTF-16LE",
        "total_rows": total_rows,
        "output_rows": output_rows,
        "station_count": len(station_ids),
        "snapshot_min": (str(min_time) if min_time is not None else None),
        "snapshot_max": (str(max_time) if max_time is not None else None),
        "invalid_time": invalid_time,
        "negative_bikes": (negative_bikes),
        "nonpositive_capacity": (nonpositive_capacity),
        "bikes_gt_rack_count": (bikes_gt_rack_count),
        "bikes_gt_rack_count_pct": (
            bikes_gt_rack_count / total_rows * 100 if total_rows else 0.0
        ),
        "capacity_semantics": (
            "Seoul API rackTotCnt; "
            "treated as rack count, "
            "not a hard upper bound "
            "on bikes_available"
        ),
        "empty_racks_definition": ("max(rack_count - " "bikes_available, 0)"),
    }

    args.metadata_output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.metadata_output.write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
