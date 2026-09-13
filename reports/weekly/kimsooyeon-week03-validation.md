# Week 03 Validation Report

## 담당자

김수연

## 작업 목적

Week 03 feature와 target 생성 결과를 확인하고, train/test 분할 및 모델 입력
allowlist에 미래 정보가 포함되지 않는지 검증한다.

## 검증 범위

- feature 생성 결과 및 target window contract
- 현재 시점 활동량과 미래 target의 model feature 제외 여부
- 과거 activity window의 base time 경계
- 미래 weather observation 차단
- 불완전한 날짜의 train/validation/test 제외 처리
- chronological split의 시간 순서

## 검증 결과

### Feature/target

- Week 03 focused tests: `8 passed`
- feature build summary: 6,377,643 rows, 185 stations
- model feature allowlist: 46 columns
- valid target rows: h15 `6,290,571`, h30 `6,290,023`, h60 `6,288,927`
- current activity columns (`rent_count`, `return_count`, `delta_hist`) are
  audit-only and are not returned by `get_model_feature_columns()`.
- target columns (`delta_hist_h15`, `delta_hist_h30`, `delta_hist_h60` and
  validity flags) are marked as target and are not model inputs.

### Leakage

- Historical activity features begin at `shift(1)`, so the current `[t, t+15m)`
  activity window is not used for a prediction at `t`.
- A history feature is unavailable when any required source interval is missing
  or timestamp-discontinuous.
- A weather observation after `base_time` raises `FeatureContractError`.
- The persistence baseline uses the target window ending at `base_time`, not the
  future target window beginning at `base_time`.
- Chronological split assigns complete dates only and keeps incomplete dates as
  `excluded`; train dates precede validation dates, which precede test dates.
- The active-station threshold is calculated from the train split only.

## Definition of Done

- [x] feature/target 검증 완료
- [x] train/test leakage 여부 확인 완료
- [x] 발견 문제 및 수정 필요사항 기록

## 발견 문제 및 후속 확인

현재 코드와 compact 산출물에서는 수정이 필요한 leakage가 발견되지 않았다.
다만 원본 parquet는 워크스페이스 외부 경로에 있어, 전체 데이터 재빌드와 독립
재실행은 원본 입력을 다시 연결한 환경에서 한 번 더 수행해야 한다.
