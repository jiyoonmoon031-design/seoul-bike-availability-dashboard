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

Do not convert station identifiers to numeric values if that could alter the original representation.

The approved Gwangjin-gu/Seongdong-gu station master is used as the reference station list.

Data sources are linked using the following station identifiers:

- Station master: `station_id`
- Historical rental data: `시작_대여소_ID` → `station_id`
- Historical return data: `종료_대여소_ID` → `station_id`
- Real-time bike API: `stationId` → `station_id`
- Snapshot DB: `station_snapshot.station_id` → `station.station_id`

Station IDs are matched using their original string values without arbitrary ID conversion.

If a station exists in the station master but is not observed in a specific data source, it remains unmatched and is not mapped to another station.

### Station coverage by data source

The Gwangjin-gu/Seongdong-gu station master contains 221 stations.

For the historical trip data from August 2025 to July 2026:

- 185 stations have at least one rental record.
- 185 stations have at least one return record.
- The union of stations with rental or return records is 185.
- 36 master stations have neither rental nor return records during the period.

For the real-time bike data:

- 177 of the 221 master stations were observed.
- 44 master stations were not observed in the real-time data.
- All 36 stations absent from the historical trip data are included among these 44 stations.
- The remaining 8 stations have historical trip records but were not observed in the real-time data.

Absence from a data source is treated as "not observed in the dataset" and is not interpreted as station closure or inactivity without additional evidence.

### Station status and unmatched station handling

Station status is distinguished from data matching status.

- **Matched**: The `station_id` in a source matches a station in the target station master.
- **Unmatched / not observed**: A station exists in the target master but does not appear in a specific source or observation period.
- **Inactive**: A station is confirmed as non-operational only when supported by an official source or explicit operational-status information.
- **New station**: A station is classified as newly established only when its opening or registration date can be verified.
- **Closed station**: A station is classified as closed only when closure can be verified from an official source or operational-status information.

A station is not classified as inactive, new, or closed solely because it is absent from historical trip data or real-time bike data.

For the current Week 02 datasets, the 36 stations absent from historical trip data and the 44 stations absent from real-time data are therefore treated as **not observed**, unless additional evidence confirms their operational status.

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
