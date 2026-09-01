# Week 02 Data Intake Checklist

## Required datasets

### Trip history
Expected location from handoff:
`ddareungi_data/interim/trip/`

Verify:

- source organization / dataset name
- source URL or acquisition method
- period
- raw vs filtered vs aggregated
- row count
- file count
- file format
- rental station ID
- return station ID
- rental timestamp
- return timestamp
- timestamp timezone
- Gwangjin/Seongdong filtering rule
- filtering script
- target station reference file

Do not assume a filtered dataset is reproducible unless the filtering
script or exact filtering rule is available.

## Weather

Expected location:
`ddareungi_data/raw/weather/`

Week 01 project decision:
KMA AWS Seongdong station 421.

IMPORTANT:
The handoff message describes this directory as "ASOS weather raw data".
Confirm whether the actual files are:

1. AWS station 421 data, or
2. ASOS data from another station.

Do not merge ASOS data into the model pipeline until this is resolved.

Verify:

- observation network: AWS / ASOS
- station ID
- station name
- period
- temperature
- precipitation
- humidity
- wind speed
- timestamp resolution
- missing values

## Calendar

Expected location:
`ddareungi_data/processed/calendar/calendar_dim.csv`

Verify:

- date
- weekday
- weekend
- holiday
- source of holiday information
- full project date coverage

## Reference

Expected:
`ddareungi_data/reference/target_stations.csv`

Verify:

- station_id
- station_name
- district
- latitude
- longitude
- capacity if available
- only Gwangjin-gu / Seongdong-gu

## Reproducibility requirement

Large raw datasets do not need to be committed to GitHub.

GitHub must contain or reference:

- acquisition/source information
- filtering rules
- preprocessing code
- schema
- data period
- row counts
- file manifest
- generated dataset provenance
