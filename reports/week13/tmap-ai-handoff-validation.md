# TMAP 지도와 AI 개발 터널 검증

2026-11-25 KST에 통합 브랜치를 검증했다. TMAP 개발 키와 최종 서버 설정은 백엔드 담당자가 관리한다.

| 확인 항목 | 결과 |
| --- | --- |
| 최신 FastAPI 로컬 `/health` | HTTP 200, `ready=true` |
| 개발용 ngrok `/health` | 인증 없음 HTTP 401, Basic Auth 적용 HTTP 200 및 `ready=true` |
| 최신 Spring → 인증된 ngrok → FastAPI | 로컬 DB의 대여소 1개에 15/30/60분 예측을 요청해 HTTP 200 및 모델 버전 확인 |
| 최신 Spring `/api/v1/stations/status` | HTTP 200, 180개 대여소 |
| Spring 실행 중 OpenAPI와 저장소 명세 | 경로 16개 일치 |
| 브라우저 회귀 테스트 | 7개 통과. 지도 SDK와 API 응답을 대체한 테스트에서 세 추천의 TMAP 입력은 실선, 직선 대체 입력은 점선으로 표시됨 |
| 서버·빌드 | Python 94개 통과, Gradle 테스트·JAR 생성 성공, 프런트엔드 ESLint·TypeScript·Vite 빌드 성공 |
| 이 Mac의 기존 TMAP 설정 | 공식 보행자 경로 API에서 HTTP 403 `INVALID_API_KEY`. 기존 Spring 경로 API에서 `straight_line` 두 점을 반환함 |

백엔드 담당자 환경의 TMAP 실경로와 EC2 배포는 별도 검증 항목이다. 공개 운영 배포는 실행하지 않았다.
