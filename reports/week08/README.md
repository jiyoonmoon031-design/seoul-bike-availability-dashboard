# Week 08 Recommendation Results

## Implemented

- ETA-based prediction interpolation
- origin recommendation scoring
- destination recommendation scoring
- distance score
- future availability score
- Top-3 ranking
- current / predicted inventory separation
- effective_horizon metadata
- smoke runner

## Parameters

| Parameter | Value |
|---|---:|
| MAX_WALK_M | 800 m |
| AVAIL_STABLE_TARGET | 3 |
| distance weight | 0.5 |
| availability weight | 0.5 |
| horizons | 15 / 30 / 60 min |

## Important rule

추천 점수는 현재 재고가 아니라 ETA 시점의 미래 예상 가용성을 사용한다.

Origin:

    bikes_expected(ETA)

Destination:

    docks_expected(ETA)

## Validation

- Week 08 unit tests: 9 passed
- origin smoke test: PASS
- destination smoke test: PASS
- ETA > 60 clamp: PASS

Actual full regression count should be recorded after the final test run.
