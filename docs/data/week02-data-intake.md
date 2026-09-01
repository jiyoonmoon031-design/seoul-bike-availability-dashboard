# Week 02 Data Intake

## Status

- Intake date: 2026-09-02
- Scope: Gwangjin-gu and Seongdong-gu
- Historical period: 2025-08-01 ~ 2026-07-31
- Trip intake: VALIDATED
- Calendar intake: VALIDATED
- Weather intake: PENDING CORRECTION

## 1. Delivered data structure

```text
ddareungi_data/
├── raw/
│   ├── trip/
│   └── weather/
├── interim/
│   └── trip/
├── processed/
│   ├── calendar/
│   └── trip/
├── reference/
│   └── target_stations.csv
└── scripts/
Large raw/interim/generated datasets are stored outside GitHub.

GitHub stores preprocessing code, schemas, validation results, summary tables, and figures.

2. Historical rental/return data

Source:

Seoul Bike station-level rental/return usage history.

Delivered source period:

2025-08 ~ 2026-07

Raw files:

12 monthly ZIP files

Filtered interim files:

12 rental CSV files
12 return CSV files

Total filtered source rows audited:

5,782,026

The source is not individual trip-level data.

It is provided as 5-minute aggregated rental/return records.

Main columns
기준_날짜
집계_기준
기준_시간대
시작_대여소_ID
시작_대여소명
종료_대여소_ID
종료_대여소명
전체_건수
전체_이용_분
전체_이용_거리

Rental-side station ID:

시작_대여소_ID

Return-side station ID:

종료_대여소_ID

Rental rows:

집계_기준 = 출발시간

Return rows:

집계_기준 = 도착시간

3. Source integrity validation

Audit result:

station IDs outside target scope: 0
invalid dates/timestamps: 0
non-5-minute timestamps: 0
invalid counts: 0
negative counts: 0
exact duplicate rows: 0

The 5-minute source resolution was confirmed for all audited records.

4. Missing source dates

Five dates are absent from both rental and return source data:

2026-05-16
2026-05-17
2026-06-29
2026-06-30
2026-07-01

These dates are classified as source-unobserved periods.

They must NOT be interpreted as zero rental/return demand.

5. Target station reference

File:

reference/target_stations.csv

Columns:

station_id
station_name
district

Target master:

221 stations

Gwangjin-gu: 111
Seongdong-gu: 110

Historical observations were found for:

185 stations

Gwangjin-gu: 90
Seongdong-gu: 95

36 target stations were never observed during the historical period.

The following populations remain distinct until reconciliation is completed:

target master: 221
historical observed: 185
realtime collector: 177

No station is removed solely because it is absent from one of these populations until the cause is verified.

6. Calendar data

File:

processed/calendar/calendar_dim.csv

Period:

2025-08-01 ~ 2026-07-31

Rows:

365

Columns:

date
weekday
is_weekend
is_holiday

Calendar data is approved for Week 02 preprocessing and EDA.

7. Weather data

Initially delivered file:

OBS_ASOS_TIM_20260901014501.csv

Detected observation station:

network: ASOS
station ID: 108
station name: Seoul

This does NOT match the Week 01 project decision.

Approved project weather station:

KMA AWS Seongdong station 421.

Therefore:

ASOS 108 is excluded from the modeling pipeline.
weather integration is currently pending.
corrected AWS 421 data must be validated before joining weather features.
8. Historical aggregation

Model preprocessing owner:

문지윤

Base aggregation unit:

station_id × 15-minute interval

Interval convention:

[t, t+15 min)

Generated fields:

rent_count
return_count
delta_hist

Formula:

delta_hist = return_count - rent_count

Generated horizons:

15 min
30 min
60 min

The generated model datasets themselves are not committed to GitHub.

Reproducible aggregation scripts and validation artifacts are committed instead.

9. Current handoff status

Ready:

trip data
target station reference
calendar data
15-minute aggregation
15/30/60-minute target generation
basic EDA

Pending:

corrected AWS 421 weather data
221 / 185 / 177 station population reconciliation
