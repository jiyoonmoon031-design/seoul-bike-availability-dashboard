from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

from src.llm.contracts import (
    OperatorBriefingPayload,
    UserRecommendationPayload,
)
from src.llm.prompts import (
    OPERATOR_BRIEFING_PROMPT,
    USER_REASON_PROMPT,
)


class LLMConfigurationError(RuntimeError):
    pass


class LLMExecutionError(RuntimeError):
    pass


def _model() -> str:
    return os.getenv(
        "OPENAI_MODEL",
        "gpt-6-luna",
    )


def _client() -> OpenAI:
    if not os.getenv("OPENAI_API_KEY"):
        raise LLMConfigurationError("OPENAI_API_KEY is not set")

    return OpenAI()


def _generate(
    *,
    instructions: str,
    payload: dict[str, Any],
    max_output_tokens: int,
) -> str:
    try:
        response = _client().responses.create(
            model=_model(),
            reasoning={"effort": "none"},
            temperature=0.2,
            store=False,
            max_output_tokens=(max_output_tokens),
            instructions=instructions,
            input=json.dumps(
                payload,
                ensure_ascii=False,
            ),
        )
    except Exception as exc:
        raise LLMExecutionError("OpenAI response failed") from exc

    text = response.output_text.strip()

    if not text:
        raise LLMExecutionError("OpenAI response was empty")

    return text


def generate_operator_briefing(
    payload: dict[str, Any],
) -> dict[str, Any]:
    validated = OperatorBriefingPayload.model_validate(payload)

    text = _generate(
        instructions=OPERATOR_BRIEFING_PROMPT,
        payload=validated.model_dump(),
        max_output_tokens=180,
    )

    return {
        "model": _model(),
        "temperature": 0.2,
        "text": text,
    }


def generate_user_reasons(
    payload: dict[str, Any],
) -> dict[str, Any]:
    validated = UserRecommendationPayload.model_validate(payload)

    reasons = []

    for candidate in validated.candidates:
        candidate_payload = {
            "leg": validated.leg,
            "eta_min": validated.eta_min,
            "candidate": candidate.model_dump(),
        }

        text = _generate(
            instructions=USER_REASON_PROMPT,
            payload=candidate_payload,
            max_output_tokens=80,
        )

        reasons.append(
            {
                "rank": candidate.rank,
                "station_name": candidate.station_name,
                "text": text,
            }
        )

    return {
        "model": _model(),
        "temperature": 0.2,
        "reasons": reasons,
    }
