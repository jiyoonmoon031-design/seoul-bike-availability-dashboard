# Week 04 Model Comparison Results

## Run status

- Related Issue: #49
- Owner: Moon Jiyoon
- Input period: 2025-08-01 00:00 through 2026-07-31 23:45
- Input rows / stations: 6,377,643 / 185
- Input SHA-256: `e1c94933347c27ef80bb4dc8a774960497ec6de94455cc195266aefd551e5202`
- Ordered Week 03 features: 46
- Seed: 42
- Evaluation: validation only
- Final test: preserved for Week 05; no test metrics generated

## Chronological split

Ratios apply to timestamps retained after the two 60-minute purge gaps.

| Partition | Start | End | Unique timestamps | Rows |
|---|---|---|---:|---:|
| Train | 2025-08-01 00:00 | 2026-04-13 10:15 | 24,522 | 4,470,108 |
| Train→validation gap | 2026-04-13 10:30 | 2026-04-13 11:15 | 4 | included in 1,452 excluded rows |
| Validation | 2026-04-13 11:30 | 2026-06-07 04:45 | 5,254 | 955,628 |
| Validation→test gap | 2026-06-07 05:00 | 2026-06-07 05:45 | 4 | included in 1,452 excluded rows |
| Reserved test | 2026-06-07 06:00 | 2026-07-31 23:45 | 5,256 | 950,455 |

Realized retained timestamp ratios are 69.9989% / 14.9977% / 15.0034%.
Every model and baseline uses these same boundaries.

## Validation results — ALL

Full-precision results for every model and `ALL`, `ACTIVE`, `PEAK`, and
`ACTIVE_PEAK` segment are in `model_comparison_table.csv`.

| Model | 15m MAE | 30m MAE | 60m MAE | 15m RMSE | 30m RMSE | 60m RMSE | B1 improvement 15/30/60 | Inference ms/1k rows |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B1 Persistence | 0.676 | 1.073 | 1.680 | 1.313 | 1.966 | 3.026 | 0.0% / 0.0% / 0.0% | 0.009 |
| B2 Recent 60m mean | 0.833 | 1.360 | 2.312 | 1.403 | 2.228 | 3.783 | -23.1% / -26.7% / -37.6% | 0.192 |
| B3 Train DOW-time mean | 0.706 | 1.053 | 1.534 | 1.217 | 1.730 | 2.465 | -4.4% / 1.9% / 8.7% | 13.086 |
| Linear Model | 0.736 | 1.129 | 1.728 | 1.260 | 1.864 | 2.844 | -8.9% / -5.1% / -2.8% | 54.299 |
| Random Forest | 0.682 | 1.045 | 1.579 | 1.222 | 1.770 | 2.609 | -0.9% / 2.6% / 6.0% | 303.170 |
| LightGBM | **0.659** | **1.031** | 1.583 | 1.243 | 1.808 | 2.694 | 2.5% / 3.9% / 5.8% | 180.957 |

Random Forest has the lowest learned-candidate 60-minute MAE at 1.579. The B3
train-only day/time mean remains lower at 1.534, so Week 04 does not claim a
universal candidate win.

## Segment findings

The best learned candidate by validation MAE is:

| Segment | 15 minutes | 30 minutes | 60 minutes |
|---|---|---|---|
| ALL | LightGBM, 0.659 | LightGBM, 1.031 | Random Forest, 1.579 |
| ACTIVE | LightGBM, 1.065 | LightGBM, 1.607 | Random Forest, 2.385 |
| PEAK | LightGBM, 0.981 | Random Forest, 1.523 | Random Forest, 2.330 |
| ACTIVE∩PEAK | LightGBM, 1.546 | Random Forest, 2.327 | Random Forest, 3.537 |

Against B1 on the same eligible rows, gains are largest in higher-activity
segments. Random Forest improves `ACTIVE_PEAK` MAE by 9.9%, 15.0%, and 19.2%
for 15/30/60 minutes. LightGBM improves it by 10.0%, 13.8%, and 16.0%.

The provisional 10% B1-improvement threshold in `config/params.yaml` is not met
for every horizon and segment. B3 also remains stronger than the learned
candidates in several 30/60-minute cells. These validation findings justify
additional train/validation-only feature/model work before any Week 05 final
test evaluation.

This report intentionally stops at aggregate model comparison. Error
distributions, residual slices, and explanatory analysis remain Kim Suyeon's
separate Week 04 scope in #33.

## Artifacts

- `model_comparison_table.csv`: required 24-row wide comparison table
- `model_comparison_metrics.csv`: 72 full-precision long-form metric rows with
  evaluated-row counts and same-row B1 references
- `run_metadata.json`: split boundaries, seed, feature order, parameters, data
  checksum/period, runtime versions, ACTIVE definition, output checksums, and
  the explicit Week 05 final-test reservation
- `docs/model/week04-model-comparison.md`: independent reproduction procedure

Inference time is the median of five warmed end-to-end runs over a deterministic
1,000-row validation sample, including preprocessing and predictions for all
three horizons. It is environment-dependent and is not a release threshold.
