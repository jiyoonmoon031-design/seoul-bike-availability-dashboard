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

## Week 04 model comparison

```bash
python scripts/run_week04_model_comparison.py \
  --input /path/to/week03_features.parquet
```

Linear Model, Random Forest, LightGBM을 동일한 Week 03 feature와 purge가
적용된 70/15/15 시간순 분할로 학습합니다. Week 04에서는 validation 결과만
저장하며 최종 test 평가는 Week 05까지 보존합니다. 세부 재현 절차는
`docs/model/week04-model-comparison.md`를 따릅니다.

## Real-time collection

예정된 주요 운영 스크립트:

```text
collect_snapshot.py
check_snapshot_quality.py
```

실시간 대여소 스냅샷 수집은 프로젝트 P0 작업으로 관리합니다.


## Week 05 final-model inference

```bash
python scripts/run_week05_inference.py \
  --request /path/to/prediction_request.json \
  --feature-table /path/to/point_in_time_features.parquet \
  --inventory /path/to/current_inventory.json
```

The request JSON follows `docs/interface/model-backend.md`.

The feature-table and inventory arguments are standalone Week 05 execution
adapters and are not additional public API request fields.
