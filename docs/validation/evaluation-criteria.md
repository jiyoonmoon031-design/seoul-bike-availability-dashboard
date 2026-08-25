# Evaluation Metrics and Validation Criteria

## Status

- Week: Week 01
- Related issue: #6
- Status: Pre-registered before model test results
- Scope: 광진구·성동구, 15/30/60분 예측

이 문서는 모델 및 서비스 결과를 확인하기 전에 평가 방법과 합격 기준을 고정한다. 결과 확인 후 기준을 변경하지 않으며, 기준 변경이 불가피하면 변경 사유와 영향 범위를 별도 이슈와 PR에 기록하고 기존 기준 결과도 함께 보고한다.

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

`ACTIVE` 경계값은 test를 보지 않고 train 데이터에서만 계산한다. 동률인 대여소는 모두 포함한다.

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

합격 기준:

- `ALL` 전체 horizon micro MAE 개선율이 10% 이상이어야 한다.
- 각 horizon의 `ALL` MAE와 RMSE가 각각 persistence baseline보다 낮아야 한다.
- `ACTIVE`, `PEAK`, `ACTIVE ∩ PEAK`의 MAE 개선율을 공개하며, 어느 segment도 음수이면 원인 분석을 남긴다.

## 4. Availability classification

대여 가능 여부를 양성(`1`)으로 정의한다.

```text
actual positive    = actual bikes at t+h >= AVAIL_MIN
predicted positive = bikes_expected at t+h >= AVAIL_STABLE
```

`TP`, `FP`, `FN`은 각각 true positive, false positive, false negative 수다.

```text
Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
F1        = 2 × Precision × Recall / (Precision + Recall)
```

분모가 0인 지표는 0으로 임의 대체하지 않고 `N/A`로 보고한다.

`ALL` 전체 horizon micro 기준 합격선:

| Metric | Minimum |
|---|---:|
| Availability Precision | 0.80 |
| Availability Recall | 0.85 |
| Availability F1 | 0.80 |

horizon 및 segment별 값도 별도로 공개한다.

## 5. Top-3 availability hit rate

추천 요청 `q`에 대해 추천된 최대 3개 대여소 중 목표 시각에 실제 자전거가 `AVAIL_MIN`대 이상인 대여소가 하나 이상 있으면 hit로 판정한다.

```text
hit(q) = 1 if any(actual_bikes(s, t+h) >= AVAIL_MIN for s in Top3(q)) else 0

Top-3 hit rate = Σ hit(q) / number of eligible requests
```

- 추천 후보가 3개 미만이면 반환된 전체 후보로 평가한다.
- 추천 후보가 0개이면 miss로 계산한다.
- `ALL` 전체 horizon micro hit rate 합격선은 0.90이다.
- horizon 및 segment별 hit rate도 공개한다.

## 6. Rebalancing shortage-score reduction

대여소 `s`와 horizon `h`의 부족량을 다음과 같이 정의한다.

```text
shortage(s, h) = max(0, S_MIN(s) - bikes_expected(s, h))
total shortage score = Σ urgency(h) × demand_weight(s) × shortage(s, h)

reduction
= (score_before - score_after) / score_before
```

- `score_before=0`인 경우는 감소시킬 부족이 없으므로 `N/A`로 보고하고 평균 분모에서 제외한다.
- `score_after`는 추천 이동량을 적용하되 `capacity`, 공급여유, `VEHICLE_CAP` 제약을 모두 적용해 계산한다.
- 전체 평가 사건의 합산 score 기준 감소율 합격선은 0.10이다.
- 재배치로 새롭게 부족 상태가 된 공급 대여소가 있으면 합격 처리하지 않는다.

## 7. Acceptance summary

다음 조건을 모두 충족해야 최종 모델·서비스 검증을 통과한다.

| Area | Criterion |
|---|---|
| Forecast | ALL micro MAE가 persistence baseline 대비 10% 이상 개선 |
| Forecast guardrail | 각 horizon ALL MAE/RMSE가 baseline보다 낮음 |
| Availability | Precision ≥ 0.80, Recall ≥ 0.85, F1 ≥ 0.80 |
| Recommendation | Top-3 availability hit rate ≥ 0.90 |
| Rebalancing | Aggregate shortage-score reduction ≥ 0.10 |
| Reporting | ALL / ACTIVE / PEAK / ACTIVE ∩ PEAK 결과 및 제외율 공개 |

하나라도 충족하지 못하면 결과를 숨기거나 기준을 낮추지 않고 실패 항목과 원인을 기록한 뒤 새로운 모델 버전으로 다시 평가한다.

## 8. Required evaluation output

평가 결과에는 최소한 다음 메타데이터를 포함한다.

- model version and git commit
- train/validation/test 시작·종료 시각
- 대상 대여소 수와 표본 수
- horizon 및 segment
- metric 값과 baseline 값
- 결측·중복·개입 의심으로 제외한 건수와 비율
- 사용한 `config/params.yaml` 사본 또는 hash

이 정보가 없으면 동일한 평가를 재현할 수 없으므로 공식 결과로 인정하지 않는다.
