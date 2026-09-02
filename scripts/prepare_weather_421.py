from pathlib import Path

import pandas as pd

INPUT = Path(
    "/Users/jiyoonmoon/Desktop/창학 4-2/ddareungi_data/"
    "raw/weather/aws421/aws421_202508_202607.csv"
)

OUTPUT = Path(
    "/Users/jiyoonmoon/Desktop/창학 4-2/ddareungi_data/"
    "processed/weather/weather_421_normalized.parquet"
)

REPORT = Path("reports/week02/weather_421_missingness.csv")


def read_source(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(
                path,
                encoding=encoding,
                low_memory=False,
            )
        except UnicodeDecodeError:
            continue

    raise RuntimeError("Unable to decode AWS source")


df = read_source(INPUT)

required = {
    "지점",
    "일시",
    "기온(°C)",
    "강수량(mm)",
    "풍속(m/s)",
    "습도(%)",
}

missing_cols = required - set(df.columns)

if missing_cols:
    raise ValueError(f"Missing required columns: {sorted(missing_cols)}")

weather = pd.DataFrame(
    {
        "weather_station_id": pd.to_numeric(df["지점"], errors="coerce"),
        "weather_obs_time": pd.to_datetime(df["일시"], errors="coerce"),
        "temp_c": pd.to_numeric(df["기온(°C)"], errors="coerce"),
        "precip_mm": pd.to_numeric(df["강수량(mm)"], errors="coerce"),
        "wind_ms": pd.to_numeric(df["풍속(m/s)"], errors="coerce"),
        "humidity_pct": pd.to_numeric(df["습도(%)"], errors="coerce"),
    }
)

weather = weather.loc[weather["weather_station_id"].eq(421)].copy()

weather = weather.loc[
    weather["weather_obs_time"].between(
        "2025-08-01 00:00:00",
        "2026-07-31 23:59:59",
    )
].copy()

weather = weather.dropna(subset=["weather_obs_time"])

weather = weather.sort_values("weather_obs_time").drop_duplicates(
    subset=["weather_obs_time"],
    keep="last",
)

weather["weather_obs_time"] = weather["weather_obs_time"].dt.tz_localize("Asia/Seoul")

# Preserve missingness explicitly.
for col in (
    "temp_c",
    "precip_mm",
    "wind_ms",
    "humidity_pct",
):
    weather[f"{col}_missing"] = weather[col].isna()

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
REPORT.parent.mkdir(parents=True, exist_ok=True)

weather.to_parquet(
    OUTPUT,
    index=False,
)

report = pd.DataFrame(
    {
        "field": [
            "temp_c",
            "precip_mm",
            "wind_ms",
            "humidity_pct",
        ],
        "missing_count": [
            weather["temp_c"].isna().sum(),
            weather["precip_mm"].isna().sum(),
            weather["wind_ms"].isna().sum(),
            weather["humidity_pct"].isna().sum(),
        ],
    }
)

report["missing_rate"] = report["missing_count"] / len(weather)

report.to_csv(
    REPORT,
    index=False,
)

print("=" * 80)
print("AWS 421 NORMALIZATION")
print("=" * 80)

print("rows:", f"{len(weather):,}")
print("start:", weather["weather_obs_time"].min())
print("end:", weather["weather_obs_time"].max())
print("duplicates:", int(weather["weather_obs_time"].duplicated().sum()))

print()
print(report.to_string(index=False))

print()
print("Output:", OUTPUT)
