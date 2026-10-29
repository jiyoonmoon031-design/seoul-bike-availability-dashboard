from datetime import datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PredictionRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "request_id": ("550e8400-e29b-41d4-a716-446655440000"),
                    "base_time": ("2026-10-15T08:30:00+09:00"),
                    "station_ids": [
                        "ST-0001",
                        "ST-0002",
                    ],
                    "horizons": [
                        15,
                        30,
                        60,
                    ],
                }
            ]
        },
    )

    request_id: UUID

    base_time: datetime

    station_ids: list[str] = Field(min_length=1)

    horizons: list[Literal[15, 30, 60]] = Field(min_length=1)

    @field_validator("base_time")
    @classmethod
    def validate_base_time(
        cls,
        value: datetime,
    ) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("base_time must be " "timezone-aware")

        if value.utcoffset() != timedelta(hours=9):
            raise ValueError("base_time must use " "KST offset +09:00")

        if value.minute % 15 != 0 or value.second != 0 or value.microsecond != 0:
            raise ValueError("base_time must align " "to a 15-minute boundary")

        return value

    @field_validator("station_ids")
    @classmethod
    def validate_station_ids(
        cls,
        values: list[str],
    ) -> list[str]:
        cleaned = [value.strip() for value in values]

        if any(not value for value in cleaned):
            raise ValueError("station_ids must not " "contain empty values")

        if len(cleaned) != len(set(cleaned)):
            raise ValueError("station_ids must not " "contain duplicates")

        return cleaned

    @field_validator("horizons")
    @classmethod
    def validate_horizons(
        cls,
        values: list[int],
    ) -> list[int]:
        if len(values) != len(set(values)):
            raise ValueError("horizons must not " "contain duplicates")

        return values


class RebalancingEnvelope(BaseModel):
    prediction_response: dict[
        str,
        Any,
    ]

    station_contexts: list[dict[str, Any]]

    horizon_min: int = Field(
        default=30,
        ge=1,
    )

    top_n: int = Field(
        default=10,
        ge=1,
        le=100,
    )


class RecommendationEnvelope(BaseModel):
    leg: Literal[
        "origin",
        "destination",
    ]

    eta_min: float = Field(ge=0)

    candidates: list[dict[str, Any]]

    top_n: int = Field(
        default=3,
        ge=1,
        le=20,
    )
