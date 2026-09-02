from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jiyoonmoon/Desktop/창학 4-2/ddareungi_data")

TRIP = ROOT / "processed/trip/trip_targets_15_30_60.parquet"

WEATHER = ROOT / "processed/weather/weather_421_normalized.parquet"

OUTPUT = ROOT / "processed/trip/" "trip_targets_weather_15_30_60.parquet"

REPORT = Path("reports/week02/weather_join_summary.csv")


trip = pd.read_parquet(TRIP)
weather = pd.read_parquet(WEATHER)

trip["base_time_kst"] = pd.to_datetime(trip["base_time"]).dt.tz_localize("Asia/Seoul")

# Weather mapping only once per timestamp, not once per station.
base_times = trip[["base_time_kst"]].drop_duplicates().sort_values("base_time_kst")

weather = weather.sort_values("weather_obs_time")

mapping = pd.merge_asof(
    base_times,
    weather,
    left_on="base_time_kst",
    right_on="weather_obs_time",
    direction="backward",
    tolerance=pd.Timedelta(minutes=60),
)

mapping["weather_age_min"] = (
    mapping["base_time_kst"] - mapping["weather_obs_time"]
).dt.total_seconds() / 60

mapping["weather_available"] = mapping["weather_obs_time"].notna()

trip = trip.merge(
    mapping,
    how="left",
    on="base_time_kst",
    validate="many_to_one",
)

month = trip["base_time_kst"].dt.month

season_map = {
    12: "winter",
    1: "winter",
    2: "winter",
    3: "spring",
    4: "spring",
    5: "spring",
    6: "summer",
    7: "summer",
    8: "summer",
    9: "autumn",
    10: "autumn",
    11: "autumn",
}

trip["season"] = month.map(season_map)

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

trip.to_parquet(
    OUTPUT,
    index=False,
)

summary = pd.DataFrame(
    {
        "metric": [
            "rows",
            "weather_available_rows",
            "weather_unavailable_rows",
            "temp_missing_rate",
            "precip_missing_rate",
            "wind_missing_rate",
            "humidity_missing_rate",
        ],
        "value": [
            len(trip),
            int(trip["weather_available"].sum()),
            int((~trip["weather_available"]).sum()),
            float(trip["temp_c"].isna().mean()),
            float(trip["precip_mm"].isna().mean()),
            float(trip["wind_ms"].isna().mean()),
            float(trip["humidity_pct"].isna().mean()),
        ],
    }
)

REPORT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

summary.to_csv(
    REPORT,
    index=False,
)

print("=" * 80)
print("WEATHER JOIN SUMMARY")
print("=" * 80)

print(summary.to_string(index=False))

print()
print("Weather age:")
print(
    trip.loc[
        trip["weather_available"],
        "weather_age_min",
    ].describe()
)

print()
print("Output:", OUTPUT)
