from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path


EXPECTED = {
    "trip": Path("interim/trip"),
    "weather": Path("raw/weather"),
    "calendar": Path("processed/calendar"),
    "reference": Path("reference"),
}


def human_size(size: int) -> str:
    value = float(size)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} PB"


def count_csv_rows(path: Path) -> tuple[int | None, list[str], list[list[str]]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            sample_text = f.read(8192)
            f.seek(0)

            try:
                dialect = csv.Sniffer().sniff(sample_text)
            except csv.Error:
                dialect = csv.excel

            reader = csv.reader(f, dialect)
            header = next(reader, [])
            samples = []
            count = 0

            for row in reader:
                count += 1
                if len(samples) < 3:
                    samples.append(row)

            return count, header, samples

    except UnicodeDecodeError:
        return None, [], []


def inspect_file(path: Path) -> None:
    print(f"\nFILE: {path}")
    print(f"SIZE: {human_size(path.stat().st_size)}")

    suffix = path.suffix.lower()

    if suffix in {".csv", ".txt", ".tsv"}:
        rows, header, samples = count_csv_rows(path)

        if rows is not None:
            print(f"ROWS: {rows:,}")
            print(f"COLUMNS ({len(header)}):")
            for col in header:
                print(f"  - {col}")

            if samples:
                print("SAMPLE VALUES:")
                for row in samples[:2]:
                    print("  ", row[: min(len(row), 12)])
        else:
            print("NOTE: text encoding could not be read as UTF-8.")

    elif suffix in {".parquet", ".pq"}:
        print("NOTE: Parquet detected.")
        print("Run pandas/pyarrow inspection after dependencies are available.")

    elif suffix in {".xlsx", ".xls"}:
        print("NOTE: Excel file detected.")
        print("Inspect with pandas/openpyxl during Week 02 data profiling.")

    else:
        print("NOTE: unsupported/other format; listed only.")


def find_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(p for p in path.rglob("*") if p.is_file())


def keyword_check(name: str, columns: list[str]) -> None:
    lowered = [c.lower() for c in columns]

    groups = {
        "station candidates": ["station", "대여소", "station_id", "rent_station", "return_station"],
        "time candidates": ["time", "date", "timestamp", "대여일시", "반납일시"],
        "district candidates": ["district", "자치구", "구명"],
    }

    print(f"\nCOLUMN HINTS: {name}")

    for label, words in groups.items():
        matches = [
            col for col in columns
            if any(word in col.lower() for word in words)
        ]
        print(f"  {label}: {matches}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-root",
        required=True,
        help="Path containing ddareungi_data structure",
    )
    args = parser.parse_args()

    root = Path(os.path.expanduser(args.data_root)).resolve()

    print("=" * 70)
    print("WEEK 02 DATA INTAKE AUDIT")
    print("=" * 70)
    print("ROOT:", root)

    if not root.exists():
        raise SystemExit(f"ERROR: data root does not exist: {root}")

    all_columns = {}

    for name, relative in EXPECTED.items():
        path = root / relative

        print("\n" + "=" * 70)
        print(f"{name.upper()} :: {path}")
        print("=" * 70)

        if not path.exists():
            print("MISSING")
            continue

        files = find_files(path)

        if not files:
            print("EMPTY DIRECTORY")
            continue

        print(f"FILES: {len(files)}")

        for file in files:
            inspect_file(file)

            if file.suffix.lower() == ".csv":
                _, header, _ = count_csv_rows(file)
                if header:
                    all_columns[str(file)] = header

    print("\n" + "=" * 70)
    print("COLUMN CANDIDATE CHECK")
    print("=" * 70)

    for name, cols in all_columns.items():
        keyword_check(name, cols)

    print("\n" + "=" * 70)
    print("MANUAL CHECKS STILL REQUIRED")
    print("=" * 70)
    print("1. Confirm trip data source and period.")
    print("2. Confirm trip-level vs pre-aggregated format.")
    print("3. Confirm rental and return station identifiers.")
    print("4. Confirm rental and return timestamps/timezone.")
    print("5. Confirm Gwangjin/Seongdong filtering provenance.")
    print("6. Confirm weather network: AWS 421 vs ASOS.")
    print("7. Confirm calendar source and date coverage.")
    print("8. Confirm preprocessing/filtering scripts.")
    print("=" * 70)


if __name__ == "__main__":
    main()
