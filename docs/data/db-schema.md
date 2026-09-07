# Week 02 DB 스키마

## 1. 개요

현재 데이터베이스는 광진구·성동구 대상 대여소의 기본정보와
실시간 자전거 가용 현황 스냅샷을 저장한다.

예측 및 추천 결과 저장 구조는 향후 구현을 위한 설계 초안이며,
현재 데이터베이스에는 아직 구현되지 않았다.

## 2. station

광진구·성동구 대상 대여소의 기본정보를 저장한다.

| 컬럼         | 타입         | NULL | 키  | 설명                                      |
| ------------ | ------------ | ---- | --- | ----------------------------------------- |
| station_id   | varchar(20)  | NO   | PK  | 대여소 식별자                             |
| station_name | varchar(255) | NO   |     | 대여소명                                  |
| address      | varchar(255) | YES  |     | 대여소 주소                               |
| district     | varchar(20)  | NO   |     | 자치구                                    |
| latitude     | double       | NO   |     | 위도                                      |
| longitude    | double       | NO   |     | 경도                                      |
| capacity     | int          | YES  |     | 실시간 따릉이 데이터에서 조회한 거치대 수 |

## 3. station_snapshot

5분 주기로 수집한 대여소별 실시간 자전거 가용 현황을 저장한다.

| 컬럼            | 타입        | NULL | 키  | 설명                  |
| --------------- | ----------- | ---- | --- | --------------------- |
| station_id      | varchar(20) | NO   | PK  | 대여소 식별자         |
| collected_at    | datetime(6) | NO   | PK  | 스냅샷 수집 시각      |
| bikes_available | int         | NO   |     | 이용 가능한 자전거 수 |
| capacity        | int         | YES  |     | 수집 시점의 거치대 수 |

기본키(PK): `(station_id, collected_at)`

## 4. 테이블 관계

`station_snapshot.station_id`는 `station.station_id`에서 사용하는
동일한 대여소 식별자를 기준으로 연결한다.

하나의 대여소는 시간에 따라 여러 개의 스냅샷을 가질 수 있다.

`station (1) → station_snapshot (N)`

## 5. 향후 저장 구조 초안

다음 스키마는 향후 예측 및 추천 결과를 저장하기 위한 설계 초안이다.
현재 데이터베이스에는 아직 구현되지 않았다.

Model–Backend 및 Backend–Frontend JSON 인터페이스 명세를 기준으로 작성하였다.

### prediction

예측 기준 시각과 예측 구간별 대여소 예측 결과를 저장하기 위한 구조이다.

| 컬럼           | 설명                                                   |
| -------------- | ------------------------------------------------------ |
| request_id     | 예측 요청 식별자                                       |
| station_id     | 대여소 식별자                                          |
| base_time      | 예측 기준 시각                                         |
| horizon_min    | 예측 구간(15, 30, 60분)                                |
| model_version  | 예측에 사용된 모델 버전                                |
| source         | 예측 결과 출처 (`model`, `baseline_fallback`, `cache`) |
| capacity       | 예측에 사용된 거치대 수                                |
| bikes_now      | 예측 기준 시점의 자전거 수                             |
| delta_net      | 예측된 자전거 순변화량                                 |
| bikes_expected | 예측된 자전거 수                                       |
| docks_expected | 예측된 반납 가능 거치 공간 수                          |

`delta_net`의 부호 규약은 모델의 예측 타깃 및 JSON 인터페이스 명세와
함께 최종 확정할 예정이다.

하나의 예측 요청에는 여러 대여소와 여러 예측 구간의 결과가 포함될 수 있다.

`station_id`는 `station.station_id`를 기준으로 연결한다.

### recommendation

추천 결과는 운영자용 재배치 추천과 이용자용 대여소 추천을 구분하여
저장하는 방향으로 설계한다.

#### 운영자 재배치 추천

Backend–Frontend 운영자 재배치 인터페이스를 기준으로 다음 필드를
저장 후보로 정의한다.

- `base_time`
- `horizon_min`
- 부족/여유 대여소 정보
- 예상 자전거 수 및 예상 반납 가능 거치 공간 수
- 우선순위 및 위험도 정보
- 출발/도착 대여소
- 권장 이동 대수
- 대여소 간 거리

#### 이용자 대여소 추천

Backend–Frontend 이용자 추천 인터페이스를 기준으로 다음 필드를
저장 후보로 정의한다.

- `base_time`
- `leg`
- `eta_min`
- `station_id`
- `rank`
- `distance_m`
- `walk_min`
- `bikes_expected`
- `docks_expected`
- `score`
- 추천 사유

추천 로직이 구현되는 단계에서 실제 테이블 구조와 데이터 보존 정책을
최종 확정할 예정이다.
