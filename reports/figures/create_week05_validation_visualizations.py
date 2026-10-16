"""Create local Week 05 validation figures from committed summary artifacts."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
METRICS = ROOT / "reports/week05/final_model_metrics.csv"
IMPORTANCE = ROOT / "reports/week05/feature_importance.csv"
OUTPUT = ROOT / "reports/figures"


def configure_style() -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "figure.dpi": 140,
            "savefig.dpi": 180,
            "axes.titleweight": "bold",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.family": "sans-serif",
            "font.sans-serif": ["AppleGothic", "Arial", "DejaVu Sans"],
            "axes.unicode_minus": False,
        }
    )


def plot_mae_vs_baseline(metrics: pd.DataFrame) -> None:
    all_rows = metrics.loc[metrics["segment"].eq("ALL")].sort_values("horizon_min")
    horizons = all_rows["horizon_min"].astype(int).astype(str) + "m"
    x = np.arange(len(all_rows))
    width = 0.34

    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    model_bars = ax.bar(
        x - width / 2,
        all_rows["mae"],
        width,
        label="Final Random Forest",
        color="#2563EB",
    )
    baseline_bars = ax.bar(
        x + width / 2,
        all_rows["b1_mae_same_rows"],
        width,
        label="B1 persistence",
        color="#94A3B8",
    )
    ax.set_title("Week 05 Final-test MAE vs B1 (ALL)")
    ax.set_xlabel("Forecast horizon")
    ax.set_ylabel("MAE (bikes)")
    ax.set_xticks(x, horizons)
    ax.legend(frameon=False)
    ax.bar_label(model_bars, fmt="%.3f", padding=3, fontsize=9)
    ax.bar_label(baseline_bars, fmt="%.3f", padding=3, fontsize=9)
    maximum = max(
        all_rows["mae"].max(),
        all_rows["b1_mae_same_rows"].max(),
    )
    ax.set_ylim(0, maximum * 1.22)
    fig.tight_layout()
    fig.savefig(OUTPUT / "week05_horizon_mae_vs_b1.png", bbox_inches="tight")
    plt.close(fig)


def plot_improvement_heatmap(metrics: pd.DataFrame) -> None:
    segment_order = ["ALL", "ACTIVE", "PEAK", "ACTIVE_PEAK"]
    pivot = (
        metrics.pivot(
            index="segment",
            columns="horizon_min",
            values="improvement_vs_b1",
        )
        .reindex(segment_order)
        .reindex(columns=[15, 30, 60])
        * 100
    )

    fig, ax = plt.subplots(figsize=(7.8, 4.8))
    vmax = float(np.abs(pivot.to_numpy()).max())
    image = ax.imshow(pivot, cmap="RdYlBu", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_title("Improvement over B1 by Segment and Horizon")
    ax.set_xlabel("Forecast horizon")
    ax.set_ylabel("Segment")
    ax.set_xticks(range(3), ["15m", "30m", "60m"])
    ax.set_yticks(range(4), ["ALL", "ACTIVE", "PEAK", "ACTIVE ∩ PEAK"])
    for row in range(pivot.shape[0]):
        for col in range(pivot.shape[1]):
            value = pivot.iloc[row, col]
            ax.text(
                col,
                row,
                f"{value:+.1f}%",
                ha="center",
                va="center",
                color="white" if abs(value) > vmax * 0.55 else "#0F172A",
                fontweight="bold",
            )
    colorbar = fig.colorbar(image, ax=ax, shrink=0.82)
    colorbar.set_label("MAE improvement vs B1 (%)")
    fig.tight_layout()
    fig.savefig(OUTPUT / "week05_baseline_improvement_heatmap.png", bbox_inches="tight")
    plt.close(fig)


def plot_feature_importance(importance: pd.DataFrame) -> None:
    value_column = next(
        column
        for column in (
            "permutation_mae_increase",
            "native_importance",
            "permutation_importance",
            "gain_importance",
            "importance",
        )
        if column in importance.columns
    )
    feature_column = "feature" if "feature" in importance.columns else "feature_name"
    top = importance.nlargest(15, value_column).sort_values(value_column)

    fig, ax = plt.subplots(figsize=(9.2, 6.2))
    bars = ax.barh(top[feature_column], top[value_column], color="#0F766E")
    ax.set_title(f"Top 15 Features ({value_column.replace('_', ' ').title()})")
    ax.set_xlabel(value_column.replace("_", " ").title())
    ax.set_ylabel("")
    ax.bar_label(bars, fmt="%.3f", padding=3, fontsize=8)
    ax.set_xlim(0, float(top[value_column].max()) * 1.18)
    fig.tight_layout()
    fig.savefig(OUTPUT / "week05_feature_importance_top15.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    configure_style()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    metrics = pd.read_csv(METRICS)
    importance = pd.read_csv(IMPORTANCE)
    plot_mae_vs_baseline(metrics)
    plot_improvement_heatmap(metrics)
    plot_feature_importance(importance)


if __name__ == "__main__":
    main()
