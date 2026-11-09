# Week 11 Model Inference Fallback Validation

## Scope

Week 11에서는 운영 inference 안정화를 위해 다음 fallback chain을 구현했다.

```text
primary model
    ↓ failure / NaN / Inf
B3 b3_dow_time_mean
    ↓ unavailable / invalid
B1 persistence (delta_net = 0)
Implemented
- station/horizon 단위 model inference failure isolation
- prediction_source
  - model
  - baseline_fallback
- structured warning object
- BASELINE_FALLBACK
- FEATURE_UNAVAILABLE
- B3 train-only fallback artifact
- B3 artifact SHA256 검증
- B3 실패 시 B1 persistence fallback
- 최종 inventory clipping 유지
  - 0 <= bikes_expected <= capacity
  - docks_expected = capacity - bikes_expected
- AI service bridge에서 Week 11 fallback artifact 자동 연결
Missing Feature Policy
결측 값과 결측 feature schema를 구분한다.
- numeric NaN
  - 학습 시 fitted SimpleImputer(strategy="median") 사용
- categorical NaN
  - fitted constant imputation 사용
- required model feature column 자체가 없음
  - FEATURE_UNAVAILABLE
- station/base_time feature row 자체가 없음
  - FEATURE_UNAVAILABLE
  - horizon_results=[]
B3 Artifact Validation
Baseline:

b3_dow_time_mean

Grouping:
station_id
weekday_index
hour
minute

Generated group counts:
Horizon	Groups	Global mean
15 min	124,320	-0.002502
30 min	124,320	-0.004995
60 min	124,320	-0.009979


All global means were finite.

Artifact smoke result:
B3_ARTIFACT_SMOKE=PASS

The binary .joblib artifact is intentionally excluded from Git and is reproducible using:
scripts/build_week11_fallback_baseline.py

Real Model Smoke
Station:
ST-102

Base time:
2025-08-01T00:00:00+09:00

All three horizons returned normal model results:
15m prediction_source=model
30m prediction_source=model
60m prediction_source=model

Bridge Smoke
The complete path was exercised:
ai_service.bridge.run_predict
→ subprocess
→ run_week05_inference.py
→ Week 05 Random Forest
→ Week 11 fallback-aware inference

Result:
WEEK11_BRIDGE_SMOKE=PASS

Validation
Final validation commands:
python -m pytest -q
python -m pre_commit run --all-files
git diff --check
