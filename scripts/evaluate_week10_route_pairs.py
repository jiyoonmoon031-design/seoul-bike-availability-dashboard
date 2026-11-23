from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


KST = "Asia/Seoul"
EARTH_RADIUS_KM = 6371.0
DETOUR_FACTOR = 1.3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate Best-3 route-pair availability on inventory snapshots."
    )
    parser.add_argument("--snapshots", type=Path, required=True)
    parser.add_argument("--stations", type=Path, required=True)
    parser.add_argument("--params", type=Path, default=Path("config/params.yaml"))
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def haversine_matrix(stations: pd.DataFrame) -> np.ndarray:
    lat = np.radians(stations["latitude"].to_numpy(dtype=float))
    lon = np.radians(stations["longitude"].to_numpy(dtype=float))
    dlat = lat[:, None] - lat[None, :]
    dlon = lon[:, None] - lon[None, :]
    value = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_KM * np.arctan2(np.sqrt(value), np.sqrt(1.0 - value))


def load_snapshots(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, sep="\t", encoding="utf-16")
    required = {"collected_at", "station_id", "bikes_available", "capacity"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"missing snapshot columns: {sorted(missing)}")
    collected = pd.to_datetime(frame["collected_at"], errors="raise", utc=True)
    frame["slot_kst"] = collected.dt.tz_convert(KST).dt.round("5min")
    frame["station_id"] = frame["station_id"].astype(str)
    if frame.duplicated(["slot_kst", "station_id"]).any():
        raise ValueError("snapshot rows collide after five-minute normalization")
    return frame


def complete_test_dates(frame: pd.DataFrame, station_count: int, days: int) -> list:
    profile = (
        frame.assign(date_kst=frame["slot_kst"].dt.date)
        .groupby("date_kst")
        .agg(rows=("station_id", "size"), slots=("slot_kst", "nunique"))
    )
    profile["coverage"] = profile["rows"] / (station_count * 288)
    complete = profile[(profile["slots"] == 288) & (profile["coverage"] >= 0.95)]
    if len(complete) < days:
        raise ValueError(f"only {len(complete)} complete dates; {days} required")
    return list(complete.tail(days).index)


def station_candidates(distance_km: np.ndarray) -> list[np.ndarray]:
    # Backend fallback distance is straight distance * 1.3 and caps candidates at 20.
    candidates = []
    for row in distance_km:
        order = np.argsort(row)
        selected = order[(row[order] * DETOUR_FACTOR * 1000.0) <= 800.0][:20]
        if not len(selected):
            selected = order[(row[order] * DETOUR_FACTOR * 1000.0) <= 1200.0][:20]
        candidates.append(selected)
    return candidates


def score_station(distance_m: np.ndarray, available: np.ndarray) -> np.ndarray:
    distance_score = 1.0 - np.minimum(np.maximum(distance_m, 0.0) / 800.0, 1.0)
    availability_score = np.minimum(np.maximum(available, 0.0) / 3.0, 1.0)
    return 0.5 * distance_score + 0.5 * availability_score


def inverse_score(value: float, maximum: float) -> float:
    return 1.0 - min(max(value, 0.0) / maximum, 1.0)


def build_baseline(
    bikes: pd.DataFrame, train_end: pd.Timestamp, horizons: tuple[int, ...]
) -> tuple[dict[int, pd.DataFrame], dict[int, pd.Series]]:
    train = bikes.loc[bikes.index < train_end]
    group_frames: dict[int, pd.DataFrame] = {}
    global_means: dict[int, pd.Series] = {}
    for horizon in horizons:
        shifted = bikes.reindex(train.index + pd.Timedelta(minutes=horizon))
        shifted.index = train.index
        delta = shifted - train
        stacked = delta.stack(future_stack=True).rename("delta").reset_index()
        stacked.columns = ["slot_kst", "station_id", "delta"]
        stacked["weekday"] = stacked["slot_kst"].dt.weekday
        stacked["hour"] = stacked["slot_kst"].dt.hour
        stacked["minute"] = stacked["slot_kst"].dt.minute
        group_frames[horizon] = (
            stacked.groupby(["station_id", "weekday", "hour", "minute"])["delta"]
            .mean()
            .unstack("station_id")
        )
        global_means[horizon] = stacked.groupby("station_id")["delta"].mean()
    return group_frames, global_means


def predicted_delta(
    slot: pd.Timestamp,
    horizon: int,
    station_ids: list[str],
    groups: dict[int, pd.DataFrame],
    globals_: dict[int, pd.Series],
) -> np.ndarray:
    key = (slot.weekday(), slot.hour, slot.minute)
    group = groups[horizon]
    try:
        values = group.loc[key].reindex(station_ids)
    except KeyError:
        values = pd.Series(index=station_ids, dtype=float)
    return values.fillna(globals_[horizon].reindex(station_ids)).fillna(0.0).to_numpy()


