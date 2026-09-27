# Week 05 Final Forecasting Model

## Status

- Owner: Moon Jiyoon
- Related issue: Week 05 model tuning issue
- Base: Week 04 model comparison
- Scope: Gwangjin-gu + Seongdong-gu
- Horizons: 15 / 30 / 60 minutes

## Rules

- Week 04 feature contract remains unchanged.
- Chronological split remains unchanged.
- Hyperparameter tuning uses validation only.
- Test is evaluated only after final model selection.
- No feature may use information after base time t.

## Selection criteria

1. ACTIVE ∩ PEAK 30-minute MAE
2. overall mean MAE
3. inference time per 1,000 rows
4. simpler model on a tie

## Candidates for tuning

Week 04 results indicate that the strongest learned candidates are Random Forest
and LightGBM. Both remain eligible until validation-based tuning is complete.

## Required outputs

- tuning history
- segment/horizon metrics
- feature importance
- final model decision
- serialized model metadata
- inference contract
- reproducibility metadata

## Validation tuning result

Week 05 tuning was performed on the validation split only.

The pre-registered primary selection criterion is:

1. ACTIVE ∩ PEAK 30-minute MAE
2. ALL-horizon mean MAE
3. inference time per 1,000 rows

Validation finalists:

| Model | ACTIVE∩PEAK 30m MAE | ALL mean MAE | Inference ms / 1k |
|---|---:|---:|---:|
| Random Forest | 2.308383 | 1.102666 | 47.709 |
| LightGBM | 2.330840 | 1.083841 | 13.575 |

Random Forest is selected because it has the lower value on the primary
criterion. Its inference time also satisfies the preferred 200 ms / 1,000-row
constraint.

Selected Random Forest parameters:

- n_estimators: 48
- max_depth: null
- min_samples_leaf: 25
- max_features: 1.0
- max_samples: 0.35
- bootstrap: true
- n_jobs: -1
- random_seed: 42

The final test split has not been evaluated at this stage.
