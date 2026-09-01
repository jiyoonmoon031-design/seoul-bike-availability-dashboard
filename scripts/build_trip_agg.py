from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

DATE_COL = "기준_날짜"
TIME_COL = "기준_시간대"
MODE_COL = "집계_기준"
RENT_STATION_COL = "시작_대여소_ID"
RETURN_STATION_COL = "종료_대여소_ID"
COUNT_COL = "전체_건수"

EXPECTED_START = pd.Timestamp("2025-08-01")
EXPECTED_END = pd.Timestamp("2026-07-31")


def normalize_station_id(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)


def normalize_hhmm(value) -> str | None:
    if pd.isna(value):
        return None

    s = str(value).strip()

    if ":" in s:
        parts = s.split(":")
        try:
            hour = int(parts[0])
            minute = int(parts[1])
        except (ValueError, IndexError):
            return None
    else:
        digits = re.sub(r"\D", "", s)

        if not digits:
            return None

        digits = digits.zfill(4)[-4:]

        try:
            hour = int(digits[:2])
            minute = int(digits[2:])
        except ValueError:
            return None

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    if minute % 5 != 0:
        return None

    return f"{hour:02d}:{minute:02d}"


def build_timestamp(df: pd.DataFrame) -> pd.Series:
    date_str = (
        df[DATE_COL].astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    )

    time_str = df[TIME_COL].map(normalize_hhmm)

    return pd.to_datetime(
        date_str + " " + time_str.astype("string"),
        format="%Y%m%d %H:%M",
        errors="coerce",
    )


def process_file(path: Path, mode: str):
    if mode == "rent":
        station_col = RENT_STATION_COL
        expected_mode = "출발시간"
        value_col = "rent_count"
    else:
        station_col = RETURN_STATION_COL
        expected_mode = "도착시간"
        value_col = "return_count"

    usecols = [
        DATE_COL,
        MODE_COL,
        TIME_COL,
        station_col,
        COUNT_COL,
    ]

    df = pd.read_csv(
        path,
        encoding="utf-8-sig",
        usecols=usecols,
        dtype={
            DATE_COL: "string",
            TIME_COL: "string",
            station_col: "string",
        },
        low_memory=False,
    )

    modes = set(df[MODE_COL].dropna().astype(str).str.strip().unique())

    if modes != {expected_mode}:
        raise ValueError(
            f"{path.name}: expected {expected_mode}, found {sorted(modes)}"
        )

    df["station_id"] = normalize_station_id(df[station_col])
    df["timestamp"] = build_timestamp(df)

    df[value_col] = pd.to_numeric(
        df[COUNT_COL],
        errors="coerce",
    )

    invalid = (
        df["station_id"].isna()
        | df["timestamp"].isna()
        | df[value_col].isna()
        | (df[value_col] < 0)
    )

    if invalid.any():
        raise ValueError(f"{path.name}: invalid rows={int(invalid.sum())}")

    # Source coverage is determined at date level.
    source_dates = set(df["timestamp"].dt.normalize().unique())

    # [t, t+15) base aggregation.
    df["base_time"] = df["timestamp"].dt.floor("15min")

    agg = df.groupby(
        ["station_id", "base_time"],
        observed=True,
        as_index=False,
    )[value_col].sum()

    return agg, source_dates


def load_target_stations(path: Path) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        encoding="utf-8-sig",
        dtype={"station_id": "string"},
    )

    required = {"station_id", "station_name", "district"}

    missing = required - set(df.columns)

    if missing:
        raise ValueError(f"target station file missing columns: {sorted(missing)}")

    df["station_id"] = normalize_station_id(df["station_id"])

    if df["station_id"].duplicated().any():
        raise ValueError("Duplicate station_id in target_stations.csv")

    invalid_district = ~df["district"].isin(["광진구", "성동구"])

    if invalid_district.any():
        raise ValueError(
            "target_stations.csv contains districts outside " "Gwangjin/Seongdong"
        )

    return df


