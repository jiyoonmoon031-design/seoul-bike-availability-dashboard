from pathlib import Path

import pandas as pd


DATA_ROOT = Path("/Users/jiyoonmoon/Desktop/창학 4-2/ddareungi_data")
PATH = DATA_ROOT / "processed" / "trip" / "trip_agg_15m.parquet"

df = pd.read_parquet(PATH)

print("=" * 80)
print("TRIP_AGG QA")
print("=" * 80)

print("rows:", f"{len(df):,}")
print("stations:", df["station_id"].nunique())
print("start:", df["base_time"].min())
print("end:", df["base_time"].max())

print()
print("districts:")
print(df["district"].value_counts())

print()
print("source_day_observed:")
print(df["source_day_observed"].value_counts())

print()
print("is_observed:")
print(df["is_observed"].value_counts())

# ------------------------------------------------------------------
# 15 minute alignment
# ------------------------------------------------------------------

bad_alignment = (
    (df["base_time"].dt.minute % 15 != 0)
    | (df["base_time"].dt.second != 0)
).sum()

print()
print("bad 15-min alignment:", int(bad_alignment))

# ------------------------------------------------------------------
# Required null rules
# ------------------------------------------------------------------

obs = df["is_observed"]
unobs = ~obs

observed_nulls = df.loc[
    obs,
    ["rent_count", "return_count", "delta_hist"],
].isna().any(axis=1).sum()

unobserved_nonnull = df.loc[
    unobs,
    ["rent_count", "return_count", "delta_hist"],
].notna().any(axis=1).sum()

print("observed rows with null counts:", int(observed_nulls))
print(
    "unobserved rows containing counts:",
    int(unobserved_nonnull),
)

# ------------------------------------------------------------------
# Delta identity
# ------------------------------------------------------------------

calc_delta = (
    df.loc[obs, "return_count"].astype("int64")
    - df.loc[obs, "rent_count"].astype("int64")
)

delta_errors = (
    calc_delta
    != df.loc[obs, "delta_hist"].astype("int64")
).sum()

print("delta_hist identity errors:", int(delta_errors))

# ------------------------------------------------------------------
# Negative counts
# ------------------------------------------------------------------

negative_rent = (
    df.loc[obs, "rent_count"] < 0
).sum()

negative_return = (
    df.loc[obs, "return_count"] < 0
).sum()

print("negative rent counts:", int(negative_rent))
print("negative return counts:", int(negative_return))

# ------------------------------------------------------------------
# Duplicate unit
# ------------------------------------------------------------------

duplicates = df.duplicated(
    subset=["station_id", "base_time"]
).sum()

print("duplicate station_id/base_time:", int(duplicates))

# ------------------------------------------------------------------
# Missing source dates
# ------------------------------------------------------------------

missing_dates = (
    df.loc[~df["source_day_observed"], "date"]
    .drop_duplicates()
    .sort_values()
)

print()
print("missing source dates:")

for d in missing_dates:
    print(" ", pd.Timestamp(d).date())

# ------------------------------------------------------------------
# Activity
# ------------------------------------------------------------------

observed_df = df.loc[obs].copy()

print()
print("rent_count summary:")
print(observed_df["rent_count"].describe())

print()
print("return_count summary:")
print(observed_df["return_count"].describe())

print()
print("delta_hist summary:")
print(observed_df["delta_hist"].describe())

print()
print(
    "zero delta proportion:",
    float((observed_df["delta_hist"] == 0).mean()),
)

# ------------------------------------------------------------------
# Hard assertions
# ------------------------------------------------------------------

assert bad_alignment == 0
assert observed_nulls == 0
assert unobserved_nonnull == 0
assert delta_errors == 0
assert negative_rent == 0
assert negative_return == 0
assert duplicates == 0

print()
print("=" * 80)
print("PASS: trip_agg structural QA")
print("=" * 80)
