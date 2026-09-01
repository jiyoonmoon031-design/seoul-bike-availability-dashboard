# Week 02 Preprocessing Rules

## 1. Scope

Only:

- Gwangjin-gu
- Seongdong-gu

Adjacent districts are excluded.

## 2. Raw-data preservation

Source data must not be destructively overwritten.

Recommended flow:

raw/external
→ interim
→ processed
→ model-ready

Generated datasets must be reproducible from source data and scripts.

## 3. Station identifier

`station_id` is treated as a string.

Do not convert station identifiers to numeric values if that could alter
the original representation.

Station filtering must be based on the approved Gwangjin/Seongdong
station master or target station reference.

## 4. Timestamp

Timezone must be verified from the source metadata before conversion.

Do not silently assume UTC or KST.

Once confirmed, modeling timestamps must use a consistent timezone-aware
representation.

Backend DB timestamps may be stored in UTC, while Seoul operational
analysis is interpreted in KST.

## 5. Base time bin

Primary aggregation:

`station_id × 15-minute bin`

Interval convention:

`[t, t + 15 min)`

Derived windows/horizons:

- 15 min
- 30 min
- 60 min

## 6. Rental and return counts

For each station/time interval:

- `rent_count`
- `return_count`

Historical net inventory change:

`delta_hist = return_count - rent_count`

Positive:
more bikes returned than rented.

Negative:
more bikes rented than returned.

## 7. Prediction targets

For base time `t`:

`delta_hist_h15`
= returns - rentals during `[t, t+15m)`

`delta_hist_h30`
= returns - rentals during `[t, t+30m)`

`delta_hist_h60`
= returns - rentals during `[t, t+60m)`

Future target windows must never be included in model features.

## 8. Historical feature windows

Candidate lag features available at time `t` include:

- rentals during `[t-15m, t)`
- returns during `[t-15m, t)`
- rentals during `[t-30m, t)`
- returns during `[t-30m, t)`
- rentals during `[t-60m, t)`
- returns during `[t-60m, t)`

These are features, not prediction targets.

## 9. Duplicate policy

Exact duplicate source records must not be counted twice.

The exact duplicate key will be finalized after the real trip schema is
inspected.

Any removed duplicates must be counted and reported.

## 10. Empty bins vs missing data

A valid observation interval with zero activity may be represented as:

`rent_count = 0`
`return_count = 0`
`delta_hist = 0`

A missing source interval must not automatically be interpreted as zero.

Source completeness must be checked first.

## 11. Missing values

Never silently impute:

- station_id
- essential timestamps
- target values

Weather-variable imputation rules are finalized only after Week 02
missingness analysis.

## 12. Leakage prevention

For prediction base time `t`, every feature must be computable using
information available at or before `t`.

Future rental/return counts, future snapshots, or test-period aggregate
statistics must not be included in model inputs.

## 13. Required preprocessing report

Record:

- source files
- source period
- row counts
- duplicate counts
- missing counts
- unmatched station IDs
- excluded rows
- district counts
- timestamp range
- generated output files
