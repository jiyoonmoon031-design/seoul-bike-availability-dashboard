# Model ↔ Backend Interface Specification

## Status

- Project: Seoul Bike Availability Dashboard
- Week: Week 01
- GitHub Issue: #3 `W01: Define model-backend JSON interface`
- Owner: 문지윤
- Backend Reviewer: 조성은
- Status: Draft v0.1
- Target: Week 01 interface confirmation

---

# 1. Purpose

본 문서는 단기 순재고 변화량 예측 모델과 Backend 사이의 데이터 계약을 정의한다.

모델과 Backend는 본 문서의 필드명, 데이터 의미, 시간 규약 및 예측값 산출 규칙을 공통 기준으로 사용한다.

인터페이스 변경 시 코드만 수정하지 않고 본 문서를 함께 수정한다.

---

# 2. Prediction Unit

모델의 기본 예측 단위는 다음과 같다.

```text
station_id × base_time × horizon
```

예측 horizon은 다음 세 구간을 사용한다.

```text
15분
30분
60분
```

즉 특정 대여소 `station_id`의 기준시각 `base_time`에 대해 각각 15분, 30분, 60분 후의 순재고 변화를 예측한다.

---

# 3. Prediction Target

모델의 예측 target은 대여소별 미래 순재고 변화량이다.

```text
delta_net = return_count - rent_count
```

표기:

```text
Δ(station_id, t, h)
```

의미:

```text
Δ > 0
→ 반납량이 대여량보다 많음
→ 자전거 재고 증가 방향

Δ < 0
→ 대여량이 반납량보다 많음
→ 자전거 재고 감소 방향

Δ = 0
→ 순재고 변화 없음
```

---

# 4. Future Inventory Calculation

모델의 `delta_net` 예측값과 현재 실시간 자전거 수를 결합하여 미래 예상 자전거 수를 계산한다.

```text
bikes_expected
= clip(bikes_now + delta_net, 0, capacity)
```

미래 예상 빈 거치대 수:

```text
docks_expected
= capacity - bikes_expected
```

따라서 항상 다음 조건을 만족해야 한다.

```text
0 <= bikes_expected <= capacity
0 <= docks_expected <= capacity
```

`bikes_expected`와 `docks_expected`는 모델 예측으로부터 생성되는 연속값이므로 소수값을 허용한다.

---

# 5. Training Target and Validation Ground Truth

학습 target과 실제 검증값은 서로 다른 데이터 원천을 사용한다.

## 5.1 Training Target

대여·반납 이용이력에서 생성한다.

```text
delta_hist = return_count - rent_count
```

용도:

```text
모델 학습
모델 validation
시간순 hold-out 평가
```

## 5.2 Validation Ground Truth

자체 수집한 실시간 재고 snapshot에서 생성한다.

```text
delta_snap = B(t+h) - B(t)
```

용도:

```text
실제 재고 변화 검증
Top-3 가용성 검증
10주차 backtesting
```

## 5.3 Rebalancing Intervention Detection

두 변화량의 차이를 이용하여 재배치 차량 개입 의심 구간을 표시한다.

```text
abs(delta_snap - delta_hist) >= INTERVENTION_THRESHOLD
```

초기 `INTERVENTION_THRESHOLD`는 `config/params.yaml`을 따른다.

---

# 6. Time Convention

프로젝트의 시간 규약은 다음과 같다.

## Application / API

```text
KST
timezone-aware
UTC+09:00 offset 명시
```

예:

```text
2026-10-15T08:30:00+09:00
```

## Database

DB 저장 시각은 UTC를 기준으로 한다.

```text
API / Application:
2026-10-15T08:30:00+09:00

DB:
2026-10-14T23:30:00Z
```

API 응답 시 다시 KST offset을 명시한다.

timezone 정보가 없는 naive datetime을 API 계약에 사용하지 않는다.

---

# 7. station_id Convention

`station_id`는 원천 데이터가 제공하는 값을 문자열로 관리한다.

```text
type = string
```

규칙:

- 원천 `station_id` 값을 그대로 사용한다.
- 숫자로 임의 변환하지 않는다.
- 좌측 0을 제거하지 않는다.
- Model, Backend, DB, Frontend에서 동일한 ID를 사용한다.

예:

```json
"station_id": "ST-0001"
```

실제 서울시 원천 ID 형식 확인 후 예시 표현만 수정할 수 있으며, ID를 문자열로 취급한다는 원칙은 유지한다.

---

# 8. Prediction Request

Direction:

```text
Backend → Model
```

## 8.1 JSON

```json
{
  "request_id": "uuid-v4",
  "base_time": "2026-10-15T08:30:00+09:00",
  "station_ids": [
    "ST-0001",
    "ST-0002"
  ],
  "horizons": [
    15,
    30,
    60
  ]
}
```

---

# 9. Prediction Request Field Definition

