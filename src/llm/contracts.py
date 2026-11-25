from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OperatorShortage(StrictModel):
    station_name: str
    bikes_expected: float
    s_min: float
    risk_time: str


class OperatorMove(StrictModel):
    from_station_name: str
    to_station_name: str
    move_qty: int = Field(ge=1)


class OperatorBriefingPayload(StrictModel):
    base_time: str
    horizon_min: int
    shortage_top: list[OperatorShortage] = Field(max_length=100)
    move_matches: list[OperatorMove] = Field(max_length=100)


class UserCandidate(StrictModel):
    rank: int = Field(ge=1)
    station_name: str
    distance_m: float = Field(ge=0)
    bikes_expected: float = Field(ge=0)
    docks_expected: float = Field(ge=0)


class UserRecommendationPayload(StrictModel):
    leg: Literal[
        "origin",
        "destination",
    ]
    eta_min: float = Field(ge=0)
    candidates: list[UserCandidate] = Field(min_length=1, max_length=20)
