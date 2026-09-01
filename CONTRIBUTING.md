# Contributing

본 저장소의 모든 개발 작업은 GitHub Issue와 Pull Request를 기준으로 관리합니다.

## 1. Branch Structure

장기 유지 브랜치는 두 개만 사용합니다.

```text
main
└── develop
    └── short-lived task branches
```

### `main`

- 주차별 내부 검토가 완료된 안정 버전
- 교수 미팅, 중간점검, 최종 발표 기준
- 일반 개발 작업을 직접 수행하지 않음

### `develop`

- 팀 개발 결과의 통합 브랜치
- 일반 작업 Pull Request의 기본 대상

### Task Branch

Issue 하나당 하나의 작업 브랜치를 사용합니다.

예:

```text
data/realtime-snapshot
data/weather-ingestion
model/feature-engineering
model/baseline
model/lightgbm
backend/prediction-api
backend/rebalancing-api
frontend/operator-dashboard
frontend/user-dashboard
feat/llm-insight
test/backtesting
docs/model-backend-interface
fix/api-timeout
```

사람 이름별 장기 브랜치 또는 `model`, `backend`, `frontend` 영구 브랜치는 만들지 않습니다.

---

## 2. Standard Workflow

```text
Issue 확인
→ develop 최신화
→ Task Branch 생성
→ 구현
→ 테스트
→ Commit
→ Push
→ Pull Request to develop
→ 교차 Review
→ 수정
→ Merge
→ Branch 삭제
```

작업 시작:

```bash
git switch develop
git pull origin develop
git switch -c <branch-name>
```

작업 완료:

```bash
git add .
git commit -m "<type>: <summary>"
git push -u origin <branch-name>
```

GitHub에서:

```text
<head task branch> → develop
```

Pull Request를 생성합니다.

---

## 3. Weekly Release Workflow

주차의 모든 Task PR이 `develop`에 반영된 후:

```text
develop → main
```

Pull Request를 생성합니다.

- PR 생성: 해당 주차 제출 책임자
- 검토: 해당 주차 내부 검토 담당자
- 검토 완료 후 main merge
- 교수 미팅 기준 버전은 main 사용

주차 종료 후 필요 시 tag를 생성합니다.

```bash
git switch main
git pull origin main

git tag -a w01 -m "Week 01 approved snapshot"
git push origin w01
```

`w02`, `w03` 순으로 사용합니다.

---

## 4. Commit Convention

형식:

```text
<type>: <summary>
```

사용 type:

| Type | 용도 |
|---|---|
| `feat` | 새 기능 |
| `fix` | 오류 수정 |
| `data` | 데이터 수집·정제 |
| `model` | 모델 개발·실험 |
| `test` | 테스트·검증 |
| `docs` | 문서 |
| `refactor` | 기능 변경 없는 코드 개선 |
| `chore` | 저장소·환경 설정 |

예:

```text
feat: add realtime station snapshot collector
data: add station master preprocessing
model: add LightGBM forecasting model
test: validate 30-minute prediction performance
docs: define model backend response schema
fix: handle Seoul API timeout
```

---

## 5. Pull Request Rules

일반 작업 PR:

```text
Task Branch → develop
```

주차 마감 PR:

```text
develop → main
```

PR에는 최소 다음을 기록합니다.

- Related Issue
- Week
- 작업 내용
- 테스트 방법
- 결과
- Interface 변경 여부
- `params.yaml` 변경 여부

코드 작성자와 Reviewer는 동일할 수 없습니다.

본인이 직접 작성한 항목은 본인이 최종 승인하지 않습니다.

---

## 6. Secrets

다음을 GitHub에 commit하지 않습니다.

- `.env`
- API Key
- Password
- Token
- 개인 credential
- 대용량 원천 데이터
- 실시간 snapshot DB
- 모델 checkpoint
- 가상환경
- `node_modules`

실제 credential은 `.env`에 저장하고 Git에는 `.env.example`만 공유합니다.
