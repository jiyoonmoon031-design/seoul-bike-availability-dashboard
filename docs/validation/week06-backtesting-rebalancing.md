# Week 6 Backtesting and Rebalancing Evaluation Specification

Issue: #36

Owner: 김수연

Status: evaluation contract fixed; implementation input pending

## 1. Purpose

This document fixes a repeatable, leakage-safe backtesting structure and the
metrics used to compare station inventory risk before and after rebalancing.
It defines evaluation contracts only. It does not implement another owner's
forecasting or rebalancing algorithm.

## 2. Backtesting unit and time rules

The atomic evaluation unit is `run_id × base_time × horizon_min × station_id`.
Each run must use only information available at `base_time`.

- Supported horizons: 15, 30, and 60 minutes.
- Backtest timestamps advance in fixed 15-minute steps.
- Training data must end before the validation/test boundary, including the
  configured 60-minute gap.
- Weather and station snapshots must satisfy `observed_at <= base_time`.
- Rebalancing decisions are calculated once at `decision_time = base_time`.
- A vehicle moved at `decision_time` becomes effective only at
  `effective_time = decision_time + travel_minutes`.
- Actual future inventory is used only after a decision has been frozen.
- Runs must record code, model, data, configuration, and random-seed versions.

## 3. Required data structures

### 3.1 Backtest run

| Column | Type | Rule |
|---|---|---|
| `run_id` | string | unique and immutable |
| `created_at` | timestamp | run creation time |
| `window_start`, `window_end` | timestamp | inclusive evaluation window |
| `step_minutes` | integer | fixed at 15 |
| `horizons_minutes` | array[int] | `[15, 30, 60]` |
| `model_version` | string | final model identifier |
| `data_version` | string | input checksum or manifest version |
| `rebalancing_policy_version` | string | policy/config identifier |
| `code_revision` | string | Git commit SHA |
| `random_seed` | integer | reproducibility seed |

### 3.2 Frozen station prediction

| Column | Type | Rule |
|---|---|---|
| `run_id` | string | references the backtest run |
| `base_time` | timestamp | prediction decision time |
| `station_id` | string | station key |
| `horizon_min` | integer | 15, 30, or 60 |
| `bikes_now`, `capacity` | number | state known at `base_time` |
| `delta_net_pred` | number | predicted net inventory change |
| `bikes_expected` | number | clipped expected inventory |
| `docks_expected` | number | non-negative capacity-based indicator |
| `prediction_source` | string | `model` or `baseline_fallback` |
| `risk_score` | number | fixed score, descending priority |
| `is_shortage_risk`, `is_overflow_risk` | boolean | policy threshold result |

Uniqueness key: `run_id, base_time, station_id, horizon_min`.

### 3.3 Rebalancing decision and movement

| Column | Type | Rule |
|---|---|---|
| `decision_id` | string | unique and immutable |
| `run_id`, `base_time`, `horizon_min` | key | decision context |
| `source_station_id` | string | station giving bikes |
| `target_station_id` | string | station receiving bikes |
| `move_bikes` | integer | positive whole number |
| `distance_m`, `travel_minutes` | number | non-negative |
| `effective_time` | timestamp | no earlier than `base_time` |
| `rank` | integer | starts at 1; no duplicates per decision context |
| `risk_score_before` | number | source decision evidence |
| `policy_version` | string | policy/config identifier |

Hard constraints:

- `move_bikes <= source_bikes_available`.
- Source inventory must remain non-negative.
- Target inventory after the effective move must not exceed the chosen physical
  capacity policy.
- One physical bike cannot be assigned to multiple movements at the same time.
- Movements outside the service radius or fleet budget are rejected.

### 3.4 Evaluation outcome

| Column | Type | Rule |
|---|---|---|
| `run_id`, `base_time`, `station_id`, `horizon_min` | key | prediction join key |
| `actual_bikes` | number | observed only after the horizon |
| `bikes_without_rebalancing` | number | counterfactual baseline inventory |
| `bikes_with_rebalancing` | number | inventory after effective movements |
| `shortage_before`, `shortage_after` | boolean | inventory at or below shortage threshold |
| `overflow_before`, `overflow_after` | boolean | inventory at or above overflow threshold |
| `unmet_demand_before`, `unmet_demand_after` | number | non-negative lost rentals proxy |
| `unmet_return_before`, `unmet_return_after` | number | non-negative lost returns proxy |

Uniqueness key: `run_id, base_time, station_id, horizon_min`.

## 4. Metrics

Metrics are reported for ALL, ACTIVE, PEAK, and ACTIVE∩PEAK, then for each
horizon. Event counts use identical eligible rows before and after rebalancing.

| Metric | Formula | Direction |
|---|---|---|
| Shortage rate | `shortage events / eligible station-times` | lower |
| Overflow rate | `overflow events / eligible station-times` | lower |
| Shortage reduction | `(shortage_before - shortage_after) / shortage_before` | higher |
| Overflow reduction | `(overflow_before - overflow_after) / overflow_before` | higher |
| Unmet-demand reduction | `(unmet_demand_before - unmet_demand_after) / unmet_demand_before` | higher |
| Unmet-return reduction | `(unmet_return_before - unmet_return_after) / unmet_return_before` | higher |
| Protected station-times | count changing from risky before to safe after | higher |
| Harmed station-times | count changing from safe before to risky after | lower |
| Net protected station-times | protected minus harmed | higher |
| Bikes moved | sum of `move_bikes` | context |
| Efficiency | `net protected station-times / bikes moved` | higher |
| Movement distance | sum of `distance_m × move_bikes` | lower |
| Feasible decision rate | feasible decisions / proposed decisions | higher |

If a denominator is zero, the ratio is recorded as null with its numerator and
denominator; it is never replaced with zero. Results include bootstrap 95%
confidence intervals sampled by service date so within-day dependence is kept.

## 5. Acceptance criteria

- Shortage reduction is at least 10%.
- Overflow reduction is at least 10%.
- Harmed station-times do not exceed protected station-times.
- Feasible decision rate is 100%; any capacity, inventory, duplicate-bike, or
  timing violation fails the run.
- All configured timestamps produce output, or missing timestamps are listed
  with an explicit reason.
- Re-running the same versioned inputs and seed produces identical decisions
  and aggregate metrics.

The 10% thresholds come from `config/params.yaml` and remain provisional until
an operational owner approves fleet, distance, and travel-time constraints.

## 6. Required outputs

- `backtest_runs.json`: run metadata and versions.
- `backtest_predictions.parquet`: frozen station predictions.
- `rebalancing_decisions.parquet`: proposed and effective movements.
- `rebalancing_outcomes.parquet`: station-time counterfactual outcomes.
- `rebalancing_metrics.csv`: segment/horizon aggregate metrics with counts and
  confidence intervals.
- `rebalancing_validation.json`: uniqueness, leakage, feasibility, and
  reproducibility checks.

Large row-level files stay outside Git. Schemas, aggregate metrics, validation
summaries, and figures may be committed after review.

## 7. Validation checklist

1. Verify required columns, types, unique keys, and non-negative quantities.
2. Reject observations or features recorded after `base_time`.
3. Verify movement effectiveness occurs after travel time.
4. Recompute all before/after flags from the row-level outcomes.
5. Recompute aggregate metrics independently from the stored outcome table.
6. Compare repeat runs with identical versions and seed.
7. Report ALL and high-risk segments separately to avoid hiding local harm.
