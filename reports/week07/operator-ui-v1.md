# Week 07 Operator UI v1

## 담당

문지윤 — 운영자 탭 UI 구현

## 구현 범위

- React + TypeScript + Vite 기반 frontend 구성
- 운영자 dashboard layout 구현
- 기준 시각 선택
- 예측 horizon 15 / 30 / 60분 선택
- Top N 선택
- Kakao Maps JavaScript SDK 연동
- 부족 대여소 marker
- 포화/공급 대여소 marker
- 정상 대여소 marker
- marker 상세 popup
- 공급소 → 수요소 재배치 이동선 표시
- 이동 권장 대수 표시
- 재배치 이동 매칭 리스트
- 재배치 우선순위표
- 예상 재고 / 부족량 / 긴급도 / 수요 가중치 / priority score / 위험시각 표시
- baseline_fallback 표시
- TanStack Query 기반 API query layer 구성
- MSW 기반 operator/station API mock 구성
- 실제 StationStatus backend DTO와 동일한 frontend adapter 구성

## 데이터 흐름

현재 Week 07 frontend 검증 단계에서는 MSW를 사용한다.

Operator UI
→ TanStack Query
→ frontend API client
→ MSW
→ operator/rebalancing response

Station metadata는 실제 backend 계약과 동일한 다음 endpoint schema를 사용한다.

GET /api/v1/stations/status

Backend DTO 필드:

- station_id
- station_name
- district
- latitude
- longitude
- capacity
- bikes_now
- docks_now
- collected_at

Frontend adapter에서는 latitude / longitude를 lat / lon으로 변환하여
Kakao Map component에 전달한다.

## 상태 판정

Station status API의 현재 재고값으로 shortage/surplus를 다시 계산하지 않는다.

부족/포화 판정은 Week 06 재배치 알고리즘 결과를 authoritative source로 사용한다.

- shortage_top → shortage
- surplus_top → surplus
- 그 외 → normal

## 검증

Frontend production build:

- npm run build: PASS

Frontend static lint:

- npm run lint: PASS

수동 UI 확인:

- Kakao Map rendering
- shortage / surplus / normal marker
- marker popup
- rebalancing line
- horizon switching
- Top N switching
- priority sorting
- baseline fallback badge

## 현재 통합 상태

현재 develop backend에는 POST /api/v1/predict 및 station status API가 존재하지만
operator risk / rebalancing endpoint는 아직 구현되어 있지 않다.

따라서 Week 07 문지윤 frontend 구현은 MSW를 이용하여 API contract를 유지한 상태로
완료하고, 실제 backend 연동은 backend 담당자의 endpoint 구현 후 수행한다.

Backend 연결 시 frontend 구조 변경 없이 다음 환경 설정을 전환할 수 있도록 구성하였다.

VITE_USE_MSW=false
VITE_API_BASE_URL=<backend URL>

## 후속 검증

김수연 검토 단계에서 다음을 수행한다.

- API JSON과 UI 표시값 1:1 대조
- Top N priority 순서 확인
- 이동 권장 대수 확인
- 위험점수 표시 확인
- 지도 marker 상태 확인
