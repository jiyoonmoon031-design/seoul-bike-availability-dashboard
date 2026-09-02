from pathlib import Path

import pandas as pd

ROOT = Path("/Users/jiyoonmoon/Desktop/창학 4-2/ddareungi_data 2")

ENCODINGS = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]


def read_csv(path):
    last = None
    for enc in ENCODINGS:
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False), enc
        except Exception as exc:
            last = exc
    raise RuntimeError(f"{path}: {last}")


def choose_column(columns, preferred, keyword):
    if preferred in columns:
        return preferred

    candidates = [c for c in columns if keyword in str(c) and "QC" not in str(c)]

    return candidates[0] if candidates else None


files = sorted((ROOT / "raw" / "weather").glob("*.csv"))

if not files:
    raise SystemExit(f"No CSV files found under: {ROOT}")

print("=" * 80)
print("AWS 421 WEATHER AUDIT")
print("=" * 80)

valid_files = []

for path in files:
    df, enc = read_csv(path)

    print()
    print("FILE:", path)
    print("ENCODING:", enc)
    print("ROWS:", f"{len(df):,}")
    print("COLUMNS:")
    for c in df.columns:
        print(" -", c)

    station_col = "지점" if "지점" in df.columns else None
    time_col = "일시" if "일시" in df.columns else None

    temp_col = choose_column(df.columns, "기온(°C)", "기온")
    rain_col = choose_column(df.columns, "강수량(mm)", "강수량")
    wind_col = choose_column(df.columns, "풍속(m/s)", "풍속")
    humid_col = choose_column(df.columns, "습도(%)", "습도")

    print()
    print("Detected:")
    print(" station :", station_col)
    print(" time    :", time_col)
    print(" temp    :", temp_col)
    print(" precip  :", rain_col)
    print(" wind    :", wind_col)
    print(" humidity:", humid_col)

    if station_col is None or time_col is None:
        print("FAIL: required station/time columns not detected")
        continue

    stations = (
        pd.to_numeric(df[station_col], errors="coerce")
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    ts = pd.to_datetime(df[time_col], errors="coerce")

    print("station IDs:", sorted(stations))
    print("start:", ts.min())
    print("end  :", ts.max())
    print("invalid timestamps:", int(ts.isna().sum()))

    unique_ts = ts.dropna().drop_duplicates().sort_values()

    if len(unique_ts) > 1:
        cadence = (
            unique_ts.diff().dropna().dt.total_seconds().div(60).value_counts().head(10)
        )

        print()
        print("cadence minutes:")
        print(cadence.to_string())

    print()
    print("missing values:")

    selected = [c for c in [temp_col, rain_col, wind_col, humid_col] if c is not None]

    if selected:
        print(df[selected].isna().sum().to_string())

    station_ok = stations == [421] or set(stations) == {421}

    period_ok = ts.min() <= pd.Timestamp("2025-08-01") and ts.max() >= pd.Timestamp(
        "2026-07-31"
    )

    vars_ok = all(c is not None for c in [temp_col, rain_col, wind_col, humid_col])

    print()
    print("station 421:", "PASS" if station_ok else "FAIL")
    print("period     :", "PASS" if period_ok else "FAIL")
    print("variables  :", "PASS" if vars_ok else "FAIL")

    if station_ok and period_ok and vars_ok:
        valid_files.append(path)


print()
print("=" * 80)
print("FINAL")
print("=" * 80)

if len(valid_files) != 1:
    print("Valid AWS 421 files:", len(valid_files))

    for p in valid_files:
        print(p)

    raise SystemExit("Need exactly one validated AWS 421 source file.")

print("PASS: AWS 421 source validated")
print("FILE:", valid_files[0])
