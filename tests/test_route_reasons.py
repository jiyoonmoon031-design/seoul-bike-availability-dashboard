import json

import pytest
from pydantic import ValidationError

from src.llm import route_reasons
from src.llm.client import LLMExecutionError


def make_route(rank=1):
    return {
        "rank": rank,
        "origin_station_name": "세종대학교",
        "destination_station_name": "성수역",
        "walk_to_origin_min": 2,
        "bike_min": 10,
        "walk_to_destination_min": 1,
        "total_eta_min": 13,
        "origin_bikes_expected": 2.0,
        "destination_docks_expected": 8.0,
        "score": 0.86,
    }


def test_route_reasons_single_call(monkeypatch):
    calls = []

    def fake_generate(**kwargs):
        calls.append(kwargs)

        return json.dumps(
            {
                "reasons": [
                    {"rank": 1, "text": "첫 번째 경로"},
                    {"rank": 2, "text": "두 번째 경로"},
                    {"rank": 3, "text": "세 번째 경로"},
                ]
            }
        )

    monkeypatch.setattr(
        route_reasons,
        "_generate",
        fake_generate,
    )

    result = route_reasons.generate_route_reasons(
        {
            "routes": [
                make_route(1),
                make_route(2),
                make_route(3),
            ]
        }
    )

    assert len(calls) == 1
    assert len(result["reasons"]) == 3
    assert [item["rank"] for item in result["reasons"]] == [1, 2, 3]


def test_invalid_input_rank():
    with pytest.raises(ValidationError):
        route_reasons.RouteReasonsPayload.model_validate(
            {
                "routes": [
                    make_route(1),
                    make_route(1),
                ]
            }
        )


def test_invalid_output_rank(monkeypatch):
    monkeypatch.setattr(
        route_reasons,
        "_generate",
        lambda **kwargs: json.dumps({"reasons": [{"rank": 2, "text": "잘못된 순위"}]}),
    )

    with pytest.raises(LLMExecutionError):
        route_reasons.generate_route_reasons({"routes": [make_route(1)]})


def test_invalid_output_json(monkeypatch):
    monkeypatch.setattr(
        route_reasons,
        "_generate",
        lambda **kwargs: "invalid json",
    )

    with pytest.raises(LLMExecutionError):
        route_reasons.generate_route_reasons({"routes": [make_route(1)]})
