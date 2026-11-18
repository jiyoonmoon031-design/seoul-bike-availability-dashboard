from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

from src.llm.operator_contracts import (
    OperatorBriefingRequest,
    OperatorDiagnosisRequest,
    OperatorQuestionRequest,
)

LOGGER = logging.getLogger(__name__)

PROMPT_VERSION = "operator-copilot-v1"

COMMON_RULES = """
너는 서울시 따릉이 운영자 지원용 설명 계층이다.

[절대 규칙]
- 예측값, 부족량, priority_score, 이동대수, 거리, 순위 등 숫자를 새로 계산하지 않는다.
- 입력 JSON에 없는 숫자, 대여소, 원인, 장애 사실을 만들어내지 않는다.
- 예측 또는 재배치 결정을 변경하거나 실행하지 않는다.
- model / baseline_fallback / warning 상태를 입력 그대로 구분한다.
- 확정할 수 없는 원인은 추정하지 말고 "제공된 운영 데이터만으로 확인할 수 없습니다"라고 말한다.
- 답변에 사용한 핵심 근거는 반드시 입력 JSON에 존재해야 한다.
- 한국어로 간결하고 운영자가 다음 행동을 이해하기 쉽게 작성한다.

결정 로직은 Random Forest/B3/B1 및 deterministic rebalancing이 담당한다.
너는 설명, 진단, 질의응답만 담당한다.
""".strip()

BRIEFING_PROMPT = (
    COMMON_RULES
    + """

[운영 브리핑]
- 현재 horizon의 부족 위험, 공급 후보, 이동 매칭을 3~5문장으로 요약한다.
- 가장 우선순위가 높은 부족 대여소가 있으면 입력의 priority_score와 shortage를 근거로 언급한다.
- warning 또는 baseline_fallback이 있으면 정상 model 결과와 구분해서 알린다.
- horizon_snapshots가 있으면 시간에 따른 위험 변화 방향만 설명하고 새로운 차이/비율을 계산하지 않는다.
"""
)

DIAGNOSIS_PROMPT = (
    COMMON_RULES
    + """

[진단]
- warning, prediction_summary, health에 실제로 나타난 사실만 진단한다.
- FEATURE_ROW_NOT_FOUND 등 warning code가 있으면 feature/data 계층 문제로 표시할 수 있다.
- BASELINE_FALLBACK이 있으면 fallback 사용 사실을 명시하되 원인을 임의로 확정하지 않는다.
- health에 backend/API 오류가 명시된 경우에만 backend/API 문제라고 말한다.
- 마지막에 "확인할 항목"을 최대 3개 제시한다.
"""
)

QA_PROMPT = (
    COMMON_RULES
    + """

[운영자 Q&A]
- 질문에 직접 답한다.
- 입력에 있는 station_id, priority_score, shortage, move match, prediction_source, warning을 근거로 설명한다.
- 입력에 없는 정책 변경, 새로운 재배치 수량, 새로운 대여소 추천을 생성하지 않는다.
- 질문이 제공된 context만으로 답할 수 없으면 그 사실을 명시한다.
"""
)

_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_LOCK = threading.Lock()


def _model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-6-luna").strip() or "gpt-6-luna"


