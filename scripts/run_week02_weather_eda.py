from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path("/Users/jiyoonmoon/Desktop/창학 4-2/ddareungi_data")

INPUT = ROOT / "processed/trip/" "trip_targets_weather_15_30_60.parquet"

REPORT = Path("reports/week02")
FIG = Path("reports/figures")

REPORT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)


df = pd.read_parquet(INPUT)

df = df.loc[df["is_observed"]].copy()

# Aggregate across stations before weather analysis so each
# timestamp is not artificially weighted by station count.
system = df.groupby(
    "base_time_kst",
    as_index=False,
).agg(
    rent_total=("rent_count", "sum"),
    return_total=("return_count", "sum"),
    temp_c=("temp_c", "first"),
    precip_mm=("precip_mm", "first"),
    humidity_pct=("humidity_pct", "first"),
    wind_ms=("wind_ms", "first"),
    season=("season", "first"),
    is_holiday=("is_holiday", "first"),
    weather_available=("weather_available", "first"),
)

system["total_activity"] = system["rent_total"] + system["return_total"]


season = (
    system.groupby("season")
    .agg(
        intervals=("base_time_kst", "size"),
        rent_mean=("rent_total", "mean"),
        return_mean=("return_total", "mean"),
        activity_mean=("total_activity", "mean"),
    )
    .reset_index()
)

season.to_csv(
    REPORT / "eda_season.csv",
    index=False,
)


holiday = (
    system.groupby("is_holiday")
    .agg(
        intervals=("base_time_kst", "size"),
        rent_mean=("rent_total", "mean"),
        return_mean=("return_total", "mean"),
        activity_mean=("total_activity", "mean"),
    )
    .reset_index()
)

holiday.to_csv(
    REPORT / "eda_holiday.csv",
    index=False,
)


temp_df = system.loc[system["temp_c"].notna()].copy()

temp_df["temp_bin"] = pd.qcut(
    temp_df["temp_c"],
    4,
    duplicates="drop",
)

temp = (
    temp_df.groupby(
        "temp_bin",
        observed=True,
    )
    .agg(
        intervals=("base_time_kst", "size"),
        temp_mean=("temp_c", "mean"),
        activity_mean=("total_activity", "mean"),
    )
    .reset_index()
)

temp["temp_bin"] = temp["temp_bin"].astype(str)

temp.to_csv(
    REPORT / "eda_temperature.csv",
    index=False,
)


rain = system.loc[system["precip_mm"].notna()].copy()

rain["rain_flag"] = rain["precip_mm"] > 0

rain_summary = (
    rain.groupby("rain_flag")
    .agg(
        intervals=("base_time_kst", "size"),
        activity_mean=("total_activity", "mean"),
        precip_mean=("precip_mm", "mean"),
    )
    .reset_index()
)

rain_summary.to_csv(
    REPORT / "eda_precipitation.csv",
    index=False,
)


corr = system[
    [
        "total_activity",
        "temp_c",
        "precip_mm",
        "humidity_pct",
        "wind_ms",
    ]
].corr(method="spearman")

corr.to_csv(REPORT / "eda_weather_spearman.csv")


# Figures
plt.figure(figsize=(7, 4))
plt.bar(
    season["season"],
    season["activity_mean"],
)
plt.xlabel("Season")
plt.ylabel("Mean activity per 15 min")
plt.title("Seasonal Bike Activity")
plt.tight_layout()
plt.savefig(
    FIG / "season_activity.png",
    dpi=160,
)
plt.close()


plt.figure(figsize=(6, 4))
plt.bar(
    holiday["is_holiday"].astype(str),
    holiday["activity_mean"],
)
plt.xlabel("Holiday")
plt.ylabel("Mean activity per 15 min")
plt.title("Holiday vs Non-Holiday Activity")
plt.tight_layout()
plt.savefig(
    FIG / "holiday_activity.png",
    dpi=160,
)
plt.close()


plt.figure(figsize=(8, 4))
plt.plot(
    temp["temp_bin"],
    temp["activity_mean"],
    marker="o",
)
plt.xticks(rotation=20)
plt.xlabel("Temperature quartile")
plt.ylabel("Mean activity per 15 min")
plt.title("Bike Activity by Temperature")
plt.tight_layout()
plt.savefig(
    FIG / "temperature_activity.png",
    dpi=160,
)
plt.close()


if len(rain_summary) > 1:
    plt.figure(figsize=(6, 4))
    plt.bar(
        rain_summary["rain_flag"].astype(str),
        rain_summary["activity_mean"],
    )
    plt.xlabel("Rain")
    plt.ylabel("Mean activity per 15 min")
    plt.title("Rain vs Dry Bike Activity")
    plt.tight_layout()
    plt.savefig(
        FIG / "precipitation_activity.png",
        dpi=160,
    )
    plt.close()


print("=" * 80)
print("WEEK 02 WEATHER / CALENDAR EDA")
print("=" * 80)

print()
print("[Season]")
print(season.to_string(index=False))

print()
print("[Holiday]")
print(holiday.to_string(index=False))

print()
print("[Temperature]")
print(temp.to_string(index=False))

print()
print("[Precipitation]")
print(rain_summary.to_string(index=False))

print()
print("[Spearman correlations]")
print(corr.to_string())

print()
print("Tables :", REPORT)
print("Figures:", FIG)
