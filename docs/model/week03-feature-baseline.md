# Week 03 Feature Engineering and Naive Baseline

## Status and ownership

- Related Issue: #26
- Owner: 문지윤
- Scope: feature engineering and naive baseline only
- Input contract: Week 02 `station_id × base_time` 15-minute table
- Review required: 김수연 or 조성은

The real-time station collector and persistence layer remain 조성은's work.
Independent leakage and data-quality approval remains 김수연's work. This
implementation supplies testable checks but does not self-approve those tasks.

## Preserved Week 01-02 contracts

- Service/model scope is 광진구 and 성동구 only.
- `station_id` remains a string.
- One row is `station_id × base_time`.
- Base intervals are 15-minute `[t, t+15m)` windows.
- Targets are future net inventory changes:
  `delta_hist_h{h} = returns - rentals during [t, t+h)`.
- A missing source interval remains missing and is never filled as zero demand.
- AWS 421 weather is joined as-of: `weather_obs_time <= base_time`, with a
  maximum age of 60 minutes.
- Model and backend request/response fields are unchanged.

## Prediction-time boundary

At prediction base time `t`, the Week 02 row's `rent_count`, `return_count`, and
`delta_hist` describe `[t, t+15m)`. They are therefore future information.

The Week 03 feature code starts historical activity at `shift(1)`:

```text
rent_prev_15m(t) = rentals during [t-15m, t)
rent_prev_30m(t) = rentals during [t-30m, t)
rent_prev_60m(t) = rentals during [t-60m, t)
```

The same rule applies to return and delta features. A window is available only
when every required 15-minute source interval is observed and continuous.

The enriched parquet retains current activity, target, and validity columns for
audit/evaluation. They are deliberately excluded from
`get_model_feature_columns()` and marked as `audit_only` or `target` in the
generated manifest. Future model training must use this allowlist rather than
selecting every numeric column.

## Feature definitions

### Identity and station context

- `station_id`
- `district`
- `capacity`, only when an upstream table supplies it

No station-population reconciliation or capacity imputation is performed here.

### Time and calendar

- `hour`, `minute`, `weekday_index`, `month`, `day_of_year`
- `is_weekend`, `is_holiday`, `is_peak`, `is_holiday_or_weekend`
- cyclic time-of-day and weekday sine/cosine values

`is_weekend` and `is_peak` are checked against `base_time`; conflicting source
values fail the build.

### Historical activity

- previous 15/30/60-minute rent, return, and net-delta sums
- availability flag for each history window
- complete previous-24-hour rent, return, and delta means
- previous-24-hour observation count and availability flag
- exact previous-day and previous-week net-delta lags and availability flags

The 24-hour aggregates require all 96 prior 15-minute intervals. This avoids
hiding a missing source period inside a partial average.

### Weather

When present, the allowlist includes temperature, precipitation, humidity,
wind, weather age, availability, and explicit missingness flags. The build fails
if a non-421 station or a weather observation later than `base_time` is found.
Weather values are not silently imputed.

## Naive baselines

The primary persistence baseline follows the pre-registered Week 01 evaluation
contract:

```text
prediction_persistence(station, t, h)
  = delta_hist_h(station, t-h)
```

The prior target window ends exactly at `t`, so it is available without using
the future target `[t, t+h)`. A prediction is missing if that prior window was
not fully observed or is not timestamp-continuous.

The secondary baseline always predicts zero net change. It is reported for
context but does not replace persistence as the main comparison baseline.

## Chronological evaluation

Values come from `config/params.yaml`:

- test: most recent 28 complete source days
- validation: preceding 14 complete source days
- train: earlier complete source days
- minimum train history: 90 complete days
- ACTIVE: stations at or above the train-only 75th activity percentile

Incomplete source dates receive `split=excluded`. Metrics are MAE and RMSE for
15/30/60 minutes and the combined micro average, reported for:

- `ALL`
- `ACTIVE`
- `PEAK`
- `ACTIVE_PEAK` (`ACTIVE ∩ PEAK`)

The test split is evaluated only to establish the fixed naive reference. Model
selection and threshold tuning must continue to use train/validation only.

## Reproducible execution

Build the enriched feature table and column-role manifest:

```bash
python scripts/build_week03_features.py \
  --input /path/to/trip_targets_weather_15_30_60.parquet \
  --output /path/to/week03_features.parquet
```

Run naive baseline evaluation:

```bash
python scripts/run_week03_naive_baseline.py \
  --input /path/to/week03_features.parquet \
  --params config/params.yaml \
  --metrics-output reports/week03/naive_baseline_metrics.csv
```

`--allow-short-history` exists only for smoke tests on small samples. It must not
be used for an official baseline report.

Large feature and prediction parquet files stay outside Git. Commit only code,
the compact manifest/summary/metric outputs, and documentation.

## Validation handoff

The independent reviewer should verify:

1. current-window activity and future targets are absent from the feature
   allowlist;
2. historical windows stop at `base_time`;
3. source-missing dates remain excluded rather than becoming zero activity;
4. weather timestamps never exceed `base_time`;
5. ACTIVE threshold uses train data only;
6. persistence uses the target window ending exactly at `base_time`;
7. the 15/30/60-minute and micro metrics reproduce from the documented CLI.
