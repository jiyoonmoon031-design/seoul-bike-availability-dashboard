# Team Work Guide

## 1. Team

| 팀원 | GitHub | 주요 담당 영역 |
|---|---|---|
| 문지윤 | `@jiyoonmoon031-design` | AI 모델링, 피처엔지니어링, 재배치 로직, 운영자 탭 |
| 조성은 | `@whtjddms0714-byte` | Backend, DB, 외부 API, 실시간 수집, 시스템 통합 |
| 김수연 | `@rlatndusgu` | AI 검증, 추천 검증, 이용자 탭, 사용자 시나리오 |

프로젝트 작업은 담당 영역을 기준으로 수행하되 모든 작업은 GitHub Issue와 Pull Request로 관리합니다.

---

# 2. 가장 먼저 알아야 할 Branch 구조

```text
main
└── develop
    ├── data/...
    ├── model/...
    ├── backend/...
    ├── frontend/...
    ├── feat/...
    ├── test/...
    ├── docs/...
    └── fix/...
```

## main

주차별 내부 검토가 완료된 안정 버전입니다.

다음 상황에서 기준으로 사용합니다.

- 교수 미팅
- 중간점검
- 주차별 확정 결과
- 최종 발표
- 최종 결과보고서

직접 개발하지 않습니다.

## develop

3명의 개발 결과를 통합하는 기본 개발 브랜치입니다.

일반 Task PR은 모두 `develop`을 대상으로 합니다.

## Task Branch

Issue 하나당 하나의 branch를 사용합니다.

작업할 때만 생성하고 merge 후 삭제합니다.

---

# 3. 작업 시작 방법

먼저 자신에게 할당된 GitHub Issue를 확인합니다.

그 다음:

```bash
git switch develop
git pull origin develop
```

작업 branch 생성:

```bash
git switch -c <branch-name>
```

예:

### 문지윤

```bash
git switch -c docs/model-backend-interface
```

또는:

```bash
git switch -c model/feature-engineering
```

### 조성은

```bash
git switch -c data/realtime-snapshot
```

또는:

```bash
git switch -c backend/prediction-api
```

### 김수연

```bash
git switch -c data/weather-station-selection
```

또는:

```bash
git switch -c test/model-validation
```

---

# 4. 어디에 무엇을 저장하는가

## `data/`

데이터 파일 관리 영역입니다.

### `data/raw/`

원천 데이터.

예:

- 서울시 대여소 마스터 원본
- 대여/반납 이력 원본
- 기상 원본

실제 대용량 파일은 GitHub에 올리지 않습니다.

### `data/interim/`

중간 처리 데이터.

예:

- ID 정규화 후 데이터
- timestamp 변환 후 데이터
- join 전 임시 dataset

GitHub 추적 대상이 아닙니다.

### `data/processed/`

모델 입력용 최종 처리 데이터.

GitHub 추적 대상이 아닙니다.

### `data/sample/`

재현 테스트용 소량 sample 데이터.

팀원이 코드를 실행하기 위해 필요한 작은 데이터만 GitHub에 올립니다.

---

# 5. 데이터 수집 코드

## 서울시 따릉이

```text
src/ingestion/seoul_bike/
```

여기에 저장:

- 대여소 마스터 수집
- 이용이력 수집
- 실시간 대여정보 API
- station snapshot 수집

### P0

실시간 스냅샷 수집기는 프로젝트 최우선 작업입니다.

주 담당:

```text
조성은
```

일일 적재 품질 확인:

```text
김수연
```

---

## 기상

```text
src/ingestion/weather/
```

여기에 저장:

- 기상 API 호출
- 관측지점 데이터 수집
- 기상 원천 파싱

---

## 달력

```text
src/ingestion/calendar/
```

여기에 저장:

- 공휴일
- 요일
- 주말
- 시간대 관련 데이터 생성

---

# 6. 데이터 정제

```text
src/preprocessing/
```

여기에 저장:

- timestamp 정규화
- station_id 정리
- 결측 처리
- 중복 제거
- 15분 bin 생성
- 데이터 join
- capacity 처리

EDA Notebook 안에만 최종 preprocessing 로직을 남기지 않습니다.

재사용하는 로직은 반드시 `src/preprocessing/`으로 옮깁니다.

---

# 7. Feature Engineering

```text
src/features/
```

여기에 저장:

- rent_15 / rent_30 / rent_60
- return_15 / return_30 / return_60
- delta lag
- moving average
- hour
- weekday
- holiday
- commute peak
- weather features
- station pattern features

---

# 8. Model

## Baseline

```text
src/models/baseline/
```

예:

- persistence
- moving average
- 동일 요일·시간 평균

## Forecasting Model

```text
src/models/forecasting/
```

예:

- Linear Model
- Random Forest
- LightGBM
- XGBoost
- inference logic

대용량 model weight/checkpoint는 GitHub에 직접 올리지 않습니다.

---

# 9. 운영자 재배치

```text
src/rebalancing/
```

여기에 저장:

- 부족량 계산
- 포화 판정
- 긴급도
- 최근 수요 가중치
- 재배치 우선순위 점수
- 2km 후보 탐색
- greedy matching
- 이동 권장 대수

---

# 10. 이용자 추천

```text
src/recommendation/
```

여기에 저장:

- 주변 대여소 탐색
- 거리 계산
- ETA
- horizon interpolation
- 출발 대여소 score
- 도착 대여소 score
- Top-3 추천

---

# 11. LLM

```text
src/llm/
```

LLM은 계산을 담당하지 않습니다.

여기에 저장:

- structured JSON payload 생성
- prompt
- 응답 검증
- fallback template

