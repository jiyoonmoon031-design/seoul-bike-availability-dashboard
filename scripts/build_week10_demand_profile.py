from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

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

    parquet = pq.ParquetFile(args.feature_table)

    sums: dict[tuple, float] = defaultdict(float)
    counts: dict[tuple, int] = defaultdict(int)
    names: dict[str, str] = {}
    districts: dict[str, str] = {}

    input_rows = 0
    observed_rows = 0

    min_time = None
    max_time = None

    columns = [
        "station_id",
        "station_name",
        "district",
        "base_time",
        "rent_count",
        "is_observed",
    ]

    for batch in parquet.iter_batches(
        batch_size=250_000,
        columns=columns,
    ):
        frame = batch.to_pandas()

        input_rows += len(frame)

        frame["station_id"] = frame["station_id"].astype(str).str.strip()

        frame["base_time"] = pd.to_datetime(
            frame["base_time"],
            errors="coerce",
        )

        frame["rent_count"] = pd.to_numeric(
            frame["rent_count"],
            errors="coerce",
        )

        frame = frame.loc[
            frame["base_time"].notna() & frame["rent_count"].notna()
        ].copy()

        if "is_observed" in frame:
            frame = frame.loc[frame["is_observed"].fillna(False)].copy()

        observed_rows += len(frame)

        if frame.empty:
            continue

        cmin = frame["base_time"].min()
        cmax = frame["base_time"].max()

        min_time = cmin if min_time is None else min(min_time, cmin)

        max_time = cmax if max_time is None else max(max_time, cmax)

        frame["weekday"] = frame["base_time"].dt.weekday
        frame["hour"] = frame["base_time"].dt.hour
        frame["minute"] = frame["base_time"].dt.minute

        for row in (
            frame[
                [
                    "station_id",
                    "station_name",
                    "district",
                ]
            ]
            .drop_duplicates("station_id")
            .itertuples(index=False)
        ):
            names[row.station_id] = str(row.station_name)
            districts[row.station_id] = str(row.district)

        grouped = (
            frame.groupby(
                [
                    "station_id",
                    "weekday",
                    "hour",
                    "minute",
                ],
                observed=True,
            )["rent_count"]
            .agg(["sum", "count"])
            .reset_index()
        )

        for row in grouped.itertuples(index=False):
            key = (
                str(row.station_id),
                int(row.weekday),
                int(row.hour),
                int(row.minute),
            )

            sums[key] += float(row.sum)
            counts[key] += int(row.count)

    rows = []

    for key in sorted(sums):
        station_id, weekday, hour, minute = key

        count = counts[key]

        if count <= 0:
            continue

        rows.append(
            {
                "station_id": station_id,
                "station_name": names.get(station_id),
                "district": districts.get(station_id),
                "weekday": weekday,
                "hour": hour,
                "minute": minute,
                "same_dow_time_mean_rent": (sums[key] / count),
                "history_observation_count": count,
            }
        )

    result = pd.DataFrame(rows)

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_parquet(
        args.output,
        index=False,
    )

    metadata = {
        "source": str(args.feature_table),
        "input_rows": input_rows,
        "observed_rows": observed_rows,
        "profile_rows": len(result),
        "station_count": int(result["station_id"].nunique()),
        "history_min": str(min_time),
        "history_max": str(max_time),
        "definition": (
            "mean historical rent_count by " "station_id x weekday x hour x minute"
        ),
        "causality_note": (
            "Profile source ends before the " "2026-08-24 oracle evaluation period."
        ),
    }

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
