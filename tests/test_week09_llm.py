import pytest

from src.llm.payloads import (
    build_operator_payload,
    build_user_payload,
)
from src.llm.prompts import (
    COMMON_RULES,
    OPERATOR_BRIEFING_PROMPT,
    USER_REASON_PROMPT,
)


def test_operator_payload():
    result = build_operator_payload(
        {
            "base_time": "2026-10-28T08:00:00+09:00",
            "horizon_min": 30,
            "shortage_top": [
                {
                    "station_id": "D",
                    "bikes_expected": 2.0,
                    "s_min": 4,
                    "risk_time": "2026-10-28T08:30:00+09:00",
                }
            ],
            "move_matches": [
                {
                    "from_station_id": "S",
                    "to_station_id": "D",
                    "move_qty": 2,
                }
            ],
        },
        {
            "D": "수요 대여소",
            "S": "공급 대여소",
        },
    )

    assert result["shortage_top"][0]["station_name"] == "수요 대여소"

    assert result["move_matches"][0]["from_station_name"] == "공급 대여소"


def test_operator_missing_name():
    with pytest.raises(ValueError):
        build_operator_payload(
            {
                "base_time": "x",
                "horizon_min": 30,
                "shortage_top": [
                    {
                        "station_id": "X",
                        "bikes_expected": 1,
                        "s_min": 4,
                        "risk_time": "y",
                    }
                ],
                "move_matches": [],
            },
            {},
        )


def test_user_payload():
    result = build_user_payload(
        {
            "leg": "origin",
            "eta_min": 8,
            "recommendations": [
                {
                    "rank": 1,
                    "station_name": "세종대학교 정문",
                    "distance_m": 420,
                    "bikes_expected": 7.4,
                    "docks_expected": 12.6,
                }
            ],
        }
    )

    assert result["leg"] == "origin"
    assert result["candidates"][0]["rank"] == 1


def test_prompt_constraints():
    assert "새로 계산하지 않는다" in COMMON_RULES

    assert "150자" in OPERATOR_BRIEFING_PROMPT

    assert "40자" in USER_REASON_PROMPT
