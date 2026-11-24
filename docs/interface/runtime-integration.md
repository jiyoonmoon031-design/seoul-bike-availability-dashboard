# Runtime Integration Interface

## 1. Prediction

POST /predict

- Timezone: Asia/Seoul (UTC+09:00)
- Base time: aligned to a 15-minute boundary
- Supported horizons: 15, 30, 60 minutes
- Primary model: frozen Week 05 forecasting model
- Runtime fallback: B3 day-of-week/time mean
- Final fallback: B1 persistence when B3 execution fails
- Prediction source: model or baseline_fallback

Historical feature rows are not fabricated when
current-time features are unavailable.

The historical model capacity constraint remains unchanged. Runtime inventory
uses the separate overflow-aware policy in
`docs/data/runtime-inventory-policy.md`.

## 2. Recommendation

The Backend PredictionProvider owns prediction calls.

The Backend attaches horizon_results to each
recommendation candidate before calling POST /recommend.

The AI recommendation service does not execute
prediction again.

GET /api/v1/recommendations
GET /api/v1/routes/recommendations

## 3. Operator Rebalancing

GET /api/v1/operator/rebalancing

Query parameters:

- basetime: ISO-8601 datetime with timezone
- horizon: 15, 30, or 60
- topn: number of requested results

## 4. LLM Integration

Existing OpenAI client and configured model are reused.

### Backend endpoints

POST /api/v1/llm/recommendation-reasons
POST /api/v1/llm/route-reasons
POST /api/v1/llm/operator-copilot/briefing
POST /api/v1/llm/operator-copilot/diagnosis
POST /api/v1/llm/operator-copilot/qa

### AI endpoint added

POST /llm/route-reasons

Route explanation input:

- routes: array containing one to three routes
- rank
- origin_station_name
- destination_station_name
- walk_to_origin_min
- bike_min
- walk_to_destination_min
- total_eta_min
- origin_bikes_expected
- destination_docks_expected
- score

Route explanation output:

- model
- temperature
- reasons: array of rank and text

The LLM explains existing results and does not
modify prediction values, route rankings or move plans.

LLM requests are triggered separately by the user.

## 5. Known Limitations

- Current-time Random Forest feature generation
  is not implemented.
- Current-time predictions may use B3/B1 fallback.
- Missing, invalid and stale inventory remains excluded.
- Inventory exceeding registered capacity remains usable and is reported as
  overflow; available docks are clamped at zero.
- TMAP authentication is unresolved.
- Map connections are schematic straight lines.
- Prediction provenance is propagated to route cards; full live operator
  warning coverage still requires an integrated Backend/AI run.
- Production LLM authentication, request limits and CORS controls are
  implemented but require trusted proxy configuration.
- In-process warm scoring is optimized; full live HTTP p95 still requires the
  real DB and provider configuration.

## 6. Local Integration Evidence

Test date: 2026-11-25 KST

Integration checkpoint: 77749f8

- Python tests: 77 passed at checkpoint
- Backend Gradle tests: passed
- Frontend lint, TypeScript and build: passed
- API E2E: 9 passed, 1 failed
- Failed station prediction: ST-1760
- Realtime station inventory count: 180
- Stations exceeding capacity: 107
- Top 3 route recommendation: 25.278 seconds
- GPT route explanations: 5.140 seconds
- Operator briefing: 2.994 seconds
- Operator diagnosis: 2.839 seconds
- Operator QA: 9.829 seconds

User route recommendation and operator dashboard
were also verified in the local browser.

The failed prediction is retained as a known
integration limitation, not reported as a pass.

## 7. Runtime Inventory Warnings

Additional station-level warnings:

| Code | Meaning |
|---|---|
| MISSING_INVENTORY | Realtime station inventory is unavailable |
| INVALID_INVENTORY | Inventory is outside the supported range |
| INVENTORY_OVER_CAPACITY | Observed bikes exceed registered capacity |

When runtime inventory is unavailable or invalid,
the affected station retains an empty horizon_results array.

Other valid stations continue to return predictions.

Missing inventory must not be replaced with fabricated
values or stale historical inventory.

The historical capacity constraint remains unchanged; the runtime projection
ceiling is `max(registered_capacity, observed_inventory)`.

### Additional validation

- Runtime fallback tests: 7 passed
- Full Python test suite: 94 passed
- Java PredictionWarning uses a String code field.
- Live API regression verification remains required.

### Observed inventory limitations

- ST-1760 was absent from realtime station status.
- Its latest stored snapshot was collected on
  2026-09-13 07:30 KST.
- The stale snapshot must not be used as current inventory.
- 107 of 180 stations exceeded registered capacity during the earlier live
  integration test. The policy now preserves those observations, and the new
  interface/calculation remains a reviewer approval item.
