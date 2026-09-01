# Evaluation Metrics and Validation Criteria

## Status

- Week: Week 01
- Related issue: #6
- Status: Pre-registered before model test results
- Scope: 광진구·성동구, 15/30/60분 예측

이 문서는 모델 및 서비스 결과를 확인하기 전에 평가 방법과 기준을 고정한다. 결과 확인 후 기준을 변경하지 않으며, 기준 변경이 불가피하면 변경 사유와 영향 범위를 별도 이슈와 PR에 기록하고 기존 기준 결과도 함께 보고한다. 현재 절대 수치 기준은 실증 근거가 쌓이기 전의 `provisional target`이며 정식 운영 release gate와 구분한다.

## 1. Evaluation data

### 1.1 Ground truth

기존 모델-백엔드 인터페이스에 따라 목적별 실제값을 구분한다.

| Purpose | Ground truth | Source |
|---|---|---|
| Forecast model comparison | `delta_hist = return_count - rent_count` | 대여·반납 이용이력 |
| Real inventory and recommendation | `delta_snap = B(t+h) - B(t)` | 자체 수집 실시간 재고 snapshot |
| Availability | `B(t+h)` and `capacity - B(t+h)` | 자체 수집 실시간 재고 snapshot |

모든 평가는 광진구·성동구 대여소와 15/30/60분 horizon을 대상으로 한다. horizon별 결과와 전체 micro average를 모두 보고한다.

### 1.2 Chronological split

무작위 분할로 미래 정보가 학습 데이터에 섞이지 않도록 시간순으로 분할한다.

```text
test       = 가장 최근 28개 완결 일
validation = test 직전 14개 완결 일
train      = validation 이전 자료
```

- 최초 최종평가에는 test 시작 전 최소 90일의 이력이 있어야 한다.
- 모델 선택과 threshold 조정은 train/validation에서만 수행한다.
- test는 최종 모델과 기준이 고정된 후 한 번 평가한다.
- 동일 timestamp와 station의 중복은 하나만 남기고, 필수 실제값이 없는 행은 해당 지표의 분모에서 제외한다.
- 제외 건수와 제외율을 지표와 함께 공개한다.

### 1.3 Snapshot rules

- 스냅샷 간격은 `SNAPSHOT_INTERVAL_MIN`을 따른다.
- 목표 시각의 정확한 스냅샷이 없으면 목표 시각 기준 ±2분 30초 내 가장 가까운 값을 사용한다.
- 허용 범위에 스냅샷이 없으면 해당 표본을 제외한다.
- `abs(delta_snap - delta_hist) >= INTERVENTION_THRESHOLD`인 재배치 개입 의심 표본은 순수 수요 예측 MAE/RMSE에서는 제외하고, 서비스 가용성 평가는 실제 운영 상황을 반영하기 위해 포함한다.

## 2. Segments

모든 핵심 지표는 다음 네 segment로 분리해 보고한다.

| Segment | Definition |
|---|---|
| `ALL` | 평가 가능한 전체 대여소·시간 표본 |
| `ACTIVE` | train 기간의 대여+반납 건수가 75백분위 이상인 상위 25% 대여소 |
| `PEAK` | KST 07:00~09:00 또는 18:00~20:00에 예측을 시작한 표본 |
| `ACTIVE ∩ PEAK` | `ACTIVE` 대여소이면서 `PEAK` 시간인 표본 |

`ACTIVE` 경계값은 test를 보지 않고 train 데이터에서만 계산한다. 동률인 대여소는 모두 포함한다. 상위 25%는 전체 평균에 가려질 수 있는 고수요 대여소 성능을 보면서도 충분한 표본을 유지하기 위한 사전 운영 기준이다. 민감도 분석에서는 50/75/90백분위를 함께 보고하되, 75백분위인 주 분석 정의는 test 결과에 따라 바꾸지 않는다.

## 3. Forecast metrics

표본 `i`의 실제 순재고 변화량을 `y_i`, 예측값을 `ŷ_i`, 평가 표본 수를 `N`이라 한다.

### 3.1 MAE

```text
MAE = (1/N) × Σ |y_i - ŷ_i|
```

평균적으로 예측이 실제 자전거 수 변화와 몇 대 차이 나는지 나타낸다. 낮을수록 좋다.

### 3.2 RMSE

```text
RMSE = sqrt((1/N) × Σ(y_i - ŷ_i)²)
```

큰 오차에 더 큰 불이익을 준다. 낮을수록 좋다.

### 3.3 Naive baseline and improvement

