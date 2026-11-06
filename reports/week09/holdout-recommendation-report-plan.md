# Week 09 Hold-out Recommendation Report Plan

Related issue: #43

## Deliverable

`build_week09_recommendation_report.py` converts the frozen Issue #42 result
artifacts into:

- a horizon and micro-average result table;
- a target-aware hit-rate figure;
- a checksum-linked validation report;
- an explicit limitations section.

The report distinguishes rent and return, 15/30/60-minute horizons, and the
minimum (1+) and stable (2+) availability thresholds. Results below the
preregistered 0.90 target are labelled without changing the target.

## Completion dependency

The official report cannot be generated until Issue #42 receives the hold-out
station snapshots and station master documented in
`top3-evaluation-status.md`. No synthetic or historical-flow substitute is
used for the final result.