| Field | Type | Required | Description |
|---|---|---:|---|
| `request_id` | string | Yes | 요청 추적용 UUID v4 |
| `base_time` | string(datetime) | Yes | 예측 기준시각, KST timezone-aware |
| `station_ids` | array[string] | Yes | 예측 대상 대여소 ID 목록 |
| `horizons` | array[integer] | Yes | 요청 예측구간 |

지원 horizon:

```text
15
30
60
```

현재 v1 계약에서는 위 세 horizon을 사용한다.

---

# 10. Prediction Response

Direction:

```text
Model → Backend
```

## 10.1 JSON

```json
{
  "request_id": "uuid-v4",
  "base_time": "2026-10-15T08:30:00+09:00",
  "model_version": "lgbm-v1.2.0",
  "source": "model",
  "predictions": [
    {
      "station_id": "ST-0001",
      "capacity": 20,
      "bikes_now": 12,
      "horizon_results": [
        {
          "horizon_min": 15,
          "delta_net": -3.2,
          "bikes_expected": 8.8,
          "docks_expected": 11.2
        },
        {
          "horizon_min": 30,
          "delta_net": -6.5,
          "bikes_expected": 5.5,
          "docks_expected": 14.5
        },
        {
          "horizon_min": 60,
          "delta_net": -9.1,
          "bikes_expected": 2.9,
          "docks_expected": 17.1
        }
      ]
    }
  ],
  "warnings": []
}
```

---

# 11. Prediction Response Field Definition

## Top Level

| Field | Type | Required | Description |
|---|---|---:|---|
| `request_id` | string | Yes | 요청과 동일한 request ID |
| `base_time` | string(datetime) | Yes | 예측 기준시각 |
| `model_version` | string | Yes | 사용된 모델 버전 |
| `source` | string | Yes | 결과 생성 원천 |
| `predictions` | array | Yes | 대여소별 예측 결과 |
| `warnings` | array | Yes | 예측 경고 또는 처리 사유 |

## Prediction Object

| Field | Type | Required | Description |
|---|---|---:|---|
| `station_id` | string | Yes | 대여소 ID |
| `capacity` | integer | Review | 해당 시점 거치대 수 |
| `bikes_now` | integer | Review | 기준시각 현재 자전거 수 |
| `horizon_results` | array | Yes | horizon별 결과 |

`capacity`, `bikes_now`의 예측 불가 상황에서의 null 허용 여부는 Backend 담당자와 Week 01에 최종 확정한다.

## Horizon Result

| Field | Type | Required | Description |
|---|---|---:|---|
| `horizon_min` | integer | Yes | 15 / 30 / 60 |
| `delta_net` | number | Yes | 예측 순재고 변화량 |
| `bikes_expected` | number | Yes | clipping 적용 후 미래 예상 자전거 수 |
| `docks_expected` | number | Yes | 미래 예상 빈 거치대 수 |

---

# 12. source Contract

`source`는 다음 값을 사용한다.

```text
model
baseline_fallback
cache
```

## model

정상 모델 inference 결과.

```json
"source": "model"
```

## baseline_fallback

모델 inference 실패 등으로 baseline을 사용한 경우.

```json
"source": "baseline_fallback"
```

## cache

실시간 API 장애 등으로 최근 cache 데이터를 사용한 경우.

```json
"source": "cache"
```

Frontend는 이 필드를 이용해 fallback 상태를 표시할 수 있다.

---

# 13. Prediction Failure Policy

특정 대여소의 예측이 불가능하더라도 해당 대여소를 `predictions` 배열에서 제거하지 않는다.

예:

```json
{
  "station_id": "ST-0002",
  "capacity": 20,
  "bikes_now": 7,
  "horizon_results": []
}
```

예측 실패 또는 처리 사유는 `warnings`에 기록한다.

`warnings`의 세부 구조는 Backend 담당자와 Week 01 리뷰에서 확정한다.

현재 결정되지 않은 warning object 구조를 임의로 고정하지 않는다.

---

# 14. Null Policy

Master Execution Guide는 Week 01에 null 허용/불허 필드를 명시하도록 요구한다.

현재 문서만으로 최종 null 정책을 확정할 수 없는 필드는 다음과 같다.

```text
capacity
bikes_now
warnings element structure
```

따라서 아래 사항을 조성은과 검토 후 확정한다.

| 항목 | 검토 질문 |
|---|---|
| `capacity` | 대여소 master 조회 실패 시 null 허용인가, station 전체 실패인가 |
| `bikes_now` | 실시간 snapshot 미존재 시 null 허용인가, cache/fallback으로 반드시 채울 것인가 |
| `warnings` | string 배열인가 structured object 배열인가 |
| 일부 horizon 실패 | 성공 horizon만 반환할지 station 전체 `horizon_results=[]`로 할지 |

확정 후 본 절을 수정하고 Draft 상태를 해제한다.

---

# 15. Feature Input Boundary

현재 v1 Prediction Request 계약은 다음 필드만 Backend에서 Model로 전달한다.

```text
request_id
base_time
station_ids
horizons
```

모델이 사용하는 실제 feature는 다음과 같다.

