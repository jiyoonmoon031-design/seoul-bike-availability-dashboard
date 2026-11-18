from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.llm.operator_copilot import (
    answer_operator_question,
    diagnose_operator_state,
    generate_operator_briefing_v2,
)
from src.llm.operator_contracts import (
    OperatorBriefingRequest,
    OperatorContext,
    OperatorDiagnosisRequest,
    OperatorQuestionRequest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rebalancing",
        type=Path,
        default=Path("reports/week12/e2e/operator_rebalancing_30m.json"),
    )
    parser.add_argument(
        "--prediction",
        type=Path,
        default=Path("reports/week12/e2e/predict_st102.json"),
    )
    parser.add_argument(
        "--health",
        type=Path,
        default=Path("reports/week12/e2e/ai_health.json"),
    )
    parser.add_argument(
        "--question",
        default="가장 우선순위가 높은 부족 대여소와 근거를 설명해줘.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    args = parse_args()
    rebalance = load_json(args.rebalancing)
    prediction = load_json(args.prediction)
    health = load_json(args.health)

    context = OperatorContext(
        base_time=rebalance["base_time"],
        horizon_min=int(rebalance["horizon_min"]),
        shortage_top=rebalance.get("shortage_top", []),
        surplus_top=rebalance.get("surplus_top", []),
        move_matches=rebalance.get("move_matches", []),
        warnings=prediction.get("warnings", []),
        prediction_summary={
            "model_version": prediction.get("model_version"),
            "source": prediction.get("source"),
        },
        health=health,
    )

    outputs = {
        "briefing": generate_operator_briefing_v2(
            OperatorBriefingRequest(context=context)
        ),
        "diagnosis": diagnose_operator_state(
            OperatorDiagnosisRequest(context=context)
        ),
        "qa": answer_operator_question(
            OperatorQuestionRequest(question=args.question, context=context)
        ),
    }
    print(json.dumps(outputs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
