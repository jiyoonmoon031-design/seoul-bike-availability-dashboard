# Project Area Decision

## Status

- Week: Week 01
- Related Issue: #8
- Status: Confirmed

## Service Area

- 광진구
- 성동구

## Model Training Area

- 광진구
- 성동구

## Decision

서비스 대상 권역과 모델 학습 대상 권역을 모두 광진구·성동구로 한정한다.

인접 자치구 데이터는 본 프로젝트의 모델 학습 범위에 포함하지 않는다.

## Implementation Rule

Backend 데이터 수집, 데이터 전처리, 모델 학습, 검증 및 서비스 대상 station은 광진구·성동구 기준으로 관리한다.

대여소 단위 단기 데이터 희소성이 확인되는 경우 권역을 확대하는 대신 30/60분 집계, 활성 대여소 및 시간대별 segment 분석으로 대응한다.
