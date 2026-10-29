# Week 05 Independent Model Reproduction

Related issue: #34

## Artifact integrity

| Artifact | Expected SHA-256 | Result |
|---|---|---|
| `final_model.joblib` | `e8b7543db145c63259301e60cf6fe248843ec9327cfe85f0c2323cba432deadd` | Match |
| `week03_features.parquet` | `e1c94933347c27ef80bb4dc8a774960497ec6de94455cc195266aefd551e5202` | Match |

The files were downloaded to a local directory outside Git. The model loads as the registered `FittedCandidate`, and its 46 ordered raw features exactly match `final_model_metadata.json`.

## Independent procedure

1. Verify the model and feature-table checksums.
2. Load only the registered feature and evaluation columns.
3. Recreate the chronological 70/15/15 split with two 60-minute purge gaps.
4. Recompute the train-only 75th-percentile active-station definition.
5. Load the frozen model without fitting.
6. Predict the fixed test split and recompute all 12 segment/horizon metrics.
7. Compare the results against `final_model_test_metrics.csv` at `1e-10` tolerance.

## Reproduction checks

- Test rows: 950,455
- Registered features: 46
- Active threshold: 28,428
- Active stations: 47
- Metric rows: 12
- Maximum absolute metric difference: `4.6913584128560615e-12`
- Rows within tolerance: 12/12

## Reproduced ALL metrics

| Horizon | MAE | RMSE | B1 MAE | Improvement vs B1 |
|---|---:|---:|---:|---:|
| 15 minutes | 0.638877 | 1.124372 | 0.623763 | -2.42% |
| 30 minutes | 0.977497 | 1.625141 | 0.999658 | +2.22% |
| 60 minutes | 1.465295 | 2.380355 | 1.581251 | +7.33% |

All segment/horizon values reproduce within decimal serialization tolerance. The local median inference measurement was 44.57 ms per 1,000 rows; the registered run recorded 48.36 ms. Runtime is environment-dependent and is not included in the deterministic metric equality assertion.

## Outputs

- `independent-reproduction/reproduced_metrics.csv`
- `independent-reproduction/metric_comparison.csv`
- `independent-reproduction/reproduction_summary.json`
- `scripts/reproduce_week05_final_metrics.py`

## Conclusion

Issue #34 is independently reproduced. The model artifact, input feature table, feature order, chronological split, active-station definition, evaluated row counts, MAE, RMSE, B1 reference, and improvement values all match the registered final result within `1e-10` tolerance.
