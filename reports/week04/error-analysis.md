# Week 04 Validation Error Analysis

Related issue: #33

## Inputs and integrity

- Prediction file: `week04_validation_predictions.parquet`
- Rows: 955,628
- SHA-256: `a826edb4df2850ac4cc94a2a372da1fd476c4e3b8549bfdf19869d033675a077`
- Source commit: `d6f9543583a8c490e02038a0eee2508d203e050b`
- Active-station threshold: 28,428 train activities
- Active stations: 47

The prediction file was stored outside Git and matched the shared checksum.

## Overall residual distribution

Residual is defined as `prediction - target`. A negative value is an underprediction and a positive value is an overprediction.

| Model | Horizon | MAE | RMSE | Mean residual | 5% residual | 95% residual |
|---|---:|---:|---:|---:|---:|---:|
| LightGBM | 15 | 0.659 | 1.243 | +0.006 | -2.000 | +2.000 |
| LightGBM | 30 | 1.031 | 1.808 | +0.016 | -2.950 | +2.982 |
| LightGBM | 60 | 1.583 | 2.694 | +0.010 | -3.997 | +4.000 |
| Random Forest | 15 | 0.682 | 1.222 | +0.003 | -1.970 | +1.969 |
| Random Forest | 30 | 1.045 | 1.770 | +0.007 | -2.751 | +2.796 |
| Random Forest | 60 | 1.579 | 2.609 | +0.012 | -3.936 | +3.976 |

Mean residuals are close to zero in ALL, so there is no material global directional bias. Error magnitude increases with horizon. Random Forest has the lower 60-minute tail spread and RMSE, while LightGBM has lower 15- and 30-minute MAE.

## Segment characteristics

Random Forest MAE rises from 0.682/1.045/1.579 in ALL to 1.548/2.327/3.537 in ACTIVE_PEAK for 15/30/60 minutes. The ACTIVE_PEAK mean residuals are -0.023, -0.050, and -0.097, indicating a small underprediction tendency during the busiest combined segment.

LightGBM shows the same concentration of error. ACTIVE_PEAK MAE is 1.546/2.361/3.679 and its 60-minute mean residual is -0.221. This is a larger busy-period underprediction bias than Random Forest at the longest horizon.

## Time-of-day characteristics

Random Forest's highest-MAE hours are concentrated around the commute peaks:

| Horizon | Highest-MAE hours |
|---|---|
| 15 minutes | 18:00, 17:00, 08:00 |
| 30 minutes | 18:00, 17:00, 08:00 |
| 60 minutes | 17:00, 18:00, 08:00 |

At 60 minutes, Random Forest MAE reaches 2.745 at 17:00, compared with the ALL average of 1.579.

## Station characteristics

The highest Random Forest station-level MAE is consistently concentrated in `ST-99`, `ST-3390`, and `ST-1660`. For `ST-99`, MAE grows from 1.853 at 15 minutes to 4.078 at 60 minutes.

The largest individual cases are demand shocks that tree models strongly shrink toward typical values:

| Horizon | Station/time | Target | RF prediction | Absolute error |
|---|---|---:|---:|---:|
| 15 | ST-99, 2026-05-01 19:15 | +40 | +1.232 | 38.768 |
| 30 | ST-483, 2026-04-25 20:45 | -49 | +1.776 | 50.776 |
| 60 | ST-483, 2026-04-25 20:45 | -71 | +4.308 | 75.308 |

These cases should be treated as rare station-time shocks, not as evidence of general bias. Operational monitoring should flag extreme recent activity and consider fallback or uncertainty messaging when predicted demand is far outside the training regime.

## Outputs

- `error-analysis/residual_summary.csv`
- `error-analysis/residual_by_segment.csv`
- `error-analysis/residual_by_hour.csv`
- `error-analysis/residual_by_station.csv`
- `error-analysis/worst_cases.csv`
- `scripts/analyze_week04_validation_errors.py`

## Conclusion

Issue #33's remaining error-distribution scope is complete. The analysis confirms low overall directional bias but materially higher errors at longer horizons, peak/active combinations, commute hours, and a small set of high-volume stations. Extreme shocks remain the primary worst-case failure mode.
