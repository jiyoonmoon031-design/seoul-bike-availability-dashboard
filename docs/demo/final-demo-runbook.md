# Final Service Demo Runbook

Related issue: #45

## 1. Demo objective

Show one end-to-end user route and one operator rebalancing view while keeping
the boundary between live integration, deterministic logic, and LLM
explanation explicit.

## 2. Pre-demo environment

Required local services:

1. MySQL with station and recent `station_snapshot` rows;
2. FastAPI AI service with the frozen model and feature/inventory paths;
3. Spring Boot backend;
4. Vite frontend;
5. Kakao and Seoul Open Data credentials in local environment files.

Never show `.env`, API keys, database passwords, or the temporary ngrok URL on
screen.

## 3. Start order

### AI service

```bash
export AI_FEATURE_TABLE_PATH=/absolute/path/to/week03_features.parquet
export AI_INVENTORY_PATH=/absolute/path/to/current_inventory.json
export OPENAI_API_KEY=<local-secret>
uvicorn ai_service.app:app --host 127.0.0.1 --port 8000
```

Confirm `GET http://127.0.0.1:8000/health` before continuing.

### Backend

```bash
cd backend
./gradlew bootRun
```

Confirm the backend health and station-status endpoints used by the frontend.

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

Open the Vite URL shown in the terminal and keep browser developer tools
closed during the presentation.

## 4. User demo script

1. Select the user tab.
2. Search `세종대학교` as origin and `성수역` as destination.
3. Point out origin and destination markers.
4. Explain that origin uses future bikes and destination uses future docks.
5. Compare rank, walking distance, current inventory, and expected inventory.
6. Read one recommendation reason and state that the LLM only verbalizes the
   structured result.
7. Resize or switch to the prepared mobile view only if time permits.

Expected duration: 90 seconds.

## 5. Operator demo script

1. Switch to the operator tab.
2. Identify the highest-priority risk station.
3. Explain source station, destination station, move quantity, and risk time.
4. State that the displayed ordering is deterministic and the explanation
   layer does not calculate a new plan.
5. Describe the oracle backtest as an upper bound, not realized model effect.

Expected duration: 60 seconds.

## 6. Fallback plan

| Failure | Immediate fallback |
|---|---|
| Kakao search unavailable | Use the prepared three-route fixture recording |
| AI service unavailable | Show the committed smoke JSON and explain the contract |
| Backend unavailable | Use the verified MSW UI fixture |
| LLM unavailable | Show structured recommendation/rebalancing values without prose |
| Full service startup fails | Present the embedded screenshots in the final PPT |

The presenter must say when fallback data is used. Do not describe a fixture
or screenshot as a live response.

## 7. Final checks

- [ ] No credential is visible.
- [ ] Health checks are green.
- [ ] User route returns three origin and three destination cards.
- [ ] Map markers are visible.
- [ ] Operator table has at least one row.
- [ ] Browser zoom is 90–100%.
- [ ] PPT and screenshots are available offline.
- [ ] Top-3 hit rate is not quoted until Issue #42 has official inputs.

