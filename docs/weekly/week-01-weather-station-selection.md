# Week 01 Weather Station Selection

## Decision

광진구·성동구 서비스 권역의 대표 기상 관측지점으로 기상청 방재기상관측(AWS) **성동(지점번호 421)** 을 사용한다.

```yaml
WEATHER_STATION: 421
```

## Service-area center

현재 저장소에는 자치구 경계 또는 확정된 따릉이 대여소 마스터가 없으므로, 재현 가능한 Week 1 기준점으로 권역 내부 AWS인 광진(413)과 성동(421)의 WGS84 좌표를 동일 가중 평균했다.

```text
latitude  = (37.53660 + 37.54721) / 2 = 37.541905
longitude = (127.08524 + 127.03885) / 2 = 127.062045
```

이 좌표는 행정구역 폴리곤의 면적 중심이 아니라 **관측망 기준 운영 중심점**이다. 추후 확정된 대여소 마스터가 들어오면 서비스 대상 대여소 좌표의 중심점으로 재검증한다.

## Adjacent AWS candidates

기상청 관측지점 메타데이터에서 권역 내부 2개 지점과 인접한 동대문·중랑 지점을 후보로 확인했다. 거리는 위 운영 중심점과 각 AWS 사이의 Haversine 거리다.

| Station | Name | WGS84 latitude | WGS84 longitude | Observation start | Distance |
|---:|---|---:|---:|---|---:|
| 413 | 광진 | 37.53660 | 127.08524 | 1994-12-08 | 2.128 km |
| 421 | 성동 | 37.54721 | 127.03885 | 2000-08-22 | 2.128 km |
| 408 | 동대문 | 37.58463 | 127.06036 | 1994-12-07 | 4.753 km |
| 409 | 중랑 | 37.58551 | 127.08682 | 1994-12-07 | 5.318 km |

공식 지점 상세정보:

- [광진(413)](https://data.kma.go.kr/tmeta/stn/selectStnDetail.do?isSelectStn=Y&pgmNo=82&stdStnNo=413)
- [성동(421)](https://data.kma.go.kr/tmeta/stn/selectStnDetail.do?isSelectStn=Y&pgmNo=82&stdStnNo=421)
- [동대문(408)](https://data.kma.go.kr/tmeta/stn/selectStnDetail.do?isSelectStn=Y&pgmNo=82&stdStnNo=408)
- [중랑(409)](https://data.kma.go.kr/tmeta/stn/selectStnDetail.do?isSelectStn=Y&pgmNo=82&stdStnNo=409)

## Missing-data validation

검증일은 2026-08-25이며, 아직 끝나지 않은 2026년 8월을 제외한 최근 12개 완결 월인 **2025-08-01~2026-07-31**을 사용했다.

기상청 데이터품질리포트의 AWS 1분 자료에서 다음 네 요소를 조회했다.

- 0.5 mm 일 누적 강수량
- 1분 평균 기온
- 1분 평균 풍속
- 1분 평균 상대습도

각 지점·요소의 월별 `결측자료수`를 합산하고 다음 식으로 결측률을 계산했다.

```text
missing rate (%) = sum(missing observations) / sum(expected observations) * 100
```

모든 요소에서 지점별 이론자료수는 각각 525,600건이었다. 동일 지점에서는 네 요소의 결측자료수가 같아 요소별 결측률도 동일했다.

| Station | Name | Missing / expected per element | Missing rate | Under 5% |
|---:|---|---:|---:|:---:|
| 408 | 동대문 | 41 / 525,600 | 0.0078% | Yes |
| 409 | 중랑 | 36 / 525,600 | 0.0068% | Yes |
| 413 | 광진 | 4,170 / 525,600 | 0.7934% | Yes |
| 421 | 성동 | 110 / 525,600 | 0.0209% | Yes |

출처: [기상청 데이터품질리포트](https://data.kma.go.kr/data/qualityInfo/qcReportList.do). 기상청 정의에 따라 결측자료율에는 결측자료와 미수집 자료가 포함된다. 오류자료는 별도의 오류자료율로 관리되므로 위 결측률 분자에는 포함하지 않았다.

## Selection rationale

1. 광진(413)과 성동(421)은 모두 서비스 권역 내부에 있고 운영 중심점과의 거리가 동일하다.
2. 두 지점 모두 최근 12개월 결측률 5% 미만 기준을 충족한다.
3. 성동(421)의 결측률 0.0209%가 광진(413)의 0.7934%보다 낮다.
4. 따라서 공간 대표성이 동률인 두 내부 후보 중 자료 완전성이 더 높은 **성동(421)** 을 최종 선택한다.

## Revalidation rule

- 매월 적재 품질 점검 시 직전 12개 완결 월 결측률을 다시 계산한다.
- 성동(421)의 결측률이 5% 이상이 되면 광진(413)을 우선 대체 후보로 재평가한다.
- 대여소 마스터가 확정되면 대여소 좌표 기반 권역 중심점으로 후보 거리를 다시 계산한다.
