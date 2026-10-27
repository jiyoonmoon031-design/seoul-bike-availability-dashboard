from __future__ import annotations

import logging
import os

from fastapi import (
    FastAPI,
    HTTPException,
)

from ai_service.bridge import (
    BridgeConfigurationError,
    BridgeExecutionError,
    health_status,
    run_predict,
    run_rebalancing,
    run_recommendation,
)
from ai_service.schemas import (
    PredictionRequest,
    RebalancingEnvelope,
    RecommendationEnvelope,
)
from src.llm.client import (
    LLMConfigurationError,
    LLMExecutionError,
    generate_operator_briefing,
    generate_user_reasons,
)
from src.llm.contracts import (
    OperatorBriefingPayload,
    UserRecommendationPayload,
)

logging.basicConfig(level=logging.INFO)

LOGGER = logging.getLogger(__name__)

app = FastAPI(
    title="Seoul Bike AI Service",
    version="0.2.0",
)


def _handle_error(
    error: Exception,
) -> None:
    if isinstance(
        error,
        (
            BridgeConfigurationError,
            LLMConfigurationError,
        ),
    ):
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error

    if isinstance(
        error,
        (
            BridgeExecutionError,
            LLMExecutionError,
        ),
    ):
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error

    LOGGER.exception("Unexpected AI service error")

    raise HTTPException(
        status_code=500,
        detail=("Unexpected AI service error"),
    ) from error


@app.get("/health")
def health():
    result = health_status()

    llm_ready = bool(os.getenv("OPENAI_API_KEY"))

    result["components"]["llm"] = {
        "ready": llm_ready,
        "model": os.getenv(
            "OPENAI_MODEL",
            "gpt-6-luna",
        ),
    }

    result["ready"] = bool(result.get("ready")) and llm_ready

    result["status"] = "ready" if result["ready"] else "degraded"

    return result


@app.post("/predict")
def predict(
    payload: PredictionRequest,
):
    try:
        return run_predict(payload.model_dump(mode="json"))
    except Exception as error:
        _handle_error(error)


@app.post("/recommend")
def recommend(
    payload: RecommendationEnvelope,
):
    try:
        return run_recommendation(payload.model_dump())
    except Exception as error:
        _handle_error(error)


@app.post("/rebalancing")
def rebalancing(
    payload: RebalancingEnvelope,
):
    try:
        return run_rebalancing(payload.model_dump())
    except Exception as error:
        _handle_error(error)


@app.post("/llm/operator-briefing")
def operator_briefing(
    payload: OperatorBriefingPayload,
):
    try:
        return generate_operator_briefing(payload.model_dump())
    except Exception as error:
        _handle_error(error)


@app.post("/llm/recommendation-reasons")
def recommendation_reasons(
    payload: UserRecommendationPayload,
):
    try:
        return generate_user_reasons(payload.model_dump())
    except Exception as error:
        _handle_error(error)
