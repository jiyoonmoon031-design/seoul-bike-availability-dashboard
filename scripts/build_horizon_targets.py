from pathlib import Path

import pandas as pd

DATA_ROOT = Path("/Users/jiyoonmoon/Desktop/창학 4-2/ddareungi_data")

INPUT = DATA_ROOT / "processed" / "trip" / "trip_agg_15m.parquet"

OUTPUT = DATA_ROOT / "processed" / "trip" / "trip_targets_15_30_60.parquet"


df = pd.read_parquet(INPUT)

df = df.sort_values(["station_id", "base_time"]).reset_index(drop=True)

g = df.groupby(
    "station_id",
    sort=False,
    group_keys=False,
)


# ----------------------------------------------------------
# Forward target components
# ----------------------------------------------------------

for k in range(4):
    df[f"delta_t{k}"] = g["delta_hist"].shift(-k)
    df[f"obs_t{k}"] = g["is_observed"].shift(-k)
    df[f"time_t{k}"] = g["base_time"].shift(-k)


# ----------------------------------------------------------
# Continuity checks
# ----------------------------------------------------------

continuous_15 = df["time_t0"].notna() & df["obs_t0"].fillna(False)

continuous_30 = (
    continuous_15
    & df["obs_t1"].fillna(False)
    & (df["time_t1"] - df["time_t0"] == pd.Timedelta(minutes=15))
)

continuous_60 = (
    continuous_30
    & df["obs_t2"].fillna(False)
    & df["obs_t3"].fillna(False)
    & (df["time_t2"] - df["time_t1"] == pd.Timedelta(minutes=15))
    & (df["time_t3"] - df["time_t2"] == pd.Timedelta(minutes=15))
)


# ----------------------------------------------------------
# Targets
# ----------------------------------------------------------

df["delta_hist_h15"] = df["delta_t0"].where(continuous_15)

df["delta_hist_h30"] = (df["delta_t0"] + df["delta_t1"]).where(continuous_30)

df["delta_hist_h60"] = (
    df["delta_t0"] + df["delta_t1"] + df["delta_t2"] + df["delta_t3"]
).where(continuous_60)


# ----------------------------------------------------------
# Validity flags
# ----------------------------------------------------------

df["target_h15_valid"] = continuous_15
df["target_h30_valid"] = continuous_30
df["target_h60_valid"] = continuous_60


# ----------------------------------------------------------
# Remove temporary columns
# ----------------------------------------------------------

temp_cols = []

for k in range(4):
    temp_cols.extend(
        [
            f"delta_t{k}",
            f"obs_t{k}",
            f"time_t{k}",
        ]
    )

df = df.drop(columns=temp_cols)


# ----------------------------------------------------------
# Save
# ----------------------------------------------------------

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

df.to_parquet(
    OUTPUT,
    index=False,
)


# ----------------------------------------------------------
# Summary
# ----------------------------------------------------------

print("=" * 80)
print("HORIZON TARGET SUMMARY")
print("=" * 80)

for h in [15, 30, 60]:

    valid = df[f"target_h{h}_valid"]

    target = df.loc[
        valid,
        f"delta_hist_h{h}",
    ]

    print()
    print(f"Horizon {h} min")
    print("valid rows:", f"{valid.sum():,}")
    print("missing rows:", f"{(~valid).sum():,}")
    print("zero rate:", float((target == 0).mean()))
    print("mean:", float(target.mean()))
    print("std:", float(target.std()))
    print("min:", float(target.min()))
    print("max:", float(target.max()))

print()
print("Output:", OUTPUT)
