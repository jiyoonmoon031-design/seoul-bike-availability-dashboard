from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = {
    "request_id",
    "base_time",
    "origin_station_id",
    "horizon_min",
    "mode",
    "candidate_station_id",
    "rank",
    "actual_bikes",
    "capacity",
}

MODE_ALIASES = {
    "origin": "rent",
    "rent": "rent",
    "destination": "return",
    "return": "return",
}


@dataclass(frozen=True)
class RecommendationEvaluation:
    request_results: pd.DataFrame
    metrics: pd.DataFrame
    metadata: dict[str, Any]


def _validate_and_normalize(rows: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(REQUIRED_COLUMNS - set(rows.columns))
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")

    frame = rows.copy()
    frame["mode"] = frame["mode"].map(MODE_ALIASES)
    if frame["mode"].isna().any():
        raise ValueError("mode must be one of origin, destination, rent, return")

    numeric_columns = [
        "horizon_min",
        "rank",
        "actual_bikes",
        "capacity",
    ]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    if frame[numeric_columns].isna().any().any():
        raise ValueError("numeric evaluation columns must be finite numbers")
    if not frame["horizon_min"].isin([15, 30, 60]).all():
        raise ValueError("horizon_min must be 15, 30, or 60")
    if ((frame["rank"] < 1) | (frame["rank"] > 3)).any():
        raise ValueError("rank must be between 1 and 3")
    if (frame["capacity"] <= 0).any():
        raise ValueError("capacity must be greater than zero")
    if (
        (frame["actual_bikes"] < 0) | (frame["actual_bikes"] > frame["capacity"])
    ).any():
        raise ValueError("actual_bikes must be between zero and capacity")

    identity = ["request_id", "candidate_station_id"]
    if frame.duplicated(identity).any():
        raise ValueError("candidate station must be unique within each request")
    if frame.duplicated(["request_id", "rank"]).any():
        raise ValueError("rank must be unique within each request")

    request_fields = [
        "base_time",
        "origin_station_id",
        "horizon_min",
        "mode",
    ]
    inconsistent = frame.groupby("request_id", sort=False)[request_fields].nunique()
    if (inconsistent > 1).any().any():
        raise ValueError("request-level fields must be consistent within a request")

    frame["actual_empty_docks"] = frame["capacity"] - frame["actual_bikes"]
    frame["actual_available"] = frame["actual_bikes"].where(
        frame["mode"].eq("rent"),
        frame["actual_empty_docks"],
    )
    return frame.sort_values(["request_id", "rank"]).reset_index(drop=True)


def evaluate_top3(
    rows: pd.DataFrame,
    *,
    thresholds: tuple[int, ...] = (1, 2),
) -> RecommendationEvaluation:
    """Evaluate Top-3 rent/return availability hit rates.

    Input rows contain only recommendations returned to a user and the actual
    inventory at ``base_time + horizon_min``. A request is a hit when at least
    one returned candidate meets the requested availability threshold.
    """

    if not thresholds or any(value < 1 for value in thresholds):
        raise ValueError("thresholds must contain positive integers")

    frame = _validate_and_normalize(rows)
    request_keys = [
        "request_id",
        "base_time",
        "origin_station_id",
        "horizon_min",
        "mode",
    ]

    request_frames = []
    for threshold in thresholds:
        grouped = frame.groupby(request_keys, sort=True, dropna=False)
        summary = grouped.agg(
            candidate_count=("candidate_station_id", "size"),
            max_actual_available=("actual_available", "max"),
        ).reset_index()
        summary["availability_threshold"] = threshold
        summary["hit"] = summary["max_actual_available"] >= threshold
        request_frames.append(summary)

    request_results = pd.concat(request_frames, ignore_index=True)
    metric_frames = []

    def summarize(group_columns: list[str], scope: str) -> pd.DataFrame:
        metrics = (
            request_results.groupby(
                group_columns + ["mode", "availability_threshold"],
                sort=True,
                dropna=False,
            )
            .agg(
                eligible_requests=("request_id", "nunique"),
                hits=("hit", "sum"),
                mean_candidates=("candidate_count", "mean"),
            )
            .reset_index()
        )
        metrics["hit_rate"] = metrics["hits"] / metrics["eligible_requests"]
        metrics["scope"] = scope
        return metrics

    metric_frames.append(summarize(["horizon_min"], "horizon"))
    metric_frames.append(summarize([], "micro"))
    metrics = pd.concat(metric_frames, ignore_index=True, sort=False)
    metrics["horizon_min"] = metrics["horizon_min"].astype("Int64")
    metrics = metrics[
        [
            "scope",
            "horizon_min",
            "mode",
            "availability_threshold",
            "eligible_requests",
            "hits",
            "hit_rate",
            "mean_candidates",
        ]
    ].sort_values(
        ["availability_threshold", "mode", "scope", "horizon_min"],
        na_position="last",
    )

    metadata = {
        "candidate_rows": int(len(frame)),
        "eligible_requests": int(frame["request_id"].nunique()),
        "thresholds": list(thresholds),
        "horizons": sorted(frame["horizon_min"].astype(int).unique().tolist()),
        "modes": sorted(frame["mode"].unique().tolist()),
    }
    return RecommendationEvaluation(
        request_results=request_results,
        metrics=metrics.reset_index(drop=True),
        metadata=metadata,
    )
