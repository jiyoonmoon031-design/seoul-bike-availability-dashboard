# Week 02 Training Table Schema

## Unit

One row represents:

`station_id × base_time`

## Required identity fields

| Field | Meaning |
|---|---|
| station_id | Seoul Bike station ID |
| base_time | prediction reference time |
| district | Gwangjin-gu / Seongdong-gu |

## Historical activity features

| Field | Meaning |
|---|---|
| rent_prev_15m | rentals in previous 15 min |
| return_prev_15m | returns in previous 15 min |
| rent_prev_30m | rentals in previous 30 min |
| return_prev_30m | returns in previous 30 min |
| rent_prev_60m | rentals in previous 60 min |
| return_prev_60m | returns in previous 60 min |

## Prediction targets

| Field | Meaning |
|---|---|
| delta_hist_h15 | return - rental count during next 15 min |
| delta_hist_h30 | return - rental count during next 30 min |
| delta_hist_h60 | return - rental count during next 60 min |

## Calendar features

Planned after validation:

- hour
- weekday
- weekend
- holiday
- peak

## Weather features

Planned after weather-source verification:

- temperature
- precipitation
- humidity
- wind speed

Weather station/network must be consistent with the Week 01 weather
station decision before integration.

## Future additions

Week 03 may add:

- same weekday/hour historical mean
- rolling demand statistics
- station activity pattern
- current inventory where appropriate

These are not finalized in Week 02.
