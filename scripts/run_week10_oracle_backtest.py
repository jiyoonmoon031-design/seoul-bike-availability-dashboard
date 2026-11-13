from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from src.evaluation.oracle_rebalancing import (  # noqa: E402
    evaluate_oracle_case,
)
from src.evaluation.rebalancing_backtest import (  # noqa: E402
    summarize_backtests,
)
from src.rebalancing.logic import (  # noqa: E402
    RebalancingConfig,
    haversine_km,
)


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--snapshot",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--station-master",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--demand-profile",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--params",
        type=Path,
        default=Path("config/params.yaml"),
    )

    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--max-base-times",
        type=int,
    )

    return parser.parse_args()


def main():
    args = parse_args()

    params = yaml.safe_load(args.params.read_text(encoding="utf-8"))

    config = RebalancingConfig.from_params(params)

    snapshot = pd.read_parquet(
        args.snapshot,
        columns=[
            "snapshot_time",
            "station_id",
            "bikes_available",
            "rack_count",
        ],
    )

    snapshot["snapshot_time"] = pd.to_datetime(snapshot["snapshot_time"])

    snapshot["station_id"] = snapshot["station_id"].astype(str)

    if snapshot.duplicated(
        [
            "snapshot_time",
            "station_id",
        ]
    ).any():
        raise ValueError("duplicate snapshot bucket")

    base = snapshot.loc[snapshot["snapshot_time"].dt.minute.mod(15).eq(0)].copy()

    base = base.rename(
        columns={
            "snapshot_time": ("base_time"),
            "bikes_available": ("bikes_now"),
        }
    )

    capacity_change_pairs = {}

    for horizon in config.horizons:
        future = snapshot[
            [
                "snapshot_time",
                "station_id",
                "bikes_available",
                "rack_count",
            ]
        ].copy()

        future["base_time"] = future["snapshot_time"] - pd.Timedelta(minutes=horizon)

        future = future.rename(
            columns={
                "bikes_available": (f"future_bikes_h" f"{horizon}"),
                "rack_count": (f"future_rack_h" f"{horizon}"),
            }
        )

        future = future[
            [
                "base_time",
                "station_id",
                f"future_bikes_h" f"{horizon}",
                f"future_rack_h" f"{horizon}",
            ]
        ]

        base = base.merge(
            future,
            on=[
                "base_time",
                "station_id",
            ],
            how="left",
            validate="one_to_one",
        )

        changed = base[f"future_rack_h" f"{horizon}"].notna() & (
            base[f"future_rack_h" f"{horizon}"] != base["rack_count"]
        )

        capacity_change_pairs[horizon] = int(changed.sum())

        base.loc[
            changed,
            f"future_bikes_h" f"{horizon}",
        ] = pd.NA

    master = pd.read_parquet(args.station_master)

    base = base.merge(
        master[
            [
                "station_id",
                "station_name",
                "district",
                "latitude",
                "longitude",
            ]
        ],
        on="station_id",
        how="left",
        validate="many_to_one",
    )

    profile = pd.read_parquet(args.demand_profile)

    base["weekday"] = base["base_time"].dt.weekday
    base["hour"] = base["base_time"].dt.hour
    base["minute"] = base["base_time"].dt.minute

    base = base.merge(
        profile[
            [
                "station_id",
                "weekday",
                "hour",
                "minute",
                "same_dow_time_mean_rent",
            ]
        ],
        on=[
            "station_id",
            "weekday",
            "hour",
            "minute",
        ],
        how="left",
        validate="many_to_one",
    )

    master_records = (
        master[
            [
                "station_id",
                "latitude",
                "longitude",
            ]
        ]
        .drop_duplicates("station_id")
        .to_dict("records")
    )

    distance_lookup = {}

    for demand in master_records:
        for supply in master_records:
            demand_id = str(demand["station_id"])
            supply_id = str(supply["station_id"])

            distance_lookup[
                (
                    demand_id,
                    supply_id,
                )
            ] = (
                haversine_km(
                    float(demand["latitude"]),
                    float(demand["longitude"]),
                    float(supply["latitude"]),
                    float(supply["longitude"]),
                )
                * config.detour_factor
            )

    base_times = sorted(base["base_time"].drop_duplicates().tolist())

    if args.max_base_times:
        base_times = base_times[: args.max_base_times]

    selected_times = set(base_times)

    base = base.loc[base["base_time"].isin(selected_times)].copy()

    details = []
    effects = []
    moves = []

    grouped = base.groupby(
        "base_time",
        sort=True,
    )

    total = len(base_times)

    for index, (
        base_time,
        frame,
    ) in enumerate(grouped, 1):
        stations = []

        for row in frame.itertuples(index=False):
            future = {}

            for horizon in config.horizons:
                value = getattr(
                    row,
                    f"future_bikes_h" f"{horizon}",
                )

                if pd.notna(value):
                    future[horizon] = float(value)

            stations.append(
                {
                    "station_id": (str(row.station_id)),
                    "station_name": (row.station_name),
                    "district": (row.district),
                    "latitude": (row.latitude),
                    "longitude": (row.longitude),
                    "rack_count": (row.rack_count),
                    "bikes_now": (row.bikes_now),
                    "same_dow_time_mean_rent": (row.same_dow_time_mean_rent),
                    "future_bikes_by_horizon": (future),
                }
            )

        for horizon in config.horizons:
            result = evaluate_oracle_case(
                stations,
                base_time=(pd.Timestamp(base_time).to_pydatetime()),
                config=config,
                horizon_min=horizon,
                distance_lookup=(distance_lookup),
            )

            detail = result["detail"]

            details.append(detail)

            for row in result["station_effects"]:
                effects.append(
                    {
                        "base_time": (detail["base_time"]),
                        "horizon_min": (horizon),
                        **row,
                    }
                )

            for row in result["move_matches"]:
                moves.append(
                    {
                        "base_time": (detail["base_time"]),
                        "horizon_min": (horizon),
                        **row,
                    }
                )

        if index % 500 == 0 or index == total:
            print(f"processed " f"{index}/{total} " f"base times")

    summary = summarize_backtests(details)

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    pd.DataFrame(details).to_csv(
        args.output_dir / "oracle_backtest_detail.csv",
        index=False,
    )

    pd.DataFrame(effects).to_parquet(
        args.output_dir / "oracle_station_effects.parquet",
        index=False,
    )

    pd.DataFrame(moves).to_csv(
        args.output_dir / "oracle_move_matches.csv",
        index=False,
    )

    pd.DataFrame(summary).to_csv(
        args.output_dir / "oracle_backtest_summary.csv",
        index=False,
    )

    payload = {
        "evaluation_type": ("oracle_counterfactual_upper_bound"),
        "assumptions": [
            (
                "Observed station snapshot "
                "at t+h is treated as "
                "perfect future inventory."
            ),
            (
                "Recommended moves are "
                "assumed completed within "
                "the selected horizon."
            ),
            ("Vehicle route/travel time " "is not simulated."),
            (
                "Snapshot capacity is "
                "interpreted as rack count, "
                "not a hard upper bound on "
                "bikes_available."
            ),
            ("Future empty racks are " "max(rack_count - " "future_bikes, 0)."),
            ("Station-horizon pairs " "crossing a rack-count " "change are excluded."),
        ],
        "base_time_count": total,
        "capacity_change_pairs_skipped": (capacity_change_pairs),
        "summary": summary,
    }

    (args.output_dir / "oracle_backtest_summary.json").write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print(
        "Cases:",
        len(details),
    )
    print(
        "Affected station rows:",
        len(effects),
    )
    print(
        "Move matches:",
        len(moves),
    )
    print(
        "Output:",
        args.output_dir,
    )


if __name__ == "__main__":
    main()