주 baseline은 동일 대여소·동일 horizon의 직전 관측 순재고 변화량을 그대로 예측하는 persistence 방식이다.

```text
ŷ_baseline(station, t, h) = delta_hist(station, t-h, h)

MAE improvement
= (MAE_baseline - MAE_model) / MAE_baseline
```

보조 비교로 `ŷ=0` baseline도 함께 보고하되 합격 판정에는 persistence baseline을 사용한다.

사전 목표:

- `ALL` 전체 horizon micro MAE 개선율이 10% 이상이어야 한다.
- 각 horizon의 `ALL` MAE와 RMSE가 각각 persistence baseline보다 낮아야 한다.
- `ACTIVE`, `PEAK`, `ACTIVE ∩ PEAK`의 MAE 개선율을 공개하며, 어느 segment도 음수이면 원인 분석을 남긴다.

## 4. Availability classification

모델 자체의 분류 성능과 서비스의 보수적 노출 정책을 분리한다.

모델 분류 지표에서는 실제값과 예측값에 동일한 `AVAIL_MIN` 경계를 사용한다.

```text
actual positive    = actual bikes at t+h >= AVAIL_MIN
predicted positive = bikes_expected at t+h >= AVAIL_MIN
```

`TP`, `FP`, `FN`은 각각 true positive, false positive, false negative 수다.

```text
Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
F1        = 2 × Precision × Recall / (Precision + Recall)
```

분모가 0인 지표는 0으로 임의 대체하지 않고 `N/A`로 보고한다.

서비스 정책 평가는 별도로 `bikes_expected >= AVAIL_STABLE`일 때만 사용자에게 안정 가용 대여소로 노출하고, 이 정책의 Precision/Recall/F1을 `conservative_policy_*` 이름으로 보고한다. `AVAIL_STABLE`은 분류 모델의 판정 경계가 아니라 품절 위험을 줄이는 안전 여유다.

`ALL` 전체 horizon micro provisional target:

| Metric | Minimum |
|---|---:|
| Availability Precision | 0.80 |
| Availability Recall | 0.85 |
| Availability F1 | 0.80 |

horizon 및 segment별 값도 별도로 공개한다.

## 5. Top-3 availability hit rate

대여와 반납은 필요한 자원이 다르므로 별도 지표로 평가한다.

```text
rent_hit(q)
= 1 if any(actual_bikes(s, t+h) >= AVAIL_MIN for s in RentTop3(q)) else 0

return_hit(q)
= 1 if any(actual_empty_docks(s, t+h) >= 1 for s in ReturnTop3(q)) else 0

Rent Top-3 hit rate   = Σ rent_hit(q) / number of eligible rent requests
Return Top-3 hit rate = Σ return_hit(q) / number of eligible return requests
```

- 두 지표 모두 `ALL` 전체 horizon micro provisional target은 0.90이다.
- 추천 후보가 3개 미만이면 반환된 전체 후보로 평가하고, 후보가 0개이면 miss로 계산한다.
- horizon 및 segment별 대여/반납 hit rate를 각각 공개한다.

### 5.1 Reproducible request set

test 구간이 확정되면 다음 규칙으로 요청 집합을 한 번 생성하고 파일 hash와 함께 보존한다.

1. KST 기준 매 15분 정각의 유효한 snapshot을 요청 시각 `t`로 사용한다.
2. 해당 시각에 신선도 기준을 통과한 광진·성동의 각 대여소 좌표를 요청 좌표로 사용한다.
3. 각 요청 좌표마다 `h ∈ {15, 30, 60}`과 `mode ∈ {rent, return}` 조합을 생성한다.
4. 요청 시점에 유효한 station master에서 운영 중이고 좌표·capacity가 있으며 `SEARCH_RADIUS_KM` 안에 있는 대여소를 후보로 한다.
5. 추천 알고리즘에는 시각 `t`까지 이용 가능한 정보만 제공한다. `t+h` 실제값은 hit 판정에만 사용한다.
6. 요청 ID는 `timestamp|origin_station_id|horizon|mode`로 고정하고, station master 버전·요청 수·제외 사유를 결과와 함께 저장한다.

## 6. Rebalancing shortage and overflow reduction

예측값으로 계획을 만든 뒤 같은 예측값으로 효과를 평가하는 순환 평가를 금지한다. 재배치 계획은 시각 `t`까지의 정보와 모델 예측으로 생성하되, 효과는 holdout의 실제 변화량으로 계산한 counterfactual inventory에서 평가한다.

