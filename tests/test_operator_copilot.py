from types import SimpleNamespace

import pytest
from pydantic import ValidationError

import src.llm.operator_copilot as copilot
from src.llm.operator_contracts import (
    OperatorBriefingRequest,
    OperatorContext,
    OperatorDiagnosisRequest,
    OperatorQuestionRequest,
)


def context() -> OperatorContext:
    return OperatorContext(
        base_time="2025-07-31T15:00:00Z",
        horizon_min=30,
        shortage_top=[
            {
                "station_id": "ST-99",
                "station_name": "자양(뚝섬한강공원)역 1번출구 앞",
                "bikes_expected": 1.2116891198657518,
                "shortage": 5.788310880134248,
                "priority_score": 11.576621760268496,
                "urgency": 2.0,
                "demand_weight": 1.0,
            }
        ],
        surplus_top=[
            {
                "station_id": "ST-446",
                "docks_expected": 1.788120633561924,
                "supply_slack": 5.211879366438076,
            }
        ],
        move_matches=[
            {
                "from_station_id": "ST-446",
                "to_station_id": "ST-99",
                "distance_km": 1.52,
                "move_qty": 5,
            }
        ],
        warnings=[],
        prediction_summary={"prediction_source": "model"},
        health={"backend_station_status_configured": True},
    )


def fake_llm_result() -> dict:
    return {
        "text": "검증된 운영 데이터만 설명했습니다.",
        "model": "gpt-6-luna",
        "response_id": "resp_test",
        "cache_hit": False,
        "cache_source_response_id": None,
        "usage": {
            "input_tokens": 10,
            "cached_tokens": 0,
            "output_tokens": 5,
            "reasoning_tokens": 0,
            "total_tokens": 15,
        },
        "latency_ms": 12.3,
        "prompt_version": copilot.PROMPT_VERSION,
    }


def test_contract_forbids_extra_fields():
    with pytest.raises(ValidationError):
        OperatorContext(
            base_time="2025-07-31T15:00:00Z",
            horizon_min=30,
            unsupported_field=True,
        )


def test_briefing_returns_original_evidence(monkeypatch):
    captured = {}

    def fake_request(**kwargs):
        captured.update(kwargs)
        return fake_llm_result()

    monkeypatch.setattr(copilot, "_perform_openai_request", fake_request)
    result = copilot.generate_operator_briefing_v2(
        OperatorBriefingRequest(context=context())
    )

    assert captured["feature"] == "operator_briefing_v2"
    assert result["evidence"]["shortage_top"][0]["priority_score"] == 11.576621760268496
    assert result["llm"]["response_id"] == "resp_test"


def test_diagnosis_passes_structured_warning(monkeypatch):
    captured = {}
    raw = context().model_dump()
    raw["warnings"] = [
        {
            "code": "FEATURE_ROW_NOT_FOUND",
            "message": "feature row not found for base_time",
            "station_id": "ST-102",
            "horizon_min": None,
        }
    ]
    ctx = OperatorContext.model_validate(raw)

    def fake_request(**kwargs):
        captured.update(kwargs)
        return fake_llm_result()

    monkeypatch.setattr(copilot, "_perform_openai_request", fake_request)
    result = copilot.diagnose_operator_state(
        OperatorDiagnosisRequest(context=ctx)
    )

    assert captured["feature"] == "operator_diagnosis"
    assert result["evidence"]["warnings"][0]["code"] == "FEATURE_ROW_NOT_FOUND"


def test_qa_keeps_question_and_context(monkeypatch):
    captured = {}

    def fake_request(**kwargs):
        captured.update(kwargs)
        return fake_llm_result()

    monkeypatch.setattr(copilot, "_perform_openai_request", fake_request)
    result = copilot.answer_operator_question(
        OperatorQuestionRequest(
            question="왜 ST-99가 최우선인가?",
            context=context(),
        )
    )

    assert captured["feature"] == "operator_qa"
    assert captured["payload"]["question"] == "왜 ST-99가 최우선인가?"
    assert result["evidence"]["context"]["move_matches"][0]["move_qty"] == 5


def test_usage_extraction():
    response = SimpleNamespace(
        usage=SimpleNamespace(
            input_tokens=20,
            input_tokens_details=SimpleNamespace(cached_tokens=3),
            output_tokens=9,
            output_tokens_details=SimpleNamespace(reasoning_tokens=0),
            total_tokens=29,
        )
    )

    assert copilot._extract_usage(response) == {
        "input_tokens": 20,
        "cached_tokens": 3,
        "output_tokens": 9,
        "reasoning_tokens": 0,
        "total_tokens": 29,
    }


def test_cache_key_is_deterministic(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-6-luna")
    first = copilot._cache_key(
        feature="operator_qa",
        instructions="x",
        payload={"b": 2, "a": 1},
    )
    second = copilot._cache_key(
        feature="operator_qa",
        instructions="x",
        payload={"a": 1, "b": 2},
    )
    assert first == second


def test_prompts_forbid_new_calculation():
    assert "숫자를 새로 계산하지 않는다" in copilot.COMMON_RULES
    assert "결정을 변경하거나 실행하지 않는다" in copilot.COMMON_RULES


def test_question_length_validation():
    with pytest.raises(ValidationError):
        OperatorQuestionRequest(question="", context=context())
