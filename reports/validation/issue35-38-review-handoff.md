# Issues #35 and #38 Review Handoff

Reviewer request: independent review before closing Issues #35 and #38

Validation branch base: `develop` at `e8be918`

## Scope

This document does not reimplement the merged features. It collects the
acceptance evidence for two Kim Suyeon-owned issues so another team member can
review the outputs before the issues are closed.

## Issue #35: baseline improvement and horizon performance

### Definition of Done check

| Requirement | Evidence | Result |
|---|---|---|
| Calculate improvement over the naive baseline | `reports/week05/final_model_test_metrics.csv` and independently recomputed values in `reports/week05/independent-performance-validation.md` | Pass |
| Summarize 15/30/60-minute performance | 12 rows across four segments and three horizons in the final metrics CSV | Pass |
| Finalize the horizon performance table | ALL and segment-level tables in the independent validation report | Pass |

### Independently confirmed results

| Segment | 15 minutes | 30 minutes | 60 minutes |
|---|---:|---:|---:|
| ALL | -2.42% | +2.22% | +7.33% |
| ACTIVE | +0.88% | +5.41% | +10.52% |
| PEAK | +7.19% | +12.61% | +17.83% |
| ACTIVE_PEAK | +10.71% | +16.63% | +21.92% |

The improvement formula is:

`(b1_mae_same_rows - mae) / b1_mae_same_rows`

The result must not be described as a universal improvement. In the ALL
segment, the final model is 2.42% worse than B1 at 15 minutes. The provisional
10% target is reached only in the cells identified in the existing independent
validation report.

### Review files

- `reports/week05/final_model_test_metrics.csv`
- `reports/week05/independent-performance-validation.md`
- `reports/figures/week05_horizon_mae_vs_b1.png`
- `reports/figures/week05_baseline_improvement_heatmap.png`
- `reports/figures/week05_feature_importance_top15.png`

The full artifact-level rerun is not part of Issue #35. It remains tracked by
Issue #34 because the model artifact and feature parquet are not committed.

## Issue #38: origin, destination, and station map UI

### Definition of Done check

| Requirement | Evidence | Result |
|---|---|---|
| Enter an origin and destination | Two independent `LocationSearch` controls in `frontend/src/App.jsx` | Pass |
| Search by place name or address | Kakao place/address adapters in `frontend/src/api/searchApi.js` | Pass |
| Load nearby station candidates | `/api/v1/stations/nearby` adapter in `frontend/src/api/stationApi.js` | Pass |
| Display station candidates on the map | Origin and destination station markers in `frontend/src/components/map/KakaoMap.jsx` | Pass |
| Preserve the user view after operator UI integration | User/operator navigation in `frontend/src/App.tsx` | Pass |
| Handle empty and failed requests | Empty-result and error messages in the search and user-view components | Pass |

### Current validation

Validation was rerun on the integrated `develop` state after PRs #60 and #58:

- `npm ci`: pass, 0 known vulnerabilities
- `npm run lint`: pass
- `npm run build`: pass
- Vite production bundle: pass

Issue #38 covers nearby station candidates and map presentation. Future-aware
Top-3 recommendation cards and recommendation reasons are intentionally outside
this issue and remain tracked by Issue #39.

### Review files

- `frontend/src/App.jsx`
- `frontend/src/App.tsx`
- `frontend/src/components/location/LocationSearch.jsx`
- `frontend/src/components/map/KakaoMap.jsx`
- `frontend/src/api/searchApi.js`
- `frontend/src/api/stationApi.js`

## Reviewer checklist

- Confirm the Issue #35 percentages against the final metrics CSV.
- Confirm that the Issue #35 limitation at ALL/15 minutes is retained.
- Confirm that origin and destination can be selected independently.
- Confirm that nearby candidates use distinct origin/destination markers.
- Confirm that switching to the operator view does not remove the user view.
- Confirm that Issue #39 recommendation work is not claimed as Issue #38 work.

After these checks pass, Issues #35 and #38 can be closed manually. Their
original implementation PRs targeted `develop`, so GitHub did not automatically
close the issues through the `Closes` keywords.
