from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _format_horizon(value: object) -> str:
    if pd.isna(value):
        return "ALL micro"
    return f"{int(value)} min"


def render_hit_rate_svg(metrics: pd.DataFrame, output: Path) -> None:
    horizon = metrics[metrics["scope"].eq("horizon")].copy()
    horizon = horizon.sort_values(
        ["availability_threshold", "mode", "horizon_min"]
    )
    labels = [
        f"{row.mode} {int(row.horizon_min)}m T≥{int(row.availability_threshold)}"
        for row in horizon.itertuples()
    ]
    rates = horizon["hit_rate"].astype(float).tolist()
    width = 900
    left = 210
    plot_width = 620
    row_height = 34
    height = 90 + row_height * len(labels)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#172554}.label{font-size:13px}.value{font-size:12px;font-weight:bold}.title{font-size:20px;font-weight:bold}</style>',
        '<text x="20" y="30" class="title">Week 09 Top-3 availability hit rate</text>',
        f'<line x1="{left + plot_width * 0.9:.1f}" y1="50" x2="{left + plot_width * 0.9:.1f}" y2="{height - 20}" stroke="#dc2626" stroke-dasharray="5 4"/>',
        f'<text x="{left + plot_width * 0.9 + 5:.1f}" y="62" class="value" fill="#dc2626">target 0.90</text>',
    ]
    for index, (label, rate) in enumerate(zip(labels, rates)):
        y = 78 + index * row_height
        bar_width = max(0.0, min(rate, 1.0)) * plot_width
        color = "#0f766e" if rate >= 0.90 else "#f59e0b"
        parts.extend(
            [
                f'<text x="20" y="{y + 15}" class="label">{label}</text>',
                f'<rect x="{left}" y="{y}" width="{plot_width}" height="20" rx="4" fill="#e2e8f0"/>',
                f'<rect x="{left}" y="{y}" width="{bar_width:.1f}" height="20" rx="4" fill="{color}"/>',
                f'<text x="{left + min(bar_width + 6, plot_width - 35):.1f}" y="{y + 15}" class="value">{rate:.1%}</text>',
            ]
        )
    parts.append("</svg>")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(parts) + "\n", encoding="utf-8")


def build_markdown_report(
    metrics: pd.DataFrame,
    metadata: dict,
    *,
    figure_path: str,
) -> str:
    rows = metrics.sort_values(
        ["availability_threshold", "mode", "scope", "horizon_min"],
        na_position="last",
    )
    table = [
        "| Scope | Mode | Threshold | Requests | Hits | Hit rate | Target |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for row in rows.itertuples():
        target = "Pass" if float(row.hit_rate) >= 0.90 else "Below target"
        table.append(
            "| "
            + " | ".join(
                [
                    _format_horizon(row.horizon_min),
                    str(row.mode),
                    f"≥{int(row.availability_threshold)}",
                    str(int(row.eligible_requests)),
                    str(int(row.hits)),
                    f"{float(row.hit_rate):.2%}",
                    target,
                ]
            )
            + " |"
        )

    return "\n".join(
        [
            "# Week 09 Hold-out Recommendation Validation",
            "",
            "Related issue: #43",
            "",
            "## Evaluation identity",
            "",
            f"- Input SHA-256: `{metadata['input_sha256']}`",
            f"- Candidate rows: {metadata['candidate_rows']:,}",
            f"- Eligible requests: {metadata['eligible_requests']:,}",
            "- Horizons: 15, 30, and 60 minutes",
            "- Modes: rent and return",
            "- Provisional Top-3 target: 0.90",
            "",
            "## Quantitative results",
            "",
            *table,
            "",
            f"![Top-3 hit-rate chart]({figure_path})",
            "",
            "## Interpretation rules",
            "",
            "- Rent uses actual bikes at the target time.",
            "- Return uses actual empty docks at the target time.",
            "- Threshold 1 measures minimum availability.",
            "- Threshold 2 measures stable availability.",
            "- Values below 0.90 are reported without changing the preregistered target.",
            "",
            "## Limitations",
            "",
            "The result applies only to the frozen request set and hold-out snapshot coverage identified by the input checksum. Missing target-time snapshots must be excluded and reported before this document is treated as final.",
            "",
        ]
    )


def write_report(
    metrics_path: Path,
    metadata_path: Path,
    report_path: Path,
    figure_path: Path,
) -> None:
    metrics = pd.read_csv(metrics_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    render_hit_rate_svg(metrics, figure_path)
    relative_figure = figure_path.relative_to(report_path.parent).as_posix()
    report_path.write_text(
        build_markdown_report(
            metrics,
            metadata,
            figure_path=relative_figure,
        ),
        encoding="utf-8",
    )

