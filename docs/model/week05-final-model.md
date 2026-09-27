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
