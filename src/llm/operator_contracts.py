from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OperatorWarning(StrictModel):
    code: str
    message: str
    station_id: str | None = None
    horizon_min: int | None = None


class ShortageStation(StrictModel):
    station_id: str
    station_name: str | None = None
    lat: float | None = None
    lon: float | None = None
    bikes_expected: float | None = None
    s_min: float | None = None
    shortage: float | None = None
    urgency: float | None = None
    demand_weight: float | None = None
    priority_score: float | None = None
    risk_time: str | None = None
    prediction_source: str | None = None


class SurplusStation(StrictModel):
    station_id: str
    docks_expected: float | None = None
    supply_slack: float | None = None


class MoveMatch(StrictModel):
    from_station_id: str
    to_station_id: str
    distance_km: float | None = None
    move_qty: int | None = None


class OperatorContext(StrictModel):
    base_time: str
    horizon_min: int = Field(ge=0)
    shortage_top: list[ShortageStation] = Field(default_factory=list, max_length=100)
    surplus_top: list[SurplusStation] = Field(default_factory=list, max_length=100)
    move_matches: list[MoveMatch] = Field(default_factory=list, max_length=100)
    warnings: list[OperatorWarning] = Field(default_factory=list, max_length=200)
    prediction_summary: dict[str, Any] = Field(default_factory=dict)
    health: dict[str, Any] = Field(default_factory=dict)
    horizon_snapshots: list[dict[str, Any]] = Field(
        default_factory=list, max_length=200
    )


class OperatorBriefingRequest(StrictModel):
    context: OperatorContext


class OperatorDiagnosisRequest(StrictModel):
    context: OperatorContext


class OperatorQuestionRequest(StrictModel):
    question: str = Field(min_length=1, max_length=500)
    context: OperatorContext