```text
현재 재고
최근 15/30/60분 대여량
최근 15/30/60분 반납량
요일
시간대
공휴일
기상
대여소 패턴 feature
```

다만 이 feature들을 Backend가 직접 request payload에 전달할지,
Model 계층이 Feature Store/DB에서 조회할지는 현재 문서에서 확정되어 있지 않다.

따라서 Week 01 Backend 리뷰에서 구현 경계를 확정한다.

JSON request 계약 자체를 변경하는 경우 본 문서와 관련 코드를 함께 변경한다.

---

# 16. Shared Parameter Source

모델 및 Backend에서 공유하는 parameter는 다음 파일을 단일 기준으로 사용한다.

```text
config/params.yaml
```

코드 내부에 동일 parameter를 개별 hardcoding하지 않는다.

인터페이스와 직접 관련된 주요 값:

```text
HORIZONS = [15, 30, 60]

RANDOM_SEED = 42

SNAPSHOT_INTERVAL_MIN = 5
(API quota 확인 결과에 따라 15 가능)

AVAIL_MIN = 1

AVAIL_STABLE = 2

SEARCH_RADIUS_KM = 2.0

INTERVENTION_THRESHOLD = 5
(초기값, 데이터 분포 확인 후 조정 가능)
```

---

# 17. Core Project Parameters

Master Execution Guide에서 정의한 핵심 parameter는 다음과 같다.

| Parameter | Definition | Status |
|---|---|---|
| `S_MIN` | `max(1, ceil(0.20 × capacity))` | Defined |
| `URGENCY` | 15→4.0 / 30→2.0 / 60→1.0 | Defined |
| `DEMAND_W` | 권역 평균 대비 동일 요일·시간대 수요비, 0.5~2.0 clip | Defined |
| `HORIZON_MAP` | (0,0), (15,Δ15), (30,Δ30), (60,Δ60) 선형보간 | Defined |
| `MOVE_QTY` | min(부족량, 공급여유, 차량 잔여 적재량) | Defined |
| `VEHICLE_CAP` | 20 | Assumption |
| `SEARCH_RADIUS_KM` | 2.0 km | Defined |
| `WEATHER_STATION` | 권역 단일 관측지점 | Week 01 Pending |
| `STATION_MASTER_POLICY` | 주 1회 재수집 및 버전 관리 | Defined |

`VEHICLE_CAP=20`은 근거가 확정되지 않은 가정값으로 유지한다.

`WEATHER_STATION`은 확인 전 임의 값을 입력하지 않는다.

---

# 18. Model Version

모든 정상 예측 응답에는 `model_version`을 포함한다.

예:

```text
lgbm-v1.2.0
```

목적:

- 어떤 모델이 결과를 생성했는지 추적
- backtesting 재현
- 모델 변경 전후 성능 비교
- 최종 보고서 결과와 코드 버전 연결

실제 model version naming 규칙은 모델 확정 시 추가할 수 있다.

---

# 19. Interface Change Rule

본 인터페이스가 확정된 이후 다음 변경은 반드시 GitHub Issue 및 PR을 통해 수행한다.

예:

```text
field 추가
field 삭제
field 이름 변경
type 변경
null 정책 변경
horizon 변경
source 값 변경
시간대 규칙 변경
station_id 규칙 변경
```

절차:

```text
Issue
→ 변경 영향 확인
→ 문서 수정
→ 코드 수정
→ Reviewer 검토
→ PR
→ develop merge
```

무단 interface 변경은 허용하지 않는다.

---

# 20. Week 01 Review Checklist

## 문지윤

- [x] prediction unit 정의
- [x] target 정의
- [x] request JSON 초안
- [x] response JSON 초안
- [x] 시간 규약 작성
- [x] station_id 규약 작성
- [x] source 규약 작성
- [x] target 이원화 전략 작성
- [ ] null 정책 확정
- [ ] feature 조회 책임 경계 확정

## 조성은 Review

- [ ] request payload를 Backend에서 실제 생성 가능한가
- [ ] response payload를 Backend에서 실제 소비 가능한가
- [ ] `capacity` 획득 위치 확인
- [ ] `bikes_now` 획득 위치 확인
- [ ] cache 적용 주체 확인
- [ ] null 허용 필드 확정
- [ ] warning 구조 확정
- [ ] feature 조회 주체 확정
- [ ] API mock 구현 가능한 계약인지 확인

---

# 21. Definition of Done

본 인터페이스 작업은 다음이 완료되어야 종료한다.

- [ ] 문지윤 초안 작성 완료
- [ ] 예측 Request/Response JSON 예제 저장
- [ ] 조성은 Backend 관점 Review 완료
- [ ] Review comment 반영
- [ ] null 정책 확정
- [ ] feature 조회 책임 경계 확정
- [ ] mock request/response JSON validation 완료
- [ ] Pull Request 승인
- [ ] `develop` merge
- [ ] GitHub Issue #3 close

---

# 22. Change History

| Version | Status | Description |
|---|---|---|
| v0.1 | Draft | Week 01 initial Model ↔ Backend contract |