def load_calendar(path: Path) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        encoding="utf-8-sig",
    )

    required = {
        "date",
        "weekday",
        "is_weekend",
        "is_holiday",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(f"calendar missing columns: {sorted(missing)}")

    df["date"] = pd.to_datetime(
        df["date"],
        errors="raise",
    ).dt.normalize()

    return df


def build_station_coverage(
    rent: pd.DataFrame,
    returns: pd.DataFrame,
    target: pd.DataFrame,
) -> pd.DataFrame:

    seen = pd.concat(
        [
            rent[["station_id", "base_time"]],
            returns[["station_id", "base_time"]],
        ],
        ignore_index=True,
    )

    coverage = seen.groupby("station_id", as_index=False).agg(
        first_seen=("base_time", "min"),
        last_seen=("base_time", "max"),
        observed_bins=("base_time", "nunique"),
    )

    coverage = target.merge(
        coverage,
        how="left",
        on="station_id",
    )

    coverage["has_history"] = coverage["first_seen"].notna()

    return coverage


def build_panel(
    rent: pd.DataFrame,
    returns: pd.DataFrame,
    target: pd.DataFrame,
    coverage: pd.DataFrame,
    calendar: pd.DataFrame,
    complete_source_dates: set[pd.Timestamp],
) -> pd.DataFrame:

    rent_idx = rent.set_index(["station_id", "base_time"])["rent_count"]
    return_idx = returns.set_index(["station_id", "base_time"])["return_count"]

    target_lookup = target.set_index("station_id")[["station_name", "district"]]

    pieces = []

    history_stations = coverage.loc[coverage["has_history"]].copy()

    all_dates = pd.date_range(
        EXPECTED_START,
        EXPECTED_END,
        freq="D",
    )

    for date in all_dates:
        times = pd.date_range(
            date,
            date + pd.Timedelta(hours=23, minutes=45),
            freq="15min",
        )

        active = history_stations[
            (history_stations["first_seen"] <= times[-1])
            & (history_stations["last_seen"] >= times[0])
        ]

        if active.empty:
            continue

        idx = pd.MultiIndex.from_product(
            [active["station_id"].tolist(), times],
            names=["station_id", "base_time"],
        )

        day = pd.DataFrame(index=idx).reset_index()

        bounds = active[["station_id", "first_seen", "last_seen"]]

        day = day.merge(
            bounds,
            on="station_id",
            how="left",
            validate="many_to_one",
        )

        day = day[
            (day["base_time"] >= day["first_seen"])
            & (day["base_time"] <= day["last_seen"])
        ].copy()

        day = day.drop(columns=["first_seen", "last_seen"])

        source_day_observed = date.normalize() in complete_source_dates

        day["source_day_observed"] = source_day_observed

        if source_day_observed:
            keys = pd.MultiIndex.from_frame(day[["station_id", "base_time"]])

            day["rent_count"] = rent_idx.reindex(keys).fillna(0).to_numpy()

            day["return_count"] = return_idx.reindex(keys).fillna(0).to_numpy()

            day["rent_count"] = day["rent_count"].astype("int32")
            day["return_count"] = day["return_count"].astype("int32")

            day["delta_hist"] = (day["return_count"] - day["rent_count"]).astype(
                "int32"
            )

            day["is_observed"] = True

        else:
            # Source date itself is absent.
            # Do NOT interpret this as zero activity.
            day["rent_count"] = pd.NA
            day["return_count"] = pd.NA
            day["delta_hist"] = pd.NA
            day["is_observed"] = False

        pieces.append(day)

    panel = pd.concat(
        pieces,
        ignore_index=True,
    )

    panel = panel.join(
        target_lookup,
        on="station_id",
    )

    panel["date"] = panel["base_time"].dt.normalize()

    panel = panel.merge(
        calendar,
        how="left",
        on="date",
        validate="many_to_one",
    )

    panel["hour"] = panel["base_time"].dt.hour.astype("int8")
    panel["minute"] = panel["base_time"].dt.minute.astype("int8")

    minutes_from_midnight = panel["hour"].astype("int16") * 60 + panel["minute"].astype(
        "int16"
    )

    panel["is_peak"] = (
        (minutes_from_midnight >= 7 * 60) & (minutes_from_midnight < 9 * 60)
    ) | ((minutes_from_midnight >= 18 * 60) & (minutes_from_midnight < 20 * 60))

    panel = panel[
        [
            "station_id",
            "station_name",
            "district",
            "base_time",
            "date",
            "hour",
            "minute",
            "weekday",
            "is_weekend",
            "is_holiday",
            "is_peak",
            "rent_count",
            "return_count",
            "delta_hist",
            "source_day_observed",
            "is_observed",
        ]
    ]

    return panel


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--target-stations", required=True)
    parser.add_argument("--calendar", required=True)
    parser.add_argument("--output-dir", required=True)

    args = parser.parse_args()

    input_dir = Path(args.input_dir).expanduser().resolve()
    target_path = Path(args.target_stations).expanduser().resolve()
    calendar_path = Path(args.calendar).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    rent_files = sorted(input_dir.glob("rent_*.csv"))
    return_files = sorted(input_dir.glob("return_*.csv"))

    if len(rent_files) != 12 or len(return_files) != 12:
        raise SystemExit(
            f"Expected 12 rent + 12 return files; "
            f"found {len(rent_files)} + {len(return_files)}"
        )

    print("=" * 80)
    print("STEP 1 - AGGREGATE SOURCE FILES")
    print("=" * 80)

    rent_parts = []
    return_parts = []

    rent_dates = set()
    return_dates = set()

    for path in rent_files:
        print("Processing:", path.name)
        part, dates = process_file(path, "rent")
        rent_parts.append(part)
        rent_dates.update(dates)

    for path in return_files:
        print("Processing:", path.name)
        part, dates = process_file(path, "return")
        return_parts.append(part)
        return_dates.update(dates)

    rent = pd.concat(rent_parts, ignore_index=True)
    returns = pd.concat(return_parts, ignore_index=True)

    # Guard against accidental overlap or repeated input files.
    rent = rent.groupby(
        ["station_id", "base_time"],
        as_index=False,
    )["rent_count"].sum()

    returns = returns.groupby(
        ["station_id", "base_time"],
        as_index=False,
    )["return_count"].sum()

    print()
    print("Rent aggregated rows:", f"{len(rent):,}")
    print("Return aggregated rows:", f"{len(returns):,}")

    target = load_target_stations(target_path)
    calendar = load_calendar(calendar_path)

    complete_source_dates = {
        pd.Timestamp(x).normalize() for x in rent_dates.intersection(return_dates)
    }

    expected_dates = set(
        pd.date_range(
            EXPECTED_START,
            EXPECTED_END,
            freq="D",
        )
    )

    missing_source_dates = sorted(expected_dates - complete_source_dates)

    print()
    print("=" * 80)
    print("STEP 2 - SOURCE COVERAGE")
    print("=" * 80)

    print("Target stations:", len(target))
    print("Complete source dates:", len(complete_source_dates))
    print("Missing source dates:", len(missing_source_dates))

    for d in missing_source_dates:
        print("  MISSING:", d.date())

    coverage = build_station_coverage(
        rent,
        returns,
        target,
    )

    print()
    print(
        "Stations with historical observations:",
        int(coverage["has_history"].sum()),
    )

    print(
        "Target stations never seen in history:",
        int((~coverage["has_history"]).sum()),
    )

    print()
    print("History by district:")
    print(coverage.groupby("district")["has_history"].agg(["count", "sum"]))

    print()
    print("=" * 80)
    print("STEP 3 - BUILD 15-MIN PANEL")
    print("=" * 80)

    panel = build_panel(
        rent,
        returns,
        target,
        coverage,
        calendar,
        complete_source_dates,
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    parquet_path = output_dir / "trip_agg_15m.parquet"
    coverage_path = output_dir / "station_history_coverage.csv"
    missing_path = output_dir / "missing_source_dates.csv"

    try:
        panel.to_parquet(
            parquet_path,
            index=False,
        )
    except ImportError:
        raise SystemExit(
            "Parquet support requires pyarrow.\n"
            "Install with: python3 -m pip install pyarrow"
        )

    coverage.to_csv(
        coverage_path,
        index=False,
        encoding="utf-8-sig",
    )

    pd.DataFrame({"date": missing_source_dates}).to_csv(
        missing_path,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print("=" * 80)
    print("TRIP_AGG BUILD COMPLETE")
    print("=" * 80)

    print("Output:", parquet_path)
    print("Rows:", f"{len(panel):,}")
    print("Stations:", panel["station_id"].nunique())
    print("Start:", panel["base_time"].min())
    print("End:", panel["base_time"].max())

    print(
        "Observed rows:",
        f"{int(panel['is_observed'].sum()):,}",
    )

    print(
        "Unobserved rows:",
        f"{int((~panel['is_observed']).sum()):,}",
    )

    observed = panel[panel["is_observed"]]

    print()
    print("Observed delta_hist:")
    print(observed["delta_hist"].describe())

    print()
    print("Zero-delta proportion:")
    print((observed["delta_hist"] == 0).mean())

    print()
    print("Artifacts:")
    print(" ", parquet_path)
    print(" ", coverage_path)
    print(" ", missing_path)


if __name__ == "__main__":
    main()
