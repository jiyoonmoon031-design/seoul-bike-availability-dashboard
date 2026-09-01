# Week 02 EDA Plan

## A. Dataset integrity

1. file inventory
2. period
3. total rows
4. unique stations
5. district distribution
6. missing values
7. duplicates
8. station-master mismatches
9. timestamp continuity
10. source-data gaps

## B. Rental / return behavior

1. rentals by hour
2. returns by hour
3. net change by hour
4. weekday patterns
5. weekday vs weekend
6. holidays
7. morning peak
8. evening peak
9. Gwangjin vs Seongdong
10. station-level activity distribution

## C. Station sparsity

Measure:

- events per station
- zero-activity bins
- active station distribution
- 50 / 75 / 90 percentile activity thresholds

## D. Target analysis

For 15 / 30 / 60 min:

- delta_hist distribution
- mean
- median
- standard deviation
- zero proportion
- positive proportion
- negative proportion
- extreme values

## E. Weather

Only after weather source is verified.

Check:

- weather station/network
- timestamp coverage
- missingness
- temperature
- precipitation
- humidity
- wind speed
- relationship with rental/return volume

## F. Required outputs

Save figures under:

`reports/figures/`

Produce:

- dataset summary table
- data-quality table
- hourly demand plot
- weekday plot
- district comparison
- station activity distribution
- delta_hist distribution by horizon
