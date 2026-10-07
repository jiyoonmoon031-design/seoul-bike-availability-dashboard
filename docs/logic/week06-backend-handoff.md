# Week 06 Rebalancing Backend Handoff

## 1. Purpose

Week 06에서 문지윤이 구현한 운영자 재배치 알고리즘을 조성은의
Backend/API 계층에 연결하기 위한 handoff 문서이다.

본 문서는 역할 경계, 입력 데이터, 호출 방법, 출력 계약 및 통합 시
주의사항을 정의한다.

## 2. Role Boundary

### 문지윤

다음 재배치 알고리즘을 구현하였다.

- 부족 대여소 판별
- 포화 대여소 판별
- S_min / E_min 계산
- 예측 부족량 D 계산
- 긴급도 U 계산
- 최근 수요 가중치 W 계산
- 재배치 우선순위 P = D × U × W 계산
- 반경 2 km 공급 대여소 탐색
- greedy 이동 매칭
- 차량 적재 한도 적용
- 이동 권장 대수 산출
- 운영자용 response payload 생성

구현 위치:

    src/rebalancing/logic.py

Standalone 검증 runner:

    scripts/run_week06_rebalancing.py

### 조성은

다음 Backend 통합을 담당한다.

- POST /api/v1/predict
- GET /api/v1/operator/risk
- GET /api/v1/operator/rebalancing
- Week 05 final model loading / inference 연동
- DB에서 station context 조회
- Python 재배치 결과와 Backend DTO 연결
- API logging 및 error handling
- JSON response schema 최종 연결

## 3. Rebalancing Engine Input

재배치 엔진은 두 종류의 논리 입력을 사용한다.

### 3.1 Prediction Response

Week 05에서 확정한 기존 Model → Backend prediction response를 사용한다.

필수 정보:

- base_time
- model_version
- predictions[].station_id
- predictions[].capacity
- predictions[].horizon_results[].horizon_min
- predictions[].horizon_results[].bikes_expected
- predictions[].horizon_results[].docks_expected

기존 prediction request/response 계약에는 새로운 public 필드를 추가하지 않는다.

### 3.2 Station Context

Backend는 각 예측 대상 대여소에 대해 다음 정보를 제공해야 한다.

- station_id
- station_name
- latitude
- longitude
- same_dow_time_mean_rent

same_dow_time_mean_rent는 반드시 base_time 이하 정보만 이용해 산출된
동일 요일·시간대 평균 대여량이어야 한다.

미래 실제 수요값은 재배치 계획 생성에 사용할 수 없다.

## 4. Function Boundary

Python 호출 형태:

    config = RebalancingConfig.from_params(params)

    result = build_rebalancing_plan(
        prediction_response,
        station_contexts,
        config=config,
        horizon_min=30,
        top_n=10,
    )

공개 API에 전달할 결과:

    result.response

운영 로그 및 진단용 결과:

    result.warnings
    result.diagnostics

## 5. Public Operator Response

응답 구조:

    {
      "base_time": "2026-10-08T08:00:00+09:00",
      "horizon_min": 30,
      "shortage_top": [],
      "surplus_top": [],
      "move_matches": []
    }

기존 운영자 response contract의 핵심 필드를 그대로 유지한다.

### shortage_top

부족 위험 대여소 목록이며 주요 필드는 다음과 같다.

- station_id
- station_name
- lat
- lon
- bikes_expected
- s_min
- shortage
- urgency
- demand_weight
- priority_score
- risk_time

### surplus_top

공급 후보 대여소 목록이며 주요 필드는 다음과 같다.

- station_id
- docks_expected
- supply_slack

### move_matches

실제 재배치 권고 목록이다.

- from_station_id
- to_station_id
- distance_km
- move_qty

## 6. Parameter Source

재배치 파라미터를 Backend 코드에 중복 하드코딩하지 않는다.

정본은 다음 파일이다.

    config/params.yaml

현재 주요 값:

- S_MIN.capacity_ratio = 0.20
- S_MIN.minimum = 1
- E_MIN.capacity_ratio = 0.20
- E_MIN.minimum = 1
- URGENCY[15] = 4.0
- URGENCY[30] = 2.0
- URGENCY[60] = 1.0
- DEMAND_WEIGHT = 0.5 ~ 2.0
- SEARCH_RADIUS_KM = 2.0
- VEHICLE_CAP = 20
- DETOUR_FACTOR = 1.3

## 7. Integration Rules

1. top_n 기본값은 10으로 사용한다.
2. horizon은 15, 30, 60 중 하나만 허용한다.
3. 개별 대여소 입력 오류가 전체 API 실패로 이어지지 않도록 한다.
4. capacity가 null 또는 0인 대여소는 skip하고 warning을 기록한다.
5. 좌표가 없는 대여소는 공급·수요 후보에서 제외한다.
6. move_qty는 정수 단위로 반환한다.
7. 한 번의 재배치 계획에서 총 이동량은 VEHICLE_CAP을 초과할 수 없다.
8. 공급 대여소는 이동 후 자기 S_min 아래로 내려가면 안 된다.
9. 공급여유가 1대 미만이면 match를 생성하지 않는다.
10. 2 km 내 공급 대여소가 없으면 move_matches=[]를 정상 응답으로 반환한다.
11. Week 06 통합 과정에서 Week 05 모델을 재학습하거나 재튜닝하지 않는다.
12. 미래 actual 값은 재배치 계획 생성에 사용하지 않는다.

## 8. Warning and Diagnostics

Public response contract 변경을 최소화하기 위해 warning 및 진단 정보는
알고리즘 결과 객체에서 별도로 제공한다.

    result.warnings
    result.diagnostics

주요 diagnostics:

- model_version
- shortage_station_count
- saturation_station_count
- move_match_count
- unmatched_shortage_count
- vehicle_capacity
- vehicle_capacity_used
- vehicle_capacity_remaining
- search_radius_km
- detour_factor
- area_same_dow_time_mean_rent
- warning_count

Backend 통합 시 이 값은 API 응답 또는 서버 로그 정책에 따라 별도로
매핑할 수 있다.

## 9. Verified Smoke Test

검증 시나리오:

- base_time: 2026-10-08 08:00 KST
- horizon: 30분
- 수요 대여소 capacity: 20
- 수요 대여소 bikes_expected: 2
- S_min: 4
- shortage: 2
- urgency: 2.0
- demand_weight: 1.0
- priority_score: 4.0

공급 대여소:

- bikes_expected: 19
- docks_expected: 1
- supply_slack: 15
- estimated distance: 0.184 km

생성된 재배치 권고:

    S-001 -> D-001
    move_qty = 2

차량 용량:

- vehicle capacity: 20
- used: 2
- remaining: 18
- warnings: 0

## 10. Review Boundary

조성은은 Backend 통합 구현 작성자이므로 자신이 작성한 Backend 통합
항목을 독립 검토 대상으로 처리할 수 없다.

해당 부분은 필요 시 김수연이 대리 검토한다.

문지윤이 작성한 재배치 알고리즘 자체는 조성은이 검토할 수 있다.
