# Week 09 AI Service & LLM Handoff

## Owner

Moon Jiyoon

## Purpose

Week 09 AI/LLM integration handoff for the Seoul Bike availability dashboard.

The FastAPI service exposes prediction, recommendation, rebalancing, and
LLM explanation endpoints.

The LLM is an explanation-only thin layer and must not perform numeric
calculation, ranking, prediction, or recommendation logic.

## Public AI Server

AI_SERVER_URL:

`<NGROK_HTTPS_URL>`

Swagger:

`<NGROK_HTTPS_URL>/docs`

This ngrok URL is for development/integration testing only.

Both FastAPI/Uvicorn and ngrok must remain running.
The URL may change after ngrok is restarted.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | /health | AI service/component status |
| POST | /predict | future inventory prediction |
| POST | /recommend | user Top-N recommendation |
| POST | /rebalancing | operator rebalancing plan |
| POST | /llm/operator-briefing | operator natural-language briefing |
| POST | /llm/recommendation-reasons | user recommendation reasons |
| GET | /docs | FastAPI Swagger UI |

## Prediction

POST `/predict`

Request contains:

- request_id
- base_time
- station_ids
- horizons
- current inventory

Response contains:

- model_version
- delta_net
- bikes_expected
- docks_expected
- warnings

## User Recommendation

POST `/recommend`

Response contains:

- effective_horizon
- recommendations
- rank
- bikes_expected
- docks_expected
- score
- score_breakdown

## Operator Rebalancing

POST `/rebalancing`

Response contains:

- shortage_top
- surplus_top
- move_matches

## Operator LLM Briefing

POST `/llm/operator-briefing`

Example:

```json
{
  "base_time": "2026-10-28T08:00:00+09:00",
  "horizon_min": 30,
  "shortage_top": [
    {
      "station_name": "건대입구역 2번출구",
      "bikes_expected": 2.0,
      "s_min": 4.0,
      "risk_time": "2026-10-28T08:30:00+09:00"
    }
  ],
  "move_matches": [
    {
      "from_station_name": "성수역 3번출구",
      "to_station_name": "건대입구역 2번출구",
      "move_qty": 2
    }
  ]
}
User Recommendation Reasons
POST /llm/recommendation-reasons

Example:{
  "leg": "origin",
  "eta_min": 8,
  "candidates": [
    {
      "rank": 1,
      "station_name": "세종대학교 정문",
      "distance_m": 420,
      "bikes_expected": 7.4,
      "docks_expected": 12.6
    }
  ]
}
LLM Contract
The LLM must:
1. use only values present in the input JSON;
2. never invent station names, times, or quantities;
3. never calculate new sums, differences, ratios, rankings, or scores;
4. never make a new prediction or recommendation;
5. omit uncertain information instead of estimating it;
6. use bikes_expected for origin explanations;
7. use docks_expected for destination explanations.
Configuration:
- model: gpt-6-luna
- temperature: 0.2
- reasoning effort: none
- key: server-side OPENAI_API_KEY
Never commit or expose OPENAI_API_KEY.
Backend Integration Responsibility
The backend integration should:
- use AI_SERVER_URL for AI calls;
- connect predict/recommend/rebalancing endpoints;
- connect LLM endpoints;
- validate numeric tokens in LLM responses;
- reject a response containing numbers absent from the input payload;
- use a rule-based fallback after rejection;
- expose integrated component health.
Validation
Verified:
- Week 09 tests: 4 passed
- repository pre-commit: PASS
- GET /health: 200
- POST /predict: 200
- POST /recommend: 200
- POST /rebalancing: 200
- POST /llm/operator-briefing: 200
- POST /llm/recommendation-reasons: 200
- OpenAI Responses API: 200
Current Limitation
/predict currently depends on the historical point-in-time feature table
configured by AI_FEATURE_TABLE_PATH.

The current deployment is suitable for API integration and demo testing.
Real-time DB -> feature generation -> model inference integration remains
system-integration work.
Operations
The public endpoint remains available only while:
1. Uvicorn/FastAPI is running.
2. ngrok is running.
The ngrok URL must be shared only with project team members.