def _cache_ttl_seconds() -> int:
    raw = os.getenv("OPENAI_LLM_CACHE_TTL_SEC", "300").strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError("OPENAI_LLM_CACHE_TTL_SEC must be an integer") from exc
    return max(0, value)


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _cache_key(
    *,
    feature: str,
    instructions: str,
    payload: dict[str, Any],
) -> str:
    material = "\n".join(
        [
            PROMPT_VERSION,
            _model(),
            feature,
            instructions,
            _canonical_json(payload),
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _cache_get(key: str) -> dict[str, Any] | None:
    ttl = _cache_ttl_seconds()
    if ttl <= 0:
        return None

    now = time.monotonic()
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry is None:
            return None
        created, value = entry
        if now - created > ttl:
            _CACHE.pop(key, None)
            return None

        cached = dict(value)
        cached["cache_hit"] = True
        cached["cache_source_response_id"] = cached.get("response_id")
        cached["response_id"] = None
        cached["usage"] = {
            "input_tokens": 0,
            "cached_tokens": 0,
            "output_tokens": 0,
            "reasoning_tokens": 0,
            "total_tokens": 0,
        }
        return cached


def _cache_put(key: str, value: dict[str, Any]) -> None:
    if _cache_ttl_seconds() <= 0:
        return

    with _CACHE_LOCK:
        if len(_CACHE) >= 256:
            oldest = next(iter(_CACHE))
            _CACHE.pop(oldest, None)
        _CACHE[key] = (time.monotonic(), dict(value))


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _extract_usage(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    input_details = getattr(usage, "input_tokens_details", None)
    output_details = getattr(usage, "output_tokens_details", None)

    return {
        "input_tokens": _safe_int(getattr(usage, "input_tokens", 0)),
        "cached_tokens": _safe_int(
            getattr(input_details, "cached_tokens", 0)
        ),
        "output_tokens": _safe_int(getattr(usage, "output_tokens", 0)),
        "reasoning_tokens": _safe_int(
            getattr(output_details, "reasoning_tokens", 0)
        ),
        "total_tokens": _safe_int(getattr(usage, "total_tokens", 0)),
    }


def _log_usage(record: dict[str, Any]) -> None:
    LOGGER.info(
        "openai_usage=%s",
        json.dumps(record, ensure_ascii=False, sort_keys=True),
    )

    raw_path = os.getenv("OPENAI_USAGE_LOG_PATH", "").strip()
    if not raw_path:
        return

    path = Path(raw_path).expanduser()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(record, ensure_ascii=False, sort_keys=True)
                + "\n"
            )
    except OSError:
        LOGGER.exception("failed to write OPENAI_USAGE_LOG_PATH")


def _perform_openai_request(
    *,
    feature: str,
    instructions: str,
    payload: dict[str, Any],
    max_output_tokens: int,
) -> dict[str, Any]:
    key = _cache_key(
        feature=feature,
        instructions=instructions,
        payload=payload,
    )

    cached = _cache_get(key)
    if cached is not None:
        return cached

    started = time.perf_counter()
    client = OpenAI()

    response = client.responses.create(
        model=_model(),
        reasoning={"effort": "none"},
        instructions=instructions,
        input=_canonical_json(payload),
        max_output_tokens=max_output_tokens,
    )

    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    usage = _extract_usage(response)

    result = {
        "text": response.output_text.strip(),
        "model": getattr(response, "model", _model()),
        "response_id": getattr(response, "id", None),
        "cache_hit": False,
        "cache_source_response_id": None,
        "usage": usage,
        "latency_ms": latency_ms,
        "prompt_version": PROMPT_VERSION,
    }

    _log_usage(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "feature": feature,
            "model": result["model"],
            "response_id": result["response_id"],
            "latency_ms": latency_ms,
            "cache_hit": False,
            **usage,
        }
    )

    _cache_put(key, result)
    return result


def _result_envelope(
    *,
    kind: str,
    llm_result: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "kind": kind,
        "text": llm_result["text"],
        "evidence": evidence,
        "llm": {
            key: value
            for key, value in llm_result.items()
            if key != "text"
        },
    }


def generate_operator_briefing_v2(
    request: OperatorBriefingRequest,
) -> dict[str, Any]:
    evidence = request.context.model_dump(exclude_none=True)
    llm_result = _perform_openai_request(
        feature="operator_briefing_v2",
        instructions=BRIEFING_PROMPT,
        payload=evidence,
        max_output_tokens=220,
    )
    return _result_envelope(
        kind="operator_briefing",
        llm_result=llm_result,
        evidence=evidence,
    )


def diagnose_operator_state(
    request: OperatorDiagnosisRequest,
) -> dict[str, Any]:
    evidence = request.context.model_dump(exclude_none=True)
    llm_result = _perform_openai_request(
        feature="operator_diagnosis",
        instructions=DIAGNOSIS_PROMPT,
        payload=evidence,
        max_output_tokens=260,
    )
    return _result_envelope(
        kind="operator_diagnosis",
        llm_result=llm_result,
        evidence=evidence,
    )


def answer_operator_question(
    request: OperatorQuestionRequest,
) -> dict[str, Any]:
    evidence = {
        "question": request.question,
        "context": request.context.model_dump(exclude_none=True),
    }
    llm_result = _perform_openai_request(
        feature="operator_qa",
        instructions=QA_PROMPT,
        payload=evidence,
        max_output_tokens=240,
    )
    return _result_envelope(
        kind="operator_qa",
        llm_result=llm_result,
        evidence=evidence,
    )
