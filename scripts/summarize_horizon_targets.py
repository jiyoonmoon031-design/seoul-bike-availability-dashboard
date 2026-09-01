from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

DATA_ROOT = Path("/Users/jiyoonmoon/Desktop/창학 4-2/ddareungi_data")

INPUT = DATA_ROOT / "processed" / "trip" / "trip_targets_15_30_60.parquet"

REPORT_DIR = Path("reports/week02")
FIG_DIR = Path("reports/figures")

REPORT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(INPUT)

rows = []

for h in [15, 30, 60]:
    valid_col = f"target_h{h}_valid"
    target_col = f"delta_hist_h{h}"

    valid = df[valid_col]
    target = df.loc[valid, target_col]

    rows.append(
        {
            "horizon_min": h,
            "valid_rows": int(valid.sum()),
            "invalid_rows": int((~valid).sum()),
            "zero_rate": float((target == 0).mean()),
            "mean": float(target.mean()),
            "std": float(target.std()),
            "min": float(target.min()),
            "max": float(target.max()),
        }
    )

summary = pd.DataFrame(rows)

summary.to_csv(
    REPORT_DIR / "horizon_target_summary.csv",
    index=False,
)

plt.figure(figsize=(7, 4))
plt.plot(
    summary["horizon_min"],
    summary["zero_rate"],
    marker="o",
)
plt.xlabel("Prediction horizon (min)")
plt.ylabel("Zero-target proportion")
plt.title("Target Sparsity by Prediction Horizon")
plt.xticks([15, 30, 60])
plt.tight_layout()
plt.savefig(
    FIG_DIR / "target_sparsity_by_horizon.png",
    dpi=160,
)
plt.close()

print(summary.to_string(index=False))
print()
print("Saved:")
print(REPORT_DIR / "horizon_target_summary.csv")
print(FIG_DIR / "target_sparsity_by_horizon.png")
