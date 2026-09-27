# Week 04 Forecasting Model Comparison

## Status and ownership

- Related Issue: #49
- Owner: Moon Jiyoon
- Internal reviewer: Kim Suyeon (`@rlatndusgu`)
- Input: merged Week 03 enriched feature parquet and feature manifest
- Candidates: Linear Model, Random Forest, LightGBM
- Evaluation: validation only
- Final test: labelled and preserved for the Week 05 independent evaluation

Kim Suyeon's model error-distribution analysis remains in #33. Jo Seongeun's
prediction API mock is not part of this work. This implementation produces an
optional validation-prediction handoff file, but it does not perform or claim
either teammate's task.

## Preserved contracts

The implementation keeps the Week 01-03 contracts unchanged:

- model scope is Gwangjin-gu and Seongdong-gu;
- a row remains `station_id × base_time` at a 15-minute cadence;
- targets are future net inventory changes for 15, 30, and 60 minutes;
- missing source intervals remain missing rather than becoming zero demand;
- weather remains an AWS 421 as-of feature observed no later than `base_time`;
- training uses the exact ordered output of `get_model_feature_columns()` and
  verifies its membership/roles against the committed Week 03 feature manifest;
- current-window activity and future target columns are never model inputs.

Categorical encoding and numeric imputation are fitted only on the training
partition. Missingness flags from Week 03 remain explicit model inputs.

## One split for every model

The same unique-timestamp split is reused by all baselines and candidates:

```text
train 70% → 60-minute excluded gap → validation 15%
          → 60-minute excluded gap → final test 15%
```

The percentages apply to retained timestamps after the two gaps are removed.
All stations at the same timestamp receive the same label. A 60-minute gap is
four 15-minute timestamps, which prevents the maximum 60-minute training target
from crossing into validation and prevents a validation target from crossing
into the final test period.

Week 04 fits preprocessing and estimators on `train`, compares candidates on
`validation`, and does not calculate a test metric. Test targets are left for
Kim Suyeon's Week 05 independent final evaluation. Changing test targets is
covered by an automated test that confirms Week 04 metrics do not change.

## Baselines and candidates

The comparison uses the three pre-registered naive baseline definitions:

| ID | Name | Definition |
|---|---|---|
| B1 | Persistence | Predict zero future net change (inventory persists) |
| B2 | Recent 60-minute mean | Scale the complete preceding 60-minute net change to each horizon |
| B3 | Day/time mean | Train-only `station × weekday × hour × minute` target mean, with a train global-mean fallback |

Every candidate consumes the same raw Week 03 feature list and order:

- Linear Model: one-hot categorical encoding, median numeric imputation,
  standardization, and deterministic ridge linear regression;
- Random Forest: ordinal categorical encoding, median numeric imputation, and a
  bounded forest configuration for the Week 04 comparison;
- LightGBM: the same tree preprocessing and deterministic gradient boosting.

The fixed parameters and random seed are in `config/params.yaml` and copied
verbatim to the run metadata. Week 04 performs no test-based tuning.

## Outputs

`reports/week04/model_comparison_table.csv` is the required wide comparison.
It has one row for each model and each of:

- `ALL`
- `ACTIVE`
- `PEAK`
- `ACTIVE_PEAK` (`ACTIVE ∩ PEAK`)

Columns contain 15/30/60-minute MAE, 15/30/60-minute RMSE, improvement against
B1 on the same eligible rows, and end-to-end inference milliseconds per 1,000
rows. `model_comparison_metrics.csv` retains the long form and evaluated-row
counts.

`run_metadata.json` records:

- exact split boundaries and row/timestamp counts;
- both requested and realized retained timestamp ratios;
- the two 60-minute gaps;
- seed, target horizons, and ordered Week 03 feature list;
- parameters and training-row counts for every candidate/horizon;
- input filename, SHA-256, period, row count, and station count;
- runtime and dependency versions;
- implementation-file and output checksums;
- ACTIVE threshold and station IDs fitted on train only;
- an explicit record that no final-test metric was generated.

Model weights and the large feature/prediction parquet files are not committed.

## Reproduce

Use Python 3.11 and install the pinned dependencies:

```bash
python3.11 -m pip install -r requirements.txt
```

Run from the repository root, substituting the local Week 03 parquet path:

```bash
python3.11 scripts/run_week04_model_comparison.py \
  --input /path/to/week03_features.parquet \
  --params config/params.yaml \
  --feature-manifest reports/week03/feature_manifest.csv \
  --metrics-output reports/week04/model_comparison_metrics.csv \
  --comparison-output reports/week04/model_comparison_table.csv \
  --metadata-output reports/week04/run_metadata.json
```

Kim Suyeon's separate analysis can request an uncommitted validation handoff:

```bash
python3.11 scripts/run_week04_model_comparison.py \
  --input /path/to/week03_features.parquet \
  --predictions-output /path/outside/git/week04_validation_predictions.parquet
```

For an independent reproduction, verify the input SHA-256 and implementation
file hashes against `run_metadata.json`, use the recorded dependency versions,
and compare the full-precision validation CSV. MAE rounded to three decimal
places must agree for every model, segment, and horizon.

## Verification

```bash
python3.11 -m pytest -q
python3.11 -m pre_commit run --all-files
git diff --check
```

The tests cover the 70/15/15 timestamp allocation, both four-interval gaps,
ordered Week 03 allowlist preservation, train-only B3 fitting, all 72 long-form
comparison rows, all 24 wide-form rows, and test-target isolation.