LLM에 다음을 위임하지 않습니다.

- 수치 계산
- 재배치 계산
- 추천 순위 계산
- 점수 계산

---

# 12. Backend

```text
backend/
```

여기에 저장:

- API Server
- DB 연결
- prediction endpoint
- station endpoint
- operator endpoint
- recommendation endpoint
- cache
- fallback
- error handling
- health check

예:

```text
POST /api/v1/predict
GET  /api/v1/stations
GET  /api/v1/operator/risk
GET  /api/v1/operator/rebalancing
```

---

# 13. Frontend

## 운영자 화면

```text
frontend/operator/
```

여기에 저장:

- 부족/포화 대여소 지도
- 위험도 표
- 재배치 우선순위
- 이동 매칭 리스트

## 이용자 화면

```text
frontend/user/
```

여기에 저장:

- 출발지 입력
- 목적지 입력
- Top-3 추천
- 지도
- 추천 카드
- 추천 사유

Frontend framework가 확정되면 현재 구조 안에서 세부 디렉터리를 추가합니다.

---

# 14. Notebook

```text
notebooks/
```

## EDA

```text
notebooks/01_eda/
```

## Baseline

```text
notebooks/02_baseline/
```

## Modeling

```text
notebooks/03_modeling/
```

## Validation

```text
notebooks/04_validation/
```

Notebook은 분석·실험용입니다.

서비스에서 반복 사용하는 최종 로직은 `src/`로 옮깁니다.

---

# 15. Tests

## Unit

```text
tests/unit/
```

개별 함수 테스트.

## Integration

```text
tests/integration/
```

예:

- Model ↔ Backend
- Backend ↔ Frontend
- API ↔ DB

## Fixtures

```text
tests/fixtures/
```

테스트용 sample JSON/CSV.

---

# 16. Configuration

```text
config/params.yaml
```

공통 parameter의 단일 기준입니다.

예:

- HORIZONS
- S_MIN
- E_MIN
- URGENCY
- SEARCH_RADIUS_KM
- VEHICLE_CAP
- WALK_SPEED
- DETOUR_FACTOR
- WEATHER_STATION

동일 값을 Python 파일마다 직접 hardcoding하지 않습니다.

변경 시:

1. GitHub Issue 또는 PR에 변경 이유 기록
2. `params.yaml` 수정
3. 관련 결과 재검증

---

# 17. Interface 문서

```text
docs/interface/
```

여기에 저장:

- Model → Backend JSON
- Backend → Frontend JSON
- API schema
- field definition
- timezone 규칙
- station_id 규칙

Interface를 코드에서 변경하면 문서도 같은 PR에서 수정합니다.

---

# 18. Architecture 문서

```text
docs/architecture/
```

여기에 저장:

- 전체 시스템 구성도
- DB 구조
- 서비스 흐름
- 배포 구조

---

# 19. 주차별 기술 요약

```text
docs/weekly/
```

예:

```text
w01-summary.md
w02-summary.md
w03-summary.md
```

이 문서는 팀 기술 진행상황을 기록합니다.

학교에 개인별로 제출하는 주간학습보고서와는 별개입니다.

---

# 20. 결과물

## 모델 성능

```text
reports/model/
```

예:

```text
model_comparison.csv
horizon_metrics.csv
feature_importance.png
```

## 검증

```text
reports/validation/
```

예:

```text
availability_metrics.csv
top3_hit_rate.csv
rebalancing_backtest.csv
```

## PPT/보고서용 그림

```text
reports/figures/
```

최종 보고서와 PPT에 사용하는 그래프를 저장합니다.

---

# 21. 작업 위치 빠른 표

| 작업 | 위치 |
|---|---|
| 실시간 따릉이 수집 | `src/ingestion/seoul_bike/` |
| 대여소 마스터 수집 | `src/ingestion/seoul_bike/` |
| 기상 수집 | `src/ingestion/weather/` |
| 달력 데이터 | `src/ingestion/calendar/` |
| 데이터 정제 | `src/preprocessing/` |
| Feature | `src/features/` |
| Baseline | `src/models/baseline/` |
| 예측 모델 | `src/models/forecasting/` |
| 재배치 | `src/rebalancing/` |
| 이용자 추천 | `src/recommendation/` |
| LLM | `src/llm/` |
| Backend API | `backend/` |
| 운영자 화면 | `frontend/operator/` |
| 이용자 화면 | `frontend/user/` |
| EDA | `notebooks/01_eda/` |
| 모델 실험 | `notebooks/03_modeling/` |
| Backtesting | `notebooks/04_validation/` |
| 자동 테스트 | `tests/` |
| 공통 parameter | `config/params.yaml` |
| Interface | `docs/interface/` |
| 주차별 기술요약 | `docs/weekly/` |
| 모델 결과 | `reports/model/` |
| 검증 결과 | `reports/validation/` |
| PPT/보고서 그래프 | `reports/figures/` |

---

# 22. 작업 완료

작업이 끝나면:

```bash
git status
git add .
git commit -m "<type>: <summary>"
git push -u origin <현재-branch>
```

그 다음 GitHub에서:

```text
현재 Task Branch → develop
```

Pull Request를 생성합니다.

PR merge 후 local:

```bash
git switch develop
git pull origin develop
git branch -d <작업-branch>
```

---

# 23. 절대 하지 않는 것

```text
main에서 직접 개발
develop에서 직접 개발
사람 이름별 영구 branch 생성
대용량 raw data commit
.env commit
API Key commit
Notebook에만 최종 서비스 로직 보관
Interface 변경 후 문서 미수정
자기 코드 자기 최종 승인
```
