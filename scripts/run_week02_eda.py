from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


DATA_ROOT = Path("/Users/jiyoonmoon/Desktop/창학 4-2/ddareungi_data")
TRIP = DATA_ROOT / "processed" / "trip" / "trip_agg_15m.parquet"

REPORT_DIR = Path("reports/week02")
FIG_DIR = Path("reports/figures")

REPORT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)


print("=" * 80)
print("LOAD DATA")
print("=" * 80)

df = pd.read_parquet(TRIP)

df = df.loc[df["is_observed"]].copy()

print("Observed rows:", f"{len(df):,}")
print("Stations:", df["station_id"].nunique())
print("Period:", df["base_time"].min(), "->", df["base_time"].max())


# -------------------------------------------------------------------
# Overall summary
# -------------------------------------------------------------------

summary = pd.DataFrame(
    {
        "metric": [
            "rows",
            "stations",
            "rent_total",
            "return_total",
            "delta_mean",
            "delta_std",
            "delta_zero_rate",
        ],
        "value": [
            len(df),
            df["station_id"].nunique(),
            df["rent_count"].sum(),
            df["return_count"].sum(),
            df["delta_hist"].mean(),
            df["delta_hist"].std(),
            (df["delta_hist"] == 0).mean(),
        ],
    }
)

summary.to_csv(
    REPORT_DIR / "eda_overall_summary.csv",
    index=False,
)


# -------------------------------------------------------------------
# Hourly
# -------------------------------------------------------------------

hourly = (
    df.groupby("hour")
    .agg(
        rent_mean=("rent_count", "mean"),
        return_mean=("return_count", "mean"),
        abs_delta_mean=("delta_hist", lambda s: s.abs().mean()),
        zero_delta_rate=("delta_hist", lambda s: (s == 0).mean()),
        rows=("station_id", "size"),
    )
    .reset_index()
)

hourly.to_csv(
    REPORT_DIR / "eda_hourly.csv",
    index=False,
)

plt.figure(figsize=(10, 5))
plt.plot(hourly["hour"], hourly["rent_mean"], marker="o", label="Rent")
plt.plot(hourly["hour"], hourly["return_mean"], marker="o", label="Return")
plt.xlabel("Hour")
plt.ylabel("Mean count per 15-min station bin")
plt.title("Hourly Rental and Return Activity")
plt.legend()
plt.tight_layout()
plt.savefig(
    FIG_DIR / "hourly_rent_return.png",
    dpi=160,
)
plt.close()


# -------------------------------------------------------------------
# Weekday
# -------------------------------------------------------------------

weekday_order = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

weekday = (
    df.groupby("weekday")
    .agg(
        rent_mean=("rent_count", "mean"),
        return_mean=("return_count", "mean"),
        abs_delta_mean=("delta_hist", lambda s: s.abs().mean()),
    )
    .reindex(weekday_order)
    .reset_index()
)

weekday.to_csv(
    REPORT_DIR / "eda_weekday.csv",
    index=False,
)

plt.figure(figsize=(10, 5))
plt.plot(
    weekday["weekday"],
    weekday["rent_mean"],
    marker="o",
    label="Rent",
)
plt.plot(
    weekday["weekday"],
    weekday["return_mean"],
    marker="o",
    label="Return",
)
plt.xticks(rotation=30)
plt.ylabel("Mean count per 15-min station bin")
plt.title("Rental and Return Activity by Weekday")
plt.legend()
plt.tight_layout()
plt.savefig(
    FIG_DIR / "weekday_rent_return.png",
    dpi=160,
)
plt.close()


# -------------------------------------------------------------------
# District
# -------------------------------------------------------------------

district = (
    df.groupby("district")
    .agg(
        rows=("station_id", "size"),
        stations=("station_id", "nunique"),
        rent_total=("rent_count", "sum"),
        return_total=("return_count", "sum"),
        rent_mean=("rent_count", "mean"),
        return_mean=("return_count", "mean"),
        abs_delta_mean=("delta_hist", lambda s: s.abs().mean()),
        zero_delta_rate=("delta_hist", lambda s: (s == 0).mean()),
    )
    .reset_index()
)

district.to_csv(
    REPORT_DIR / "eda_district.csv",
    index=False,
)


