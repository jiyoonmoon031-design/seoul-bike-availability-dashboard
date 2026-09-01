# Model Training Area Selection

## Status

- Issue: #8
- Week: Week 01
- Service Area: 광진구 · 성동구
- Model Training Area: 광진구 · 성동구
- Validation Area: 광진구 · 성동구
- Status: Final

## 1. Final Decision

본 프로젝트의 서비스, 모델 학습, 검증 범위는 모두 다음 두 자치구로 고정한다.

- 광진구
- 성동구

인접 자치구는 모델 학습에 포함하지 않는다.

## 2. Scope by Layer

| Layer | Scope |
|---|---|
| Backend realtime collection | 광진구 · 성동구 |
| Historical training data | 광진구 · 성동구 |
| Model training | 광진구 · 성동구 |
| Validation | 광진구 · 성동구 |
| User recommendation | 광진구 · 성동구 |
| Operator rebalancing | 광진구 · 성동구 |

## 3. Rationale

파일럿 프로젝트의 재현성과 범위 통제를 우선한다.

인접 권역까지 포함하면 데이터 수집·전처리·검증 범위가 확대되고 서비스 대상 범위와 학습 범위가 달라져 결과 해석이 복잡해질 수 있다.

따라서 광진구·성동구 데이터만 사용한다.

## 4. Data Sparsity Policy

데이터 희소성이 확인되더라도 인접 자치구를 추가하지 않는다.

대신 다음 방법을 적용한다.

- 15분 결과와 함께 30분·60분 집계 사용
- ACTIVE segment 분리
- PEAK segment 분리
- ACTIVE ∩ PEAK segment 분리
- 대여소별 표본 수와 제외율 공개

## 5. Change Control

향후 범위를 확대해야 할 경우 현재 결과를 유지한 상태에서 별도 Issue와 PR을 통해 변경 근거와 영향 범위를 기록한다.
