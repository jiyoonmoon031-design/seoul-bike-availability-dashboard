# Data Directory

프로젝트 데이터는 다음 원칙으로 관리합니다.

```text
sample/      GitHub에 공유 가능한 재현용 소량 샘플
raw/         원천 데이터 — Git 추적 제외
interim/     중간 처리 데이터 — Git 추적 제외
processed/   모델 입력용 처리 데이터 — Git 추적 제외
```

대용량 원천 데이터와 지속적으로 적재되는 실시간 station snapshot은 GitHub repository에 직접 저장하지 않습니다.

데이터 원천, 수집 방법, 기간 및 재현 절차는 프로젝트 진행 과정에서 본 문서에 기록합니다.