# -------------------------------------------------------------------
# Peak vs non-peak
# -------------------------------------------------------------------

peak = (
    df.groupby("is_peak")
    .agg(
        rows=("station_id", "size"),
        rent_mean=("rent_count", "mean"),
        return_mean=("return_count", "mean"),
        abs_delta_mean=("delta_hist", lambda s: s.abs().mean()),
        zero_delta_rate=("delta_hist", lambda s: (s == 0).mean()),
    )
    .reset_index()
)

peak.to_csv(
    REPORT_DIR / "eda_peak.csv",
    index=False,
)


# -------------------------------------------------------------------
# Station activity
# -------------------------------------------------------------------

station = (
    df.groupby(
        ["station_id", "station_name", "district"],
        observed=True,
    )
    .agg(
        observed_bins=("base_time", "size"),
        rent_total=("rent_count", "sum"),
        return_total=("return_count", "sum"),
        nonzero_delta_bins=("delta_hist", lambda s: (s != 0).sum()),
        abs_delta_mean=("delta_hist", lambda s: s.abs().mean()),
    )
    .reset_index()
)

station["total_activity"] = (
    station["rent_total"]
    + station["return_total"]
)

station["nonzero_delta_rate"] = (
    station["nonzero_delta_bins"]
    / station["observed_bins"]
)

station = station.sort_values(
    "total_activity",
    ascending=False,
)

station.to_csv(
    REPORT_DIR / "eda_station_activity.csv",
    index=False,
    encoding="utf-8-sig",
)

plt.figure(figsize=(10, 5))
plt.hist(
    station["total_activity"],
    bins=40,
)
plt.xlabel("Total rental + return count")
plt.ylabel("Number of stations")
plt.title("Station Activity Distribution")
plt.tight_layout()
plt.savefig(
    FIG_DIR / "station_activity_distribution.png",
    dpi=160,
)
plt.close()


# -------------------------------------------------------------------
# delta_hist
# -------------------------------------------------------------------

delta_counts = (
    df["delta_hist"]
    .value_counts()
    .sort_index()
    .rename_axis("delta_hist")
    .reset_index(name="count")
)

delta_counts["proportion"] = (
    delta_counts["count"]
    / delta_counts["count"].sum()
)

delta_counts.to_csv(
    REPORT_DIR / "eda_delta_hist_distribution.csv",
    index=False,
)

plot_delta = df.loc[
    df["delta_hist"].between(-10, 10),
    "delta_hist",
]

plt.figure(figsize=(10, 5))
plt.hist(
    plot_delta,
    bins=21,
)
plt.xlabel("delta_hist (returns - rentals)")
plt.ylabel("15-min station bins")
plt.title("Distribution of 15-Minute Net Inventory Change")
plt.tight_layout()
plt.savefig(
    FIG_DIR / "delta_hist_distribution.png",
    dpi=160,
)
plt.close()


# -------------------------------------------------------------------
# Monthly activity
# -------------------------------------------------------------------

df["month"] = df["base_time"].dt.to_period("M").astype(str)

monthly = (
    df.groupby("month")
    .agg(
        stations=("station_id", "nunique"),
        rent_total=("rent_count", "sum"),
        return_total=("return_count", "sum"),
        zero_delta_rate=("delta_hist", lambda s: (s == 0).mean()),
    )
    .reset_index()
)

monthly.to_csv(
    REPORT_DIR / "eda_monthly.csv",
    index=False,
)


# -------------------------------------------------------------------
# Console summary
# -------------------------------------------------------------------

print()
print("=" * 80)
print("EDA SUMMARY")
print("=" * 80)

print()
print("[Overall]")
print(summary.to_string(index=False))

print()
print("[District]")
print(district.to_string(index=False))

print()
print("[Peak]")
print(peak.to_string(index=False))

print()
print("[Top 15 stations by activity]")
print(
    station[
        [
            "station_id",
            "station_name",
            "district",
            "total_activity",
            "nonzero_delta_rate",
        ]
    ]
    .head(15)
    .to_string(index=False)
)

print()
print("[Monthly]")
print(monthly.to_string(index=False))

print()
print("Figures:", FIG_DIR)
print("Tables :", REPORT_DIR)