```text
B_actual_before(s, t+h)
= clip(B_actual(s, t) + delta_actual(s, t, h), 0, capacity(s))

B_actual_after(s, t+h)
= clip(B_actual(s, t) + signed_move(s, t) + delta_actual(s, t, h),
       0, capacity(s))

delta_actual = delta_snap when a valid snapshot pair exists,
               otherwise delta_hist

shortage(B) = max(0, S_MIN(s) - B)
overflow(B) = max(0, E_MIN(s) - (capacity(s) - B))

shortage_score = Σ urgency(h) × demand_weight(s) × shortage(B)
overflow_score = Σ urgency(h) × demand_weight(s) × overflow(B)

shortage_reduction
= (shortage_score_before - shortage_score_after) / shortage_score_before

overflow_reduction
= (overflow_score_before - overflow_score_after) / overflow_score_before
```

- `signed_move`는 유입이면 양수, 유출이면 음수이며 모든 대여소의 합은 0이어야 한다.
- 계획 생성 시점에는 미래 `delta_actual`을 사용할 수 없고 이동량에는 `capacity`, 공급여유, `VEHICLE_CAP` 제약을 적용한다.
- 각 before score가 0이면 해당 감소율을 `N/A`로 보고 그 지표의 집계 분모에서 제외한다.
- shortage와 overflow 감소율을 서로 상쇄하지 않고 각각 보고하며 두 provisional target은 각각 0.10이다.
- 재배치 때문에 실제 counterfactual에서 새 부족 또는 새 포화 상태가 생기면 해당 사건을 guardrail 실패로 기록한다.
- `delta_snap` 사용률과 `delta_hist` fallback 사용률을 함께 공개한다.

## 7. Criteria status and rationale

현재 실제 운영 데이터와 사용자 실패 비용 추정치가 없으므로 절대 수치는 정식 합격선이 아닌 사전 engineering target이다. 0.80 수준의 분류 목표는 오류가 5건 중 1건을 넘지 않게 하려는 초기 기준이고, Recall 0.85는 대여 가능 사례 누락을 상대적으로 더 엄격히 제한한다. Top-3 0.90은 사용자 요청 10건 중 9건에서 최소 한 후보를 확보하려는 서비스 목표다. 재배치 0.10은 개입 비용을 들일 최소 효과 크기로 설정한 초기 목표다. 이 근거들은 가설이며 사용자 조사·운영비 자료로 교정하기 전까지 `provisional` 상태를 유지한다.

baseline 대비 개선 여부와 결과 공개 규칙은 즉시 적용하는 평가 계약이고, 절대 수치는 목표 달성 여부를 보고하되 단독 release gate로 사용하지 않는다.

| Area | Criterion | Status |
|---|---|---|
| Forecast | ALL micro MAE가 persistence baseline 대비 10% 이상 개선 | Provisional target |
| Forecast guardrail | 각 horizon ALL MAE/RMSE가 baseline보다 낮음 | Required |
| Availability | Precision ≥ 0.80, Recall ≥ 0.85, F1 ≥ 0.80 | Provisional target |
| Recommendation | Rent/Return Top-3 hit rate 각각 ≥ 0.90 | Provisional target |
| Rebalancing | 실제 holdout counterfactual의 shortage/overflow 감소율 각각 ≥ 0.10 | Provisional target |
| Rebalancing guardrail | 새 부족 또는 새 포화 상태를 만들지 않음 | Required |
| Reporting | ALL / ACTIVE / PEAK / ACTIVE ∩ PEAK 결과 및 제외율 공개 | Required |

목표를 충족하지 못해도 결과를 숨기거나 기준을 낮추지 않는다. 미달 항목과 원인을 기록하고 새로운 모델 버전으로 다시 평가한다. 정식 release gate 승격은 test 결과를 보고 임의로 결정하지 않고 별도 이슈에서 근거 데이터와 함께 승인한다.

## 8. Required evaluation output

평가 결과에는 최소한 다음 메타데이터를 포함한다.

- model version and git commit
- train/validation/test 시작·종료 시각
- 대상 대여소 수와 표본 수
- horizon 및 segment
- metric 값과 baseline 값
- 대여/반납 Top-3 요청 집합 파일 hash와 생성 규칙 버전
- 재배치 `delta_snap`/`delta_hist` 사용률 및 guardrail 실패 건수
- 결측·중복·개입 의심으로 제외한 건수와 비율
- 사용한 `config/params.yaml` 사본 또는 hash

이 정보가 없으면 동일한 평가를 재현할 수 없으므로 공식 결과로 인정하지 않는다.
