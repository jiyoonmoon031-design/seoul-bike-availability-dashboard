from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ENCODINGS = ("utf-8-sig", "utf-8", "cp949", "euc-kr")


def read_sample(path: Path, nrows: int = 5):
    last_error = None

    for enc in ENCODINGS:
        try:
            df = pd.read_csv(path, encoding=enc, nrows=nrows)
            return df, enc
        except UnicodeDecodeError as exc:
            last_error = exc
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"Cannot read {path}: {last_error}")


def inspect_dir(label: str, path: Path):
    print("\n" + "=" * 80)
    print(label)
    print(path)
    print("=" * 80)

    if not path.exists():
        print("MISSING")
        return

    files = sorted(p for p in path.rglob("*") if p.is_file())

    print("FILE COUNT:", len(files))

    for p in files:
        size_mb = p.stat().st_size / 1024 / 1024
        print(f"\nFILE: {p.name}")
        print(f"SIZE: {size_mb:.2f} MB")

        if p.suffix.lower() == ".csv":
            try:
                df, enc = read_sample(p)
                print("ENCODING:", enc)
                print("COLUMNS:")
                for c in df.columns:
                    print("  -", repr(c))

                print("SAMPLE:")
                print(df.head(3).to_string(index=False))

            except Exception as e:
                print("READ ERROR:", e)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True)
    args = parser.parse_args()

    root = Path(args.data_root).expanduser().resolve()

    print("DATA ROOT:", root)

    targets = {
        "RAW TRIP": root / "raw" / "trip",
        "INTERIM TRIP": root / "interim" / "trip",
        "RAW WEATHER": root / "raw" / "weather",
        "CALENDAR": root / "processed" / "calendar",
        "REFERENCE": root / "reference",
    }

    for label, path in targets.items():
        inspect_dir(label, path)


if __name__ == "__main__":
    main()
