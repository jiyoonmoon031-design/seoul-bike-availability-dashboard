# 서울 따릉이 API 연동 가이드

프런트엔드는 Spring Boot 백엔드를 호출합니다. 백엔드는 경로 좌표를 TMAP에서 조회하고, 예측·재배치·GPT 설명은 FastAPI에 요청합니다.

| 서비스 | 기본 로컬 주소 | 스키마 |
| --- | --- | --- |
| 백엔드 | `http://127.0.0.1:8080` | [OpenAPI 스냅샷](../openapi.json), 실행 시 `/v3/api-docs` |
| AI | `http://127.0.0.1:8000` | 실행 시 `/openapi.json`과 Swagger UI `/docs` |

## 백엔드

| 메서드와 경로 | 입력과 용도 |
| --- | --- |
| `GET /api/v1/search/places`, `GET /api/v1/search/addresses` | `query`로 출발지와 목적지를 검색 |
| `GET /api/v1/stations/status` | 최신 대여소 재고와 UTC 수집 시각 `collected_at` 조회 |
| `GET /api/v1/stations/nearby` | `latitude`, `longitude` 기준 주변 대여소 조회 |
| `POST /api/v1/predict` | `request_id`, `base_time`, `station_ids`, `horizons`로 재고 예측 요청 |
| `GET /api/v1/recommendations` | `leg`, `latitude`, `longitude`, 선택값 `etaMin`, `topN`으로 출발 또는 도착 대여소 추천 |
| `GET /api/v1/routes/recommendations` | `originLat`, `originLon`, `destinationLat`, `destinationLon`으로 최대 3개 경로를 추천. 각 경로에 대여·반납 위치, ETA, 예측·수집 출처 포함 |
| `GET /api/v1/routes` | 두 좌표 사이 한 구간의 지도 경로 조회 |
| `GET /api/v1/operator/risk`, `GET /api/v1/operator/rebalancing`, `GET /api/v1/operator/briefing` | `basetime`, `horizon`, 선택값 `topn`으로 운영자용 위험·재배치·브리핑 조회 |
| `POST /api/v1/llm/route-reasons` | `{"routes":[...]}`의 1~3개 추천 경로를 설명. 응답은 `{"reasons":[{"rank":1,"text":"…"}]}` |
| `POST /api/v1/llm/recommendation-reasons` | 단일 출발 또는 도착 대여소 추천 설명 |
| `POST /api/v1/llm/operator-copilot/briefing`, `/diagnosis`, `/qa` | `{"context":{...}}`에 `base_time`, `horizon_min`과 운영 지표를 전달. 질의 요청에는 1~500자의 `question` 추가 |

### 지도 경로

```sh
curl -fsS 'http://127.0.0.1:8080/api/v1/routes?startLat=37.5665&startLon=126.978&endLat=37.5701&endLon=126.9827&bike=false'
```

- 위경도는 WGS84입니다. 위도는 −90~90, 경도는 −180~180이며, 좌표가 없거나 잘못되면 HTTP 400입니다.
- 응답은 `distance_m`, `eta_min`, `method`, `path`입니다. `path`는 출발부터 도착 순서의 `{latitude, longitude}` 배열입니다.
- `method=route_api`는 TMAP 보행 경로 좌표입니다. `bike=true`는 같은 경로 거리로 시속 15km를 가정해 시간을 추정합니다. 자전거 전용 도로나 주행 허용 여부는 판별하지 않습니다.
- `method=straight_line`도 HTTP 200입니다. TMAP 오류 또는 경로 좌표 누락 시 양 끝 좌표와 추정 시간이 반환됩니다. 경로 확인에는 HTTP 상태와 `method`를 함께 확인하세요.
- 추천 지도는 출발지→대여소, 대여소→반납소, 반납소→목적지를 구간별로 조회합니다. TMAP 좌표는 실선, 대체 경로는 점선입니다.

### GPT 요청

`route-reasons` 요청의 각 경로에는 `rank`, `origin_station_name`, `destination_station_name`, `walk_to_origin_min`, `bike_min`, `walk_to_destination_min`, `total_eta_min`, `origin_bikes_expected`, `destination_docks_expected`, `score`를 전달합니다.
백엔드의 `LLM_AUTH_REQUIRED=true` 모드에서는 신뢰할 수 있는 게이트웨이가 `X-LLM-Token`을 보냅니다. LLM 기본 제한은 64 KiB 및 호출자당 분당 20회입니다. 토큰 거부는 HTTP 401, 크기 초과는 413, 호출 한도 초과는 429입니다.

## FastAPI와 개발용 ngrok

| 메서드와 경로 | 입력과 용도 |
| --- | --- |
| `GET /health` | 구성 요소 설정 상태. HTTP 200에서도 `ready`를 확인해야 함 |
| `POST /predict` | UUID `request_id`, 15분 단위 KST `base_time`, 대여소 1~200개 `station_ids`, 중복 없는 `horizons` (15/30/60분) |
| `POST /recommend` | `leg`, `eta_min`, `candidates`, `top_n`으로 대여 또는 반납 후보 평가 |
| `POST /rebalancing` | `prediction_response`, `station_contexts`, `horizon_min`, `top_n`으로 재배치 추천 |
| `POST /llm/route-reasons`, `/recommendation-reasons`, `/operator-briefing`, `/operator-copilot/{briefing,diagnosis,qa}` | 백엔드 응답을 바탕으로 설명·진단·질의 처리 |

- 같은 호스트에서는 `AI_SERVER_URL=http://127.0.0.1:8000`을 사용합니다.
- 개발용 ngrok HTTPS 주소를 쓰는 백엔드에는 `AI_SERVER_URL`, `AI_SERVER_BASIC_USER`, `AI_SERVER_BASIC_PASSWORD`를 환경변수로 설정합니다. 인증은 Java가 FastAPI로 요청할 때 적용됩니다.
- ngrok에는 [Basic Auth Traffic Policy](https://ngrok.com/docs/gateway/traffic-policy/examples/add-authentication)를 적용하고 인증 없이 `/health` 호출 시 401을 확인합니다. 자격 증명은 팀의 비밀 저장소를 사용합니다.
- 외부 백엔드를 사용한다면 FastAPI의 `AI_BACKEND_BASE_URL`도 재고 API에 접근할 수 있는 주소로 설정해야 합니다.

AI 서버를 호스팅하는 터미널에서 모델 파일과 환경변수를 준비한 다음, 프로젝트 루트에서 실행합니다.

```sh
export AI_BACKEND_BASE_URL=http://127.0.0.1:8080
export AI_FEATURE_TABLE_PATH=/absolute/path/to/week03_features.parquet
.venv/bin/python -m uvicorn ai_service.app:app --host 127.0.0.1 --port 8001
```

다른 터미널에서는 Basic Auth 정책 파일의 로컬 경로를 지정합니다.

```sh
ngrok http http://127.0.0.1:8001 --inspect=false --traffic-policy-file /secure/path/ai-ngrok-policy.json
```

백엔드 담당자는 승인된 개발용 HTTPS 주소와 팀 자격 증명을 설정하고, 필요한 TMAP 키는 자신의 백엔드 환경에 설정합니다. 백엔드의 경로 API가 반환한 `method`로 해당 환경의 TMAP 연결을 확인할 수 있습니다.