def main() -> None:
    args = parse_args()
    params = yaml.safe_load(args.params.read_text(encoding="utf-8"))
    horizons = tuple(int(value) for value in params["HORIZONS"])
    test_days = int(params["EVALUATION"]["test_days"])
    minimum_history_days = int(params["EVALUATION"]["minimum_history_days"])

    snapshots = load_snapshots(args.snapshots)
    stations = pd.read_csv(args.stations)
    snapshot_ids = set(snapshots["station_id"].unique())
    stations = (
        stations[stations["station_id"].astype(str).isin(snapshot_ids)]
        .dropna(subset=["latitude", "longitude"])
        .sort_values("station_id")
        .reset_index(drop=True)
    )
    station_ids = stations["station_id"].astype(str).tolist()
    snapshots = snapshots[snapshots["station_id"].isin(station_ids)]

    test_dates = complete_test_dates(snapshots, len(station_ids), test_days)
    test_start = pd.Timestamp(test_dates[0], tz=KST)
    test_end = pd.Timestamp(test_dates[-1], tz=KST) + pd.Timedelta(days=1)
    observed_days = (test_start - snapshots["slot_kst"].min()).total_seconds() / 86400

    bikes = snapshots.pivot(
        index="slot_kst", columns="station_id", values="bikes_available"
    )
    capacity = snapshots.pivot(
        index="slot_kst", columns="station_id", values="capacity"
    )
    bikes = bikes.reindex(columns=station_ids).sort_index()
    capacity = capacity.reindex(columns=station_ids).sort_index()
    groups, globals_ = build_baseline(bikes, test_start, horizons)

    distance_km = haversine_matrix(stations)
    nearby = station_candidates(distance_km)
    pair_offset = max(1, len(station_ids) // 2)
    destination_anchor = {
        index: (index + pair_offset) % len(station_ids)
        for index in range(len(station_ids))
    }

    request_digest = hashlib.sha256()
    result_rows: list[dict] = []
    excluded_no_base = 0
    excluded_no_route = 0
    excluded_no_actual = 0
    candidate_shortage = 0
    base_over_capacity = 0
    future_over_capacity = 0
    request_count = 0

    request_slots = pd.DatetimeIndex(
        [
            slot
            for date in test_dates
            for slot in pd.date_range(
                pd.Timestamp(date, tz=KST),
                periods=96,
                freq="15min",
            )
        ]
    )
    for slot in request_slots:
        if slot not in bikes.index:
            excluded_no_base += len(station_ids) * len(horizons)
            continue
        bikes_now = bikes.loc[slot].to_numpy(dtype=float)
        capacity_now = capacity.loc[slot].to_numpy(dtype=float)
        valid_now = (
            np.isfinite(bikes_now)
            & np.isfinite(capacity_now)
            & (capacity_now > 0)
            & (bikes_now >= 0)
            & (bikes_now <= capacity_now)
        )
        base_over_capacity += int(
            np.sum(np.isfinite(bikes_now) & (bikes_now > capacity_now))
        )

        for horizon in horizons:
            target = slot + pd.Timedelta(minutes=horizon)
            if target in bikes.index:
                actual_bikes = bikes.loc[target].to_numpy(dtype=float)
                actual_capacity = capacity.loc[target].to_numpy(dtype=float)
            else:
                actual_bikes = np.full(len(station_ids), np.nan)
                actual_capacity = np.full(len(station_ids), np.nan)
            delta = predicted_delta(slot, horizon, station_ids, groups, globals_)
            expected_bikes = np.clip(bikes_now + delta, 0.0, capacity_now)
            expected_docks = np.maximum(capacity_now - expected_bikes, 0.0)

            for origin_anchor, destination in destination_anchor.items():
                request_id = (
                    f"{slot.isoformat()}|{station_ids[origin_anchor]}|"
                    f"{station_ids[destination]}|{horizon}"
                )
                request_digest.update((request_id + "\n").encode())
                request_count += 1

                origin_indices = nearby[origin_anchor]
                destination_indices = nearby[destination]
                origin_indices = origin_indices[valid_now[origin_indices]]
                destination_indices = destination_indices[
                    valid_now[destination_indices]
                ]
                if not len(origin_indices) or not len(destination_indices):
                    excluded_no_route += 1
                    continue

                origin_distance = (
                    distance_km[origin_anchor, origin_indices] * DETOUR_FACTOR * 1000.0
                )
                destination_distance = (
                    distance_km[destination, destination_indices]
                    * DETOUR_FACTOR
                    * 1000.0
                )
                origin_scores = score_station(
                    origin_distance, expected_bikes[origin_indices]
                )
                destination_scores = score_station(
                    destination_distance, expected_docks[destination_indices]
                )
                origin_order = np.lexsort(
                    (
                        np.array(station_ids)[origin_indices],
                        origin_distance,
                        -expected_bikes[origin_indices],
                        -origin_scores,
                    )
                )[:3]
                top_origins = origin_indices[origin_order]

                routes = []
                for oi in top_origins:
                    for position, di in enumerate(destination_indices):
                        if oi == di:
                            continue
                        bike_m = distance_km[oi, di] * DETOUR_FACTOR * 1000.0
                        walk_origin_min = math.ceil(
                            distance_km[origin_anchor, oi] * DETOUR_FACTOR / 4.0 * 60.0
                        )
                        walk_destination_min = math.ceil(
                            distance_km[destination, di] * DETOUR_FACTOR / 4.0 * 60.0
                        )
                        bike_min = math.ceil(bike_m / 1000.0 / 15.0 * 60.0)
                        total_eta = walk_origin_min + bike_min + walk_destination_min
                        route_score = (
                            0.35 * origin_scores[np.where(origin_indices == oi)[0][0]]
                            + 0.35 * destination_scores[position]
                            + 0.15 * inverse_score(total_eta, 90.0)
                            + 0.15
                            * inverse_score(
                                walk_origin_min + walk_destination_min, 20.0
                            )
                        )
                        routes.append(
                            (
                                route_score,
                                total_eta,
                                walk_origin_min + walk_destination_min,
                                oi,
                                di,
                            )
                        )
                routes.sort(
                    key=lambda item: (
                        -item[0],
                        item[1],
                        item[2],
                        station_ids[item[3]],
                        station_ids[item[4]],
                    )
                )
                routes = routes[:3]
                if len(routes) < 3:
                    candidate_shortage += 1
                evaluable = []
                for _, _, _, oi, di in routes:
                    if not (
                        np.isfinite(actual_bikes[oi])
                        and np.isfinite(actual_capacity[oi])
                        and np.isfinite(actual_bikes[di])
                        and np.isfinite(actual_capacity[di])
                    ):
                        continue
                    future_over_capacity += int(actual_bikes[oi] > actual_capacity[oi])
                    future_over_capacity += int(actual_bikes[di] > actual_capacity[di])
                    evaluable.append((oi, di))
                if not evaluable:
                    excluded_no_actual += 1
                    continue

                for threshold in (1, 2):
                    origin_success = any(
                        actual_bikes[oi] >= threshold for oi, _ in evaluable
                    )
                    destination_success = any(
                        max(actual_capacity[di] - actual_bikes[di], 0.0) >= threshold
                        for _, di in evaluable
                    )
                    simultaneous = any(
                        actual_bikes[oi] >= threshold
                        and max(actual_capacity[di] - actual_bikes[di], 0.0)
                        >= threshold
                        for oi, di in evaluable
                    )
                    result_rows.append(
                        {
                            "request_id": request_id,
                            "base_time_kst": slot,
                            "horizon_min": horizon,
                            "threshold": threshold,
                            "returned_routes": len(routes),
                            "evaluable_routes": len(evaluable),
                            "origin_success": origin_success,
                            "destination_success": destination_success,
                            "simultaneous_success": simultaneous,
                        }
                    )

    results = pd.DataFrame(result_rows)
    summary = results.groupby(["horizon_min", "threshold"], as_index=False).agg(
        eligible_requests=("request_id", "nunique"),
        origin_success_rate=("origin_success", "mean"),
        destination_success_rate=("destination_success", "mean"),
        simultaneous_success_rate=("simultaneous_success", "mean"),
        mean_returned_routes=("returned_routes", "mean"),
        mean_evaluable_routes=("evaluable_routes", "mean"),
    )
    micro = (
        results.groupby("threshold", as_index=False)
        .agg(
            eligible_requests=("request_id", "nunique"),
            origin_success_rate=("origin_success", "mean"),
            destination_success_rate=("destination_success", "mean"),
            simultaneous_success_rate=("simultaneous_success", "mean"),
            mean_returned_routes=("returned_routes", "mean"),
            mean_evaluable_routes=("evaluable_routes", "mean"),
        )
        .assign(horizon_min="ALL")
    )
    summary = pd.concat([summary, micro], ignore_index=True)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output_dir / "route_pair_metrics.csv", index=False)
    results.to_parquet(
        args.output_dir / "route_pair_request_results.parquet", index=False
    )
    metadata = {
        "status": "provisional_diagnostic",
        "reason": "minimum 90-day pre-test history requirement is not met",
        "snapshot_sha256": sha256(args.snapshots),
        "station_master_sha256": sha256(args.stations),
        "request_set_sha256": request_digest.hexdigest(),
        "source_timezone": "UTC",
        "evaluation_timezone": KST,
        "test_start_kst": test_start.isoformat(),
        "test_end_exclusive_kst": test_end.isoformat(),
        "test_complete_dates": [str(value) for value in test_dates],
        "test_days": len(test_dates),
        "observed_pretest_days": observed_days,
        "required_pretest_days": minimum_history_days,
        "station_count": len(station_ids),
        "request_count": request_count,
        "eligible_request_count": int(results["request_id"].nunique()),
        "excluded_no_base": excluded_no_base,
        "excluded_no_route": excluded_no_route,
        "excluded_no_actual": excluded_no_actual,
        "candidate_shortage_requests": candidate_shortage,
        "base_rows_over_capacity_seen": base_over_capacity,
        "future_route_endpoint_rows_over_capacity_seen": future_over_capacity,
        "prediction_policy": "pre-test B3 station-weekday-time mean; station mean; B1 zero",
        "request_pair_policy": "sorted station IDs paired by half-list circular offset",
        "future_over_capacity_policy": "raw bikes retained; empty docks floored at zero",
    }
    (args.output_dir / "route_pair_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
