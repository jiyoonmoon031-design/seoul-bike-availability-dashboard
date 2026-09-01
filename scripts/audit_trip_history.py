from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

DATA_ROOT = Path("/Users/jiyoonmoon/Desktop/창학 4-2/ddareungi_data")
TRIP_DIR = DATA_ROOT / "interim" / "trip"
TARGET_FILE = DATA_ROOT / "reference" / "target_stations.csv"

DATE_COL = "기준_날짜"
TIME_COL = "기준_시간대"
MODE_COL = "집계_기준"
RENT_STATION = "시작_대여소_ID"
RETURN_STATION = "종료_대여소_ID"
COUNT_COL = "전체_건수"


def norm_station(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)


def normalize_hhmm(value):
    if pd.isna(value):
        return None

    s = str(value).strip()

    if ":" in s:
        parts = s.split(":")
        try:
            h = int(parts[0])
            m = int(parts[1])
        except Exception:
            return None
    else:
        digits = re.sub(r"\D", "", s)
        if not digits:
            return None

        digits = digits.zfill(4)[-4:]

        try:
            h = int(digits[:2])
            m = int(digits[2:])
        except Exception:
            return None

    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None

    return h, m


targets = pd.read_csv(TARGET_FILE, encoding="utf-8-sig")
targets["station_id"] = norm_station(targets["station_id"])
target_ids = set(targets["station_id"].dropna())

print("=" * 80)
print("TARGET STATIONS")
print("=" * 80)
print("rows:", len(targets))
print("unique station_id:", targets["station_id"].nunique())
print("district counts:")
print(targets["district"].value_counts(dropna=False))
print()

results = []

for path in sorted(TRIP_DIR.glob("*.csv")):
    df = pd.read_csv(
        path,
        encoding="utf-8-sig",
        low_memory=False,
        dtype={
            DATE_COL: "string",
            RENT_STATION: "string",
            RETURN_STATION: "string",
        },
    )

    mode = "rent" if path.name.startswith("rent_") else "return"
    expected_mode = "출발시간" if mode == "rent" else "도착시간"
    station_col = RENT_STATION if mode == "rent" else RETURN_STATION

    df[station_col] = norm_station(df[station_col])

    dates = pd.to_datetime(
        df[DATE_COL].astype(str),
        format="%Y%m%d",
        errors="coerce",
    )

    parsed_time = df[TIME_COL].map(normalize_hhmm)

    invalid_time = parsed_time.isna().sum()

    non_5min = sum(x is not None and x[1] % 5 != 0 for x in parsed_time)

    count_numeric = pd.to_numeric(
        df[COUNT_COL],
        errors="coerce",
    )

    invalid_count = count_numeric.isna().sum()
    negative_count = (count_numeric < 0).sum()

    mode_values = sorted(
        df[MODE_COL].dropna().astype(str).str.strip().unique().tolist()
    )

    station_ids = set(df[station_col].dropna())
    outside_target = station_ids - target_ids

    valid_dates = dates.dropna()
    unique_dates = sorted(valid_dates.dt.normalize().unique())

    month_start = valid_dates.min().replace(day=1)
    month_end = month_start + pd.offsets.MonthEnd(1)

    expected_dates = pd.date_range(
        month_start,
        month_end,
        freq="D",
    )

    observed_dates = pd.DatetimeIndex(unique_dates)
    missing_dates = expected_dates.difference(observed_dates)

    exact_dupes = int(df.duplicated().sum())

    print("=" * 80)
    print(path.name)
    print("=" * 80)
    print("rows:", f"{len(df):,}")
    print("mode values:", mode_values)
    print("date:", valid_dates.min(), "->", valid_dates.max())
    print("unique dates:", len(observed_dates))
    print("missing calendar dates:", len(missing_dates))

    if len(missing_dates):
        print("MISSING:", ", ".join(d.strftime("%Y-%m-%d") for d in missing_dates))

    print("unique target-side stations:", len(station_ids))
    print("outside target station IDs:", len(outside_target))

    if outside_target:
        print("examples:", sorted(outside_target)[:20])

    print("invalid timestamp date:", int(dates.isna().sum()))
    print("invalid HHMM:", int(invalid_time))
    print("non-5-minute HHMM:", int(non_5min))
    print("invalid count:", int(invalid_count))
    print("negative count:", int(negative_count))
    print("exact duplicate rows:", exact_dupes)

    if mode_values != [expected_mode]:
        print(f"WARNING: expected mode={expected_mode}, " f"actual={mode_values}")

    results.append(
        {
            "file": path.name,
            "mode": mode,
            "rows": len(df),
            "date_min": valid_dates.min(),
            "date_max": valid_dates.max(),
            "unique_dates": len(observed_dates),
            "missing_dates": len(missing_dates),
            "missing_date_list": ",".join(
                d.strftime("%Y-%m-%d") for d in missing_dates
            ),
            "unique_stations": len(station_ids),
            "outside_target_stations": len(outside_target),
            "invalid_time": int(invalid_time),
            "non_5min": int(non_5min),
            "invalid_count": int(invalid_count),
            "negative_count": int(negative_count),
            "exact_duplicates": exact_dupes,
        }
    )


report = pd.DataFrame(results)

out = Path("/tmp/week02_trip_audit.csv")
report.to_csv(out, index=False, encoding="utf-8-sig")

print()
print("=" * 80)
print("FINAL SUMMARY")
print("=" * 80)

print(report.to_string(index=False))

print()
print("Total source rows:", f"{report['rows'].sum():,}")
print(
    "Files with missing dates:",
    int((report["missing_dates"] > 0).sum()),
)
print(
    "Files with off-target stations:",
    int((report["outside_target_stations"] > 0).sum()),
)
print(
    "Files with non-5-minute times:",
    int((report["non_5min"] > 0).sum()),
)
print(
    "Files with invalid counts:",
    int((report["invalid_count"] > 0).sum()),
)

print()
print("Report:", out)
