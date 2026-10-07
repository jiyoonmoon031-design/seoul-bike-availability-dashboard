# Week 06 Operator Rebalancing Logic

## 1. Purpose

Week 05에서 확정한 단기 순재고 변화량 예측 결과를 운영자가 사용할 수
있는 부족·포화 위험 및 자전거 재배치 권고로 변환한다.

Week 06에서는 예측 모델을 다시 학습하거나 튜닝하지 않는다.

## 2. Processing flow

운영자 재배치 로직은 아래 순서로 수행한다.

1. 미래 예상 재고 확인
2. 부족·포화 판별
3. 부족량 D 계산
4. 최초 부족 horizon을 이용한 긴급도 U 계산
5. 동일 요일·시간대 대여량 기반 수요 가중치 W 계산
6. 우선순위 점수 P = D × U × W 계산
7. 부족 대여소 우선순위 정렬
8. 반경 2 km 내 포화 대여소 탐색
9. 공급여유와 차량 적재한도를 적용한 greedy matching
10. 공급 대여소 → 수요 대여소 이동 권장 대수 산출

## 3. Parameters

모든 주요 파라미터는 `config/params.yaml`을 SSOT로 사용한다.

### Minimum inventory

`S_min(s) = max(1, ceil(0.20 × capacity(s)))`

### Minimum empty docks

`E_min(s) = max(1, ceil(0.20 × capacity(s)))`

### Shortage

`D(s,h) = max(0, S_min(s) - B_pred(s,h))`

### Urgency

최초 부족 발생 horizon을 기준으로 한다.

| First shortage horizon | Urgency |
|---:|---:|
| 15 min | 4.0 |
| 30 min | 2.0 |
| 60 min | 1.0 |
| none | 0.0 |

### Demand weight

`W(s,t) = clip(station_mean / area_mean, 0.5, 2.0)`

여기서 station_mean은 동일 요일·시간대 대여량 평균이며,
area_mean은 해당 예측 요청에 포함된 유효 대여소의 동일 기준 평균이다.

입력값을 구할 수 없는 경우 중립값 1.0을 사용하고 warning을 남긴다.

### Priority score

`P(s) = D(s) × U(s) × W(s)`

### Supply slack

포화 위험 대여소에 대해서만 공급 후보로 사용한다.

`supply_slack = max(0, B_pred(s,h) - S_min(s))`

### Search distance

`estimated_distance = haversine_distance × DETOUR_FACTOR`

- SEARCH_RADIUS_KM = 2.0
- DETOUR_FACTOR = 1.3

### Move quantity

`move_qty = floor(min(remaining_shortage, supply_slack, vehicle_remaining))`

- VEHICLE_CAP = 20
- 한 번의 재배치 계획 전체에서 차량 잔여 적재량을 차감한다.

## 4. Greedy matching

부족 대여소는 priority score 내림차순으로 처리한다.

각 부족 대여소에 대해:

1. 2 km 이내 포화 대여소를 탐색한다.
2. 공급 후보를 공급여유 내림차순, 거리 오름차순으로 정렬한다.
3. 공급여유가 1대 미만인 후보는 제외한다.
4. 부족량, 공급여유, 차량 잔여용량 중 최솟값만큼 배정한다.
5. 정수 이동량만 허용한다.
6. 공급여유와 차량 잔여용량을 즉시 차감한다.
7. 차량용량이 소진되면 남은 부족 대여소는 미매칭 상태로 유지한다.

## 5. Guardrails

다음 입력은 예외로 전체 실행을 중단하지 않고 station 단위로 skip한다.

- capacity가 null, 0 또는 비정상
- 좌표가 없는 대여소
- 요청 horizon 예측값 누락
- bikes_expected가 0~capacity 범위를 벗어남
- S_min + E_min > capacity

추가 규칙:

- shortage와 saturation을 동시에 허용하지 않는다.
- 공급소가 자기 S_min 아래로 내려가도록 이동시키지 않는다.
- 공급여유가 1대 미만이면 이동 match를 생성하지 않는다.
- 재배치 계획 생성에는 미래 실제값을 사용하지 않는다.

## 6. Output

공개 운영자 응답:

- `base_time`
- `horizon_min`
- `shortage_top`
- `surplus_top`
- `move_matches`

내부 진단값:

- model_version
- shortage station count
- saturation station count
- move match count
- unmatched shortage count
- vehicle capacity used / remaining
- search radius
- detour factor
- area demand mean
- warnings

## 7. Smoke-test result

Synthetic test:

- base_time: 2026-10-08 08:00 KST
- evaluation horizon: 30 min
- demand station capacity: 20
- demand station B_pred(30): 2
- S_min: 4
- shortage: 2
- first shortage horizon: 30 min
- urgency: 2.0
- demand weight: 1.0
- priority score: 4.0

Supply station:

- B_pred(30): 19
- S_min: 4
- supply slack: 15
- estimated matching distance: 0.184 km

Generated matching:

`S-001 → D-001, move_qty = 2`

Vehicle result:

- capacity: 20
- used: 2
- remaining: 18
- warnings: 0

## 8. Test coverage

Week 06 unit tests cover:

- normal shortage / saturation / greedy matching
- invalid or zero capacity
- no supplier within 2 km
- supply slack below one bicycle
- vehicle capacity limit
- supplier ordering by supply slack
- incompatible S_min / E_min threshold
- demand-weight clipping and priority ordering

The Week 03–06 regression suite is also executed before PR submission.
