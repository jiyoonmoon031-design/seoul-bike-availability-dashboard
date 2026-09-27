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


## Final one-time test result

The validation-selected Random Forest was frozen before accessing the final
test split. It was then refit on the train + validation splits and evaluated
on the reserved test split exactly once.

Final model:

- model_id: `random_forest`
- model_version: `week05-random_forest-5b8406059363`
- random seed: `42`
- n_estimators: `48`
- max_depth: `None`
- min_samples_leaf: `25`
- max_features: `1.0`
- max_samples: `0.35`
- bootstrap: `true`

| Segment | Horizon | MAE | RMSE | B1 MAE | Improvement vs B1 |
|---|---:|---:|---:|---:|---:|
| ALL | 15 | 0.638877 | 1.124372 | 0.623763 | -2.42% |
| ALL | 30 | 0.977497 | 1.625141 | 0.999658 | +2.22% |
| ALL | 60 | 1.465295 | 2.380355 | 1.581251 | +7.33% |
| ACTIVE | 15 | 1.021618 | 1.587951 | 1.030647 | +0.88% |
| ACTIVE | 30 | 1.513345 | 2.291425 | 1.599895 | +5.41% |
| ACTIVE | 60 | 2.223721 | 3.355479 | 2.485127 | +10.52% |
| PEAK | 15 | 0.929512 | 1.503422 | 1.001475 | +7.19% |
| PEAK | 30 | 1.424868 | 2.233197 | 1.630428 | +12.61% |
| PEAK | 60 | 2.161232 | 3.363384 | 2.630055 | +17.83% |
| ACTIVE_PEAK | 15 | 1.459460 | 2.135092 | 1.634563 | +10.71% |
| ACTIVE_PEAK | 30 | 2.191737 | 3.178655 | 2.628998 | +16.63% |
| ACTIVE_PEAK | 60 | 3.317735 | 4.840304 | 4.249373 | +21.92% |

The pre-registered primary selection segment, ACTIVE_PEAK at 30 minutes,
achieved MAE 2.191737 and improved by 16.63% over the same-row B1 persistence
baseline.

The final result must not be described as universally outperforming B1:
the ALL 15-minute segment was 2.42% worse than B1. The improvement is stronger
for ACTIVE and PEAK operational segments and increases at the longer forecast
horizons.

No model or hyperparameter changes are permitted based on this final test
result without defining a new evaluation cycle and reserving a new untouched
evaluation set.

Model artifact SHA256:

`e8b7543db145c63259301e60cf6fe248843ec9327cfe85f0c2323cba432deadd`

## Final model inference

The serialized Week 05 model is exposed through
`scripts/run_week05_inference.py`.

The public prediction request remains the previously defined
model-backend contract:

- `request_id`
- `base_time`
- `station_ids`
- `horizons`

`base_time` must be KST timezone-aware and the inference implementation
does not silently coerce an unaligned timestamp to another 15-minute bin.

The standalone Week 05 runner additionally receives a point-in-time feature
table and current inventory file as execution adapters. These are not new
fields in the public Backend -> Model JSON contract.

The current inventory adapter supplies:

- `station_id`
- `bikes_now`
- `capacity`

For each requested horizon the model predicts `delta_net` and computes:

`bikes_expected = clip(bikes_now + delta_net, 0, capacity)`

`docks_expected = capacity - bikes_expected`

The runner verifies the serialized model SHA256 and raw feature order before
inference and includes `model_version` in every response.

If a requested station cannot be predicted, the station remains in the
`predictions` array with an empty `horizon_results` array and the reason is
added to `warnings`.

The file-based feature and inventory adapters are a Week 05 standalone
execution boundary. Backend/DB integration replaces these adapters in Week 06
without changing the public prediction JSON contract.
