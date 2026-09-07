from __future__ import annotations

import numpy as np
import pandas as pd


def make_week02_panel(
    *,
    days: int = 2,
    stations: tuple[str, ...] = ("A",),
    activity_scales: tuple[int, ...] | None = None,
    missing_dates: tuple[str, ...] = (),
) -> pd.DataFrame:
    periods = days * 96
    times = pd.date_range("2026-01-01", periods=periods, freq="15min")
    missing = {pd.Timestamp(value).normalize() for value in missing_dates}
    scales = activity_scales or tuple(1 for _ in stations)
    rows: list[pd.DataFrame] = []

    for station, scale in zip(stations, scales, strict=True):
        position = np.arange(periods)
        observed = ~times.normalize().isin(missing)
        rent = pd.Series((position % 5) * scale, dtype="Float64")
        returns = pd.Series(((position + 1) % 4) * scale, dtype="Float64")
        rent.loc[~observed] = pd.NA
        returns.loc[~observed] = pd.NA
        delta = returns - rent
        minute_of_day = times.hour * 60 + times.minute

        station_frame = pd.DataFrame(
            {
                "station_id": station,
                "station_name": f"Station {station}",
                "district": "광진구" if station == stations[0] else "성동구",
                "base_time": times,
                "date": times.normalize(),
                "weekday": times.day_name(),
                "is_weekend": times.weekday >= 5,
                "is_holiday": False,
                "is_peak": ((minute_of_day >= 7 * 60) & (minute_of_day < 9 * 60))
                | ((minute_of_day >= 18 * 60) & (minute_of_day < 20 * 60)),
                "rent_count": rent,
                "return_count": returns,
                "delta_hist": delta,
                "source_day_observed": observed,
                "is_observed": observed,
                "weather_station_id": 421,
                "weather_obs_time": times.floor("h").tz_localize("Asia/Seoul"),
                "temp_c": 20.0,
                "precip_mm": 0.0,
                "humidity_pct": 50.0,
                "wind_ms": 1.5,
                "weather_age_min": times.minute.astype(float),
                "weather_available": True,
            }
        )
        rows.append(station_frame)

    frame = pd.concat(rows, ignore_index=True)
    frame = frame.sort_values(["station_id", "base_time"]).reset_index(drop=True)
    grouped = frame.groupby("station_id", sort=False)

    for horizon in (15, 30, 60):
        steps = horizon // 15
        components = [grouped["delta_hist"].shift(-offset) for offset in range(steps)]
        observations = [
            grouped["is_observed"].shift(-offset).fillna(False).astype(bool)
            for offset in range(steps)
        ]
        timestamps = [
            grouped["base_time"].shift(-offset) for offset in range(steps)
        ]

        valid = pd.Series(True, index=frame.index)
        for offset, (observed, timestamp) in enumerate(
            zip(observations, timestamps, strict=True)
        ):
            valid &= observed
            valid &= timestamp.eq(
                frame["base_time"] + pd.Timedelta(minutes=offset * 15)
            )

        target = pd.concat(components, axis=1).sum(axis=1, min_count=steps)
        frame[f"target_h{horizon}_valid"] = valid
        frame[f"delta_hist_h{horizon}"] = target.where(valid)

    return frame
