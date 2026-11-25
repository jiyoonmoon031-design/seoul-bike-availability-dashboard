# Runtime performance validation

Audit date: 2026-11-25 KST

## Scope

The prior live local Top-3 route measurement was 25.278 seconds. That figure
includes HTTP, Backend, prediction and recommendation work. The current change
removes repeated Python subprocess startup for prediction, recommendation and
rebalancing, caches checksum-verified artifacts in memory, batches station
prediction, and keys a short prediction cache by model version, base time,
horizons and the inventory snapshot.

Backend structured logs now report inventory lookup, candidate search,
prediction and scoring durations separately. AI responses report feature read,
inference, inventory fetch and total durations without logging payload secrets.

## Repeatable warm scoring benchmark

A fixed 20-station synthetic performance fixture was run 20 times through the
in-process recommendation path. It is a performance fixture, not an observed
inventory dataset.

| Metric | Result |
|---|---:|
| runs | 20 |
| p50 | 0.109 ms |
| p95 | 0.124 ms |
| max | 4.329 ms |
| ranking stability | 20/20 identical |

The command also verified the same Top 3 IDs on every run. Python regression
tests increased from the 80-test baseline to 94 passing tests.

## Interpretation

This benchmark proves removal of scoring subprocess overhead and deterministic
warm behavior. It is not directly comparable to the 25.278-second end-to-end
measurement. A new full HTTP p50/p95/max value requires the real Backend, AI,
MySQL, Seoul API and configured artifacts. Therefore the proposed warm E2E p95
target of 5 seconds is not yet claimed as achieved.

OpenAI calls remain separate from route recommendation and were not benchmarked
because no API key was available in this execution environment.
