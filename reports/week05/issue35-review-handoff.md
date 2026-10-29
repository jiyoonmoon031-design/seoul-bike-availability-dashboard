# Issue #35 Review Handoff

Reviewer request: independently confirm the baseline improvement and final horizon performance before closing Issue #35.

## Definition of Done

| Requirement | Evidence | Result |
|---|---|---|
| Calculate improvement over naive B1 | Final metrics CSV and independent recomputation | Pass |
| Summarize 15/30/60-minute performance | Four segments × three horizons | Pass |
| Finalize the horizon performance table | Independent validation report | Pass |

## Confirmed results

| Segment | 15 minutes | 30 minutes | 60 minutes |
|---|---:|---:|---:|
| ALL | -2.42% | +2.22% | +7.33% |
| ACTIVE | +0.88% | +5.41% | +10.52% |
| PEAK | +7.19% | +12.61% | +17.83% |
| ACTIVE_PEAK | +10.71% | +16.63% | +21.92% |

The improvement formula is `(b1_mae_same_rows - mae) / b1_mae_same_rows`.

The model must not be described as a universal baseline improvement. In the ALL segment, the 15-minute result is 2.42% worse than B1. The provisional 10% target is achieved only in the cells documented in the independent validation report.

## Reviewer files

- `reports/week05/final_model_test_metrics.csv`
- `reports/week05/independent-performance-validation.md`
- `reports/figures/week05_horizon_mae_vs_b1.png`
- `reports/figures/week05_baseline_improvement_heatmap.png`
- `reports/figures/week05_feature_importance_top15.png`

The artifact-level model rerun is outside Issue #35 and remains tracked by Issue #34 because the model and feature parquet are not committed.

## Reviewer checklist

- Recompute the stored improvement values from the final metrics CSV.
- Confirm all 12 segment/horizon cells.
- Confirm the ALL/15-minute limitation remains explicit.
- Confirm Issue #34 is not claimed as completed.
