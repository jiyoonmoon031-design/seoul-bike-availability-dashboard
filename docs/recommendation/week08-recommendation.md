# Week 08 User Station Recommendation

## Owner

Moon Jiyoon

## Purpose

현재 재고가 아니라 사용자가 실제 대여소에 도착할 미래 시점의
예상 가용성을 이용하여 출발/도착 대여소를 추천한다.

## Horizon mapping

Prediction delta anchors:

- 0 min: delta = 0
- 15 min: delta_15
- 30 min: delta_30
- 60 min: delta_60

ETA가 anchor 사이에 위치하면 선형보간한다.

ETA > 60분이면 60분 prediction을 clamp한다.

## Origin recommendation

출발 추천에서는 미래 예상 자전거 수를 사용한다.

    bikes_expected(ETA)
      = clip(
          bikes_now + interpolated_delta(ETA),
          0,
          capacity
        )

## Destination recommendation

도착 추천에서는 미래 예상 빈 거치대 수를 사용한다.

    docks_expected(ETA)
      = capacity - bikes_expected(ETA)

## Score

    distance_score
      = 1 - min(distance_m / MAX_WALK_M, 1)

    availability_score
      = min(
          expected_available / AVAIL_STABLE_TARGET,
          1
        )

    score
      = 0.5 * distance_score
      + 0.5 * availability_score

Current parameters:

- MAX_WALK_M = 800
- AVAIL_STABLE_TARGET = 3
- distance weight = 0.5
- availability weight = 0.5

## Current vs predicted inventory

현재 재고와 미래 예측 재고를 같은 값으로 취급하지 않는다.

Frontend primary display:

- origin: bikes_expected
- destination: docks_expected

Secondary information:

- bikes_now
- docks_now

## Output

- leg
- eta_min
- effective_horizon
- recommendations
- rank
- station_id
- station_name
- distance_m
- walk_min
- bikes_now
- docks_now
- bikes_expected
- docks_expected
- score
- score_breakdown

## Verification

Required tests:

- 0-15 interpolation
- 15-30 interpolation
- ETA > 60 clamp
- origin uses future bikes
- destination uses future docks
- 800m distance boundary
- availability score cap
- Top-3 ordering
- incomplete prediction warning
