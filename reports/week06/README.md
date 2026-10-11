# Week 06 Rebalancing Results

## Scope

Week 05 최종 모델의 미래 예상 재고를 이용하여 운영자용 부족·포화 위험과
greedy 재배치 권고를 생성하는 로직을 구현하였다.

## Implementation

- src/rebalancing/logic.py
- scripts/run_week06_rebalancing.py
- tests/test_week06_rebalancing.py

## Parameters

- S_min ratio: 0.20
- E_min ratio: 0.20
- Demand weight range: 0.5 ~ 2.0
- Search radius: 2.0 km
- Detour factor: 1.3
- Vehicle capacity: 20
- Urgency: 15m=4.0, 30m=2.0, 60m=1.0

## Synthetic Smoke Test

30분 horizon 기준 결과:

- demand station: D-001
- bikes_expected: 2
- S_min: 4
- shortage: 2
- urgency: 2.0
- demand weight: 1.0
- priority score: 4.0
- supplier: S-001
- supply slack: 15
- estimated distance: 0.184 km
- recommended movement: S-001 -> D-001, 2 bikes
- vehicle capacity used: 2 / 20
- warnings: 0

## Verification

- Week 06 unit tests: 8 passed
- Week 03-06 regression tests: 27 passed
- pre-commit: PASS
- synthetic smoke test: PASS

The synthetic smoke test validates algorithm behavior only. It is not an
effectiveness evaluation. Rebalancing effectiveness will be evaluated later
against actual holdout counterfactual inventory.
