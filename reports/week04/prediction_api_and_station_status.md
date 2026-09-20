## 4주차 작업 보고

### 1. 예측 모델 연동 API 인터페이스 구현

실제 예측 모델 연동 전 Model → Backend 간 요청/응답 구조를 검증하기 위해
예측 API 및 Mock 서비스를 구현하였다.

- `POST /api/v1/predict` 구현
- 예측 요청/응답 DTO 구성
  - `PredictionRequest`
  - `PredictionResponse`
  - `StationPrediction`
  - `HorizonResult`
  - `PredictionWarning`
- 15/30/60분 예측 horizon을 고려한 응답 구조 설계
- 일부 horizon의 예측 실패를 처리할 수 있도록 `warnings` 구조 구현
- 실제 AI 모델 연결 전 `MockPredictionService`를 통해 응답 구조 검증

Model → Backend 예측 응답에는 다음 정보를 포함하도록 구성하였다.

- `delta_net`: 현재 대비 예상 자전거 변화량
- `bikes_expected`: 해당 시점의 예상 대여 가능 자전거 수
- `docks_expected`: 해당 시점의 예상 반납 여유 지표

현재 Mock API에서는 고정된 예측값을 사용하며,
추후 실제 예측 모델 API로 교체할 예정이다.

### 2. 현재 대여소 현황 조회 API 구현

프론트엔드에서 광진구·성동구 대여소의 현재 상태를 조회할 수 있도록
현재 대여소 현황 API를 구현하였다.

- `GET /api/v1/stations/status` 구현
- `station` 테이블의 대여소 기본 정보와
  `station_snapshot`의 대여소별 최신 데이터를 결합
- 대여소별 다음 정보 반환
  - 대여소 ID 및 이름
  - 자치구
  - 위도/경도
  - 거치대 수(`capacity`)
  - 현재 대여 가능 자전거 수(`bikes_now`)
  - 현재 반납 여유 지표(`docks_now`)
  - 데이터 수집 시각(`collected_at`)

### 3. 실제 데이터 기반 `capacity` 및 `docks_now` 처리

실제 수집 데이터를 확인한 결과 일부 대여소에서
`bikes_now`가 `capacity`보다 큰 경우가 존재함을 확인하였다.

단순히 다음과 같이 계산할 경우

`docks_now = capacity - bikes_now`

음수가 발생할 수 있으므로 다음과 같이 처리하였다.

`docks_now = max(capacity - bikes_now, 0)`

예시:

- `capacity = 10`
- `bikes_now = 51`
- `docks_now = 0`

또한 `capacity` 또는 `bikes_now` 값이 없는 경우에는
`docks_now = null`로 처리하도록 구현하였다.

`capacity`는 거치대 수를 기준으로 하는 값이므로,
`docks_now`는 실제 물리적 반납 가능 공간을 정확히 나타내는 값이라기보다
거치대 수를 기준으로 계산한 반납 여유 지표로 사용한다.

### 4. 테스트 결과

- Mock Prediction API 정상 응답 확인
- 요청의 `request_id`, `base_time` 응답 전달 확인
- 현재 대여소 현황 API 정상 응답 확인
- 대여소별 최신 snapshot 조회 확인
- `bikes_now > capacity`인 경우 `docks_now = 0` 처리 확인
- 광진구·성동구 실제 수집 데이터 기반 응답 확인

### 5. 향후 작업

- 실제 Python 예측 모델 API 연동
- Mock Prediction Service를 실제 모델 호출 로직으로 교체
- 예측 결과를 활용한 사용자 대여소 추천 로직 구현
- 운영자용 부족/포화 대여소 및 재배치 추천 로직 구현
