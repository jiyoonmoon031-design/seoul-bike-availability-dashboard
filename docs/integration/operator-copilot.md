# Operator Copilot — LLM 확장 설계 및 운영 가이드

## 1. 목적

OpenAI API는 예측이나 재배치 의사결정을 대신하지 않는다.

```text
                  ┌── Random Forest
Backend data ────►│
                  ├── B3 / B1 fallback
                  │
                  ▼
             deterministic
              predictions
                  │
                  ▼
             Rebalancing
                  │
        ┌─────────┴─────────┐
        │                   │
    Operator UI        LLM Context Builder
        │                   │
        │                   ▼
        │              OpenAI Responses API
        │                GPT-6 Luna
        │                   │
        │          ┌────────┼────────┐
        │          ▼        ▼        ▼
        │       Briefing  Diagnosis  Q&A
        │
        └────────── 결과는 항상 원본 수치와 함께 표시
```

LLM은 **Briefing / Diagnosis / Q&A**만 담당한다. GPT가 없어도 prediction과 rebalancing은 정상 동작해야 한다.

## 2. 안전 원칙

- 예측 수치·부족량·priority_score·이동대수 재계산 금지
- 새로운 대여소·재배치 추천 생성 금지
- 입력에 없는 원인 확정 금지
- 실행 명령 자동 수행 금지
- 답변과 함께 원본 `evidence` 반환
- context로 확인할 수 없는 질문은 근거 부족을 명시

## 3. Endpoint

### `POST /llm/operator-copilot/briefing`
현재 horizon의 부족 위험, 공급 후보, 이동 매칭, warning/fallback을 운영자 관점으로 요약한다.

### `POST /llm/operator-copilot/diagnosis`
structured warning, prediction source, health를 근거로 장애/데이터 상태를 설명하고 확인 항목을 제시한다.

### `POST /llm/operator-copilot/qa`
현재 화면 context만 사용해 자연어 질문에 답한다. 예: `왜 ST-99가 최우선인가?`

## 4. 공통 Request Context

```json
{
  "context": {
    "base_time": "2025-07-31T15:00:00Z",
    "horizon_min": 30,
    "shortage_top": [],
    "surplus_top": [],
    "move_matches": [],
    "warnings": [],
    "prediction_summary": {},
    "health": {},
    "horizon_snapshots": []
  }
}
```

raw history 전체를 LLM에 보내지 않는다. 화면 판단에 필요한 Top N, move match, structured warning, health summary만 보낸다.

## 5. 공통 Response Envelope

```json
{
  "kind": "operator_qa",
  "text": "LLM 설명",
  "evidence": {},
  "llm": {
    "model": "gpt-6-luna",
    "response_id": "resp_...",
    "cache_hit": false,
    "cache_source_response_id": null,
    "usage": {
      "input_tokens": 100,
      "cached_tokens": 0,
      "output_tokens": 40,
      "reasoning_tokens": 0,
      "total_tokens": 140
    },
    "latency_ms": 321.4,
    "prompt_version": "operator-copilot-v1"
  }
}
```

`response_id`와 token usage를 애플리케이션에서 직접 기록하므로 OpenAI API 사용 여부를 사후에 검증할 수 있다.

## 6. 비용 최적화

- 페이지 refresh마다 호출하지 않고 **on-demand** 호출
- 동일 model + prompt version + canonical JSON에 SHA-256 cache key 적용
- 기본 TTL 300초
- stable instruction prefix + variable JSON input 구조 유지
- 각 기능의 `max_output_tokens` 제한
- `reasoning={"effort":"none"}` 사용

환경변수:

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-6-luna"
export OPENAI_LLM_CACHE_TTL_SEC="300"
export OPENAI_USAGE_LOG_PATH="/tmp/seoul-bike-openai-usage.jsonl"  # optional
```

## 7. Usage logging

실제 OpenAI 호출마다 다음을 logger에 기록한다.

- feature
- model
- response_id
- input_tokens
- cached_tokens
- output_tokens
- reasoning_tokens
- total_tokens
- latency_ms

`OPENAI_USAGE_LOG_PATH`를 설정하면 JSONL에도 추가 저장한다. API key와 전체 prompt 원문은 usage log에 기록하지 않는다.

## 8. 테스트

```bash
python3 -m pytest -q tests/test_operator_copilot.py
python3 -m pytest -q
python3 -m pre_commit run --all-files
git diff --check
```

실제 OpenAI smoke:

```bash
PYTHONPATH=. python3 scripts/run_operator_copilot_smoke.py
```

이 smoke는 Briefing/Diagnosis/Q&A를 실제 Responses API로 호출하므로 token usage가 발생한다.

## 9. 팀원 역할별 확인 포인트

**Frontend**
- `text`는 설명용
- 지도/표/숫자는 기존 deterministic API 또는 `evidence`를 authoritative source로 사용
- LLM 장애 시 core UI는 유지

**Backend**
- rebalancing response를 context builder에 전달
- raw DB dump는 LLM에 전달하지 않음
- LLM endpoint 실패를 `/predict`나 `/operator/rebalancing` 실패로 전파하지 않음

**AI**
- Random Forest/B3/B1 및 rebalancing 의사결정 로직은 변경하지 않음
- `prediction_source`와 structured warning을 context에 보존
- prompt 정책 변경 시 `PROMPT_VERSION` 갱신

## 10. 장애 정책

OpenAI API 장애 시 prediction/rebalancing은 계속 제공한다. LLM 설명 영역만 unavailable로 처리한다.

Cache는 프로세스 메모리의 단기 중복방지 수단이며 business data 저장소가 아니다.
