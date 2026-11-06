# Week 09 Top-3 Recommendation Evaluation Status

Related issue: #42

## Implemented evaluation contract

The evaluator calculates rent and return Top-3 availability hit rates for
15, 30, and 60-minute horizons. It reports both thresholds requested by the
issue:

- minimum availability: at least 1 bike or empty dock;
- stable availability: at least 2 bikes or empty docks.

For origin/rent requests, actual availability is `actual_bikes` at `t+h`.
For destination/return requests, it is `capacity - actual_bikes` at `t+h`.
The micro result is compared with the preregistered provisional target of
0.90, but the target is not changed after observing test results.

## Required candidate-level input

Each returned Top-3 candidate must contain:

- `request_id`
- `base_time`
- `origin_station_id`
- `horizon_min`
- `mode`
- `candidate_station_id`
- `rank`
- `actual_bikes` at `base_time + horizon_min`
- `capacity`

## Current data blocker

The repository and locally shared model artifacts contain historical rental
and return flows, but not the hold-out inventory snapshots and station master
needed to establish actual bikes, empty docks, coordinates, and capacity.
Using `delta_hist` as if it were real inventory would violate the Week 01
evaluation contract. Therefore no hit-rate value is reported until the
following source artifacts are supplied:

1. the station master used for evaluation (`target_stations.csv`);
2. hold-out `station_snapshot` rows covering 2026-06-07 06:00 through
   2026-07-31 23:45 KST, including `station_id`, `collected_at`,
   `bikes_available`, and `capacity`;
3. the frozen candidate/request set, if it has already been generated.

The implemented evaluator, unit tests, input checksum, request-level output,
and horizon summary are ready to run as soon as these artifacts are available.
