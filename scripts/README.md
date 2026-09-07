# Operational Scripts

## Week 03 model workflow

```bash
python scripts/build_week03_features.py \
  --input /path/to/trip_targets_weather_15_30_60.parquet \
  --output /path/to/week03_features.parquet

python scripts/run_week03_naive_baseline.py \
  --input /path/to/week03_features.parquet \
  --params config/params.yaml \
  --metrics-output reports/week03/naive_baseline_metrics.csv
```

세부 feature, leakage, split, baseline 계약은
`docs/model/week03-feature-baseline.md`를 따릅니다.

## Real-time collection

예정된 주요 운영 스크립트:

```text
collect_snapshot.py
check_snapshot_quality.py
```

실시간 대여소 스냅샷 수집은 프로젝트 P0 작업으로 관리합니다.
