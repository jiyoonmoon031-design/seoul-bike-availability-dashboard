# Week 02 Trip Aggregation Results

## Status

15-minute historical rental/return aggregation completed and structurally validated.

## Source

Period:

2025-08-01 ~ 2026-07-31

Input:

- 12 rental CSV files
- 12 return CSV files
- 5,782,026 filtered source rows

Scope:

- Gwangjin-gu
- Seongdong-gu

## Source validation

No issues were found for:

- off-scope station IDs
- invalid dates
- invalid HHMM values
- timestamps outside 5-minute boundaries
- invalid counts
- negative counts
- exact duplicate source rows

## Missing source dates

The following dates are absent from both rental and return source files:

- 2026-05-16
- 2026-05-17
- 2026-06-29
- 2026-06-30
- 2026-07-01

These dates are treated as unobserved source periods and are NOT filled as zero demand.

## Station coverage

Target station master:

221 stations

- Gwangjin-gu: 111
- Seongdong-gu: 110

Stations observed at least once in historical data:

185 stations

- Gwangjin-gu: 90
- Seongdong-gu: 95

Stations never observed in the historical period:

36 stations

The historical station population is not yet treated as the final service-model population.

A separate reconciliation is required among:

- target master: 221
- historical observations: 185
- realtime collector population: 177

## 15-minute panel

Output:

`trip_agg_15m.parquet`

Unit:

`station_id × base_time`

Interval:

`[t, t+15 min)`

Fields include:

- station_id
- station_name
- district
- base_time
- calendar fields
- rent_count
- return_count
- delta_hist
- source_day_observed
- is_observed

Formula:

`delta_hist = return_count - rent_count`

## Build result

Rows:

6,379,584

Stations:

185

Observed rows:

6,292,512

Unobserved rows:

87,072

Period:

2025-08-01 00:00 ~ 2026-07-31 23:45

## Structural QA

PASS:

- 15-minute alignment
- observed/null policy
- unobserved/null policy
- delta_hist identity
- non-negative rent_count
- non-negative return_count
- unique station_id × base_time unit

## Initial sparsity finding

`delta_hist == 0` proportion:

64.44%

This indicates substantial short-horizon target sparsity and will be examined by station, hour, district, and activity segment during EDA.

## Weather status

The initially delivered weather dataset is ASOS Seoul station 108.

It is excluded from the current modeling pipeline because Week 01 selected KMA AWS Seongdong station 421.

Weather integration remains pending until the corrected AWS 421 dataset is delivered.
