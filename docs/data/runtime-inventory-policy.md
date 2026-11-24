# Runtime inventory policy

Status: implemented for runtime prediction, recommendation and rebalancing.
Historical Week 05–11 training and backtesting contracts are unchanged.

## Source semantics

The Seoul Open Data API documents `rackTotCnt` as **거치대개수** and
`parkingBikeTotCnt` as **자전거주차총건수**. The API does not state that the
second value is always less than or equal to the first. Runtime code therefore
stores these as separate facts:

- `registered_capacity`: the API `rackTotCnt` value.
- `observed_inventory`: the API `parkingBikeTotCnt` value.
- `overflow_bikes = max(0, observed_inventory - registered_capacity)`.
- `available_docks_now = max(0, registered_capacity - observed_inventory)`.

Official contract:
<https://data.seoul.go.kr/dataList/OA-15493/A/1/datasetView.do>

An overflow observation is usable for rentals and rebalancing. It is not used
as evidence that additional returns are possible. Available docks never become
negative.

## Validation and freshness

Runtime observations are classified independently per station:

| Status | Usable | Warning |
|---|---:|---|
| valid, including zero/full | yes | none |
| overflow | yes | `INVENTORY_OVER_CAPACITY` |
| missing station | no | `MISSING_INVENTORY` |
| invalid/negative inventory | no | `INVALID_INVENTORY` |
| missing/non-positive capacity | no | `INVALID_CAPACITY` |
| invalid timestamp | no | `INVALID_INVENTORY_TIMESTAMP` |
| missing required timestamp | no | `MISSING_INVENTORY_TIMESTAMP` |
| older than 15 minutes | no | `STALE_INVENTORY` |

Timestamp checks are enforced when the upstream observation includes a
timestamp. Callers that require realtime freshness must also require the
timestamp. ST-1760's 2026-09-13 snapshot must not be substituted for a current
observation.

## Projection rule

Runtime projections use a ceiling of
`max(registered_capacity, observed_inventory_at_request)`:

```text
bikes_expected = clip(observed_inventory + delta_net,
                      0,
                      max(registered_capacity, observed_inventory))
docks_expected = max(0, registered_capacity - bikes_expected)
overflow_expected = max(0, bikes_expected - registered_capacity)
```

This preserves a real overflow already observed while preventing the forecast
from inventing a larger overflow. The historical feature table, model training,
holdout evaluation and backtesting continue to use their original registered
capacity clipping policy.

## Interface changes requiring team review

Prediction and recommendation records retain `capacity` and `bikes_now` for
compatibility and add the explicit fields below:

- `registered_capacity`
- `observed_inventory`
- `overflow_bikes` / `overflow_now`
- `available_docks_now`
- `inventory_collected_at`
- `inventory_source`
- `inventory_status`
- `overflow_expected`

The distinction between registered racks and observed parked bicycles, and the
runtime projection ceiling, are intentionally recorded for reviewer approval.
