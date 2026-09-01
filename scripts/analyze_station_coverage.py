from pathlib import Path

import pandas as pd


DATA_ROOT = Path("/Users/jiyoonmoon/Desktop/창학 4-2/ddareungi_data")

coverage_path = (
    DATA_ROOT
    / "processed"
    / "trip"
    / "station_history_coverage.csv"
)

out_dir = Path("reports/week02")
out_dir.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(
    coverage_path,
    encoding="utf-8-sig",
    dtype={"station_id": "string"},
)

df["first_seen"] = pd.to_datetime(df["first_seen"], errors="coerce")
df["last_seen"] = pd.to_datetime(df["last_seen"], errors="coerce")

never_seen = df.loc[~df["has_history"].astype(bool)].copy()
seen = df.loc[df["has_history"].astype(bool)].copy()

never_seen.to_csv(
    out_dir / "stations_never_seen_in_history.csv",
    index=False,
    encoding="utf-8-sig",
)

seen.to_csv(
    out_dir / "stations_with_history.csv",
    index=False,
    encoding="utf-8-sig",
)

summary = (
    df.groupby("district")
    .agg(
        target_stations=("station_id", "count"),
        historical_stations=("has_history", "sum"),
    )
)

summary["never_seen"] = (
    summary["target_stations"]
    - summary["historical_stations"]
)

summary["history_coverage_rate"] = (
    summary["historical_stations"]
    / summary["target_stations"]
)

print("=" * 80)
print("STATION COVERAGE")
print("=" * 80)

print(summary)

print()
print("Never seen:", len(never_seen))

print(
    never_seen[
        ["station_id", "station_name", "district"]
    ]
    .sort_values(["district", "station_id"])
    .to_string(index=False)
)

print()
print("First-seen distribution:")
print(seen["first_seen"].dt.to_period("M").value_counts().sort_index())

print()
print("Last-seen distribution:")
print(seen["last_seen"].dt.to_period("M").value_counts().sort_index())

print()
print("Artifacts:")
print(out_dir / "stations_never_seen_in_history.csv")
print(out_dir / "stations_with_history.csv")
