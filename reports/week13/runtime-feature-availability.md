# Runtime Random Forest feature availability

Audit date: 2026-11-25 KST

## Verified artifacts

| Artifact | Size | SHA-256 | Result |
|---|---:|---|---|
| `week03_features.parquet` | 109 MiB | `e1c94933347c27ef80bb4dc8a774960497ec6de94455cc195266aefd551e5202` | matches metadata |
| `final_model.joblib` | 282 MiB | `e8b7543db145c63259301e60cf6fe248843ec9327cfe85f0c2323cba432deadd` | matches metadata |
| `fallback_baselines.joblib` | 9.3 MiB | `578d679fec113d0c112ed0c2181319939b2ce167ff665f2ad542d61c082f821e` | matches metadata |

The feature table has 6,377,643 rows, 185 stations and seven row groups. Its
period is 2025-08-01 00:00 through 2026-07-31 23:45. The frozen RF metadata
declares 46 ordered features and the same chronological train/validation/test
split already documented in `final_model_metadata.json`.

## Availability decision

The frozen Week 05 RF cannot perform an evidence-valid current-time prediction
from a five-minute inventory snapshot alone. The ordered contract requires
gross rentals and returns at 15/30/60 minute lags, 24-hour rolling history,
one-day and seven-day lags, and observation-age controlled weather values.
The live station status supplies inventory, capacity and collection time, but
does not supply gross `rent_count` and `return_count`. Net inventory differences
cannot reconstruct gross rentals and returns because simultaneous rentals and
returns cancel out.

The checked feature table also ends on 2026-07-31, so it has no exact row for
the 2026-11-25 runtime. Generating those missing values from future or synthetic
observations would violate the trained feature contract.

## Runtime decision

- Use the frozen RF only when an exact point-in-time feature row satisfies the
  stored ordered feature schema.
- Otherwise return the actual reason and use B3 day-of-week/time mean.
- If B3 is unavailable, use B1 persistence.
- Keep `prediction_source` horizon-specific and never label fallback output as
  RF output.

## Data required to unblock a separate snapshot model

Collect timestamped station snapshots at a stable interval, retain provenance
and missingness, and obtain real rental and return events if the target is the
existing gross-flow RF contract. A separate inventory-snapshot model may be
trained only after enough chronological history exists for leakage-safe lag
features and a time-ordered holdout. Its metrics and model version must remain
separate from the Week 05 RF.
