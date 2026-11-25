# Interface Documentation

이 디렉터리는 시스템 계층 간 데이터 계약의 기준 문서를 저장합니다.

현재 백엔드·AI 연동은 [API 사용 가이드](api.md) 및 [백엔드 OpenAPI](../openapi.json)를 참고하세요.

## 관리 대상

- Model → Backend
- Backend → Frontend
- Rebalancing response
- Recommendation response
- API request/response
- timezone 규약
- station_id 규약
- null 규약
- model version 규약
- fallback `source` 규약

## 기본 원칙

Interface 변경은 코드 변경과 동일한 PR에서 반영합니다.

다음 방식은 금지합니다.

```text
코드만 변경
→ 문서 미수정
→ 다른 팀원이 기존 schema를 기준으로 개발
```

## 권장 파일

```text
model-backend.md
backend-frontend.md
api-schema.md
parameter-contract.md
```

1주차에 Model ↔ Backend JSON Interface를 우선 확정합니다.
