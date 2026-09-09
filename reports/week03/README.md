# Week 03 Feature Engineering and Naive Baseline Results

## Feature build

- Period: 2025-08-01T00:00:00 ~ 2026-07-31T23:45:00
- Rows: 6,377,643
- Stations: 185
- Observed rows: 6,290,571
- Unobserved rows: 87,072
- Model features: 46
- Valid target rows: {'15': 6290571, '30': 6290023, '60': 6288927}

## Naive baseline — ALL stations

| Split | Scope | Horizon | Baseline | Evaluated rows | MAE | RMSE |
|---|---|---:|---|---:|---:|---:|
| validation | horizon | 15 | persistence | 243,083 | 0.9754 | 1.6804 |
| validation | horizon | 15 | zero | 243,264 | 0.6573 | 1.2846 |
| validation | horizon | 30 | persistence | 242,721 | 1.4791 | 2.4323 |
| validation | horizon | 30 | zero | 243,083 | 1.0496 | 1.9437 |
| validation | horizon | 60 | persistence | 241,997 | 2.2700 | 3.7466 |
| validation | horizon | 60 | zero | 242,721 | 1.6556 | 3.0336 |
| validation | micro | micro | persistence | 727,801 | 1.5738 | 2.7538 |
| validation | micro | micro | zero | 729,068 | 1.1205 | 2.2077 |
| test | horizon | 15 | persistence | 485,647 | 0.8483 | 1.4962 |
| test | horizon | 15 | zero | 485,647 | 0.5635 | 1.1311 |
| test | horizon | 30 | persistence | 485,466 | 1.2924 | 2.1515 |
| test | horizon | 30 | zero | 485,466 | 0.9075 | 1.6967 |
| test | horizon | 60 | persistence | 485,104 | 1.9840 | 3.2551 |
| test | horizon | 60 | zero | 485,104 | 1.4380 | 2.6245 |
| test | micro | micro | persistence | 1,456,217 | 1.3747 | 2.4123 |
| test | micro | micro | zero | 1,456,217 | 0.9695 | 1.9186 |

## Reproduction

- Feature definition: `docs/model/week03-feature-baseline.md`
- Feature manifest: `reports/week03/feature_manifest.csv`
- Build summary: `reports/week03/feature_build_summary.json`
- Full metrics: `reports/week03/naive_baseline_metrics.csv`
- Large feature parquet is stored outside Git.

## Review status

- Independent leakage/data-quality review: pending
- Reviewer: Kim Suyeon
