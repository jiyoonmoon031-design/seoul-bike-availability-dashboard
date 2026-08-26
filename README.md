# Seoul Bike Availability Dashboard

광진·성동구 따릉이 단기 가용성 예측 기반 재배치 지원·경로형 대여소 추천 통합 대시보드

## Overview

본 프로젝트는 서울시 공공자전거 따릉이의 대여소별 단기 순재고 변화량을 예측하고, 동일한 예측 결과를 이용하여 다음 두 가지 기능을 제공하는 웹 기반 통합 대시보드를 개발하는 프로젝트입니다.

- 운영자: 부족·포화 위험 대여소 탐지 및 재배치 우선순위·이동 매칭 제공
- 이용자: 출발·도착 예상 시점의 가용성을 고려한 대여소 Top-3 추천

서비스 제공 대상과 모델 학습 대상은 모두 광진구·성동구 대여소로 한정합니다.

## Core Prediction

모델의 예측 대상은 대여소별 미래 순재고 변화량입니다.

```text
Δ(station_id, t, h) = 반납량 - 대여량

미래 예상 자전거 수
B(t+h) = clip(B_now + Δ, 0, capacity)

미래 예상 빈 거치대 수
E(t+h) = capacity - B(t+h)
```

예측 구간은 다음과 같습니다.

```text
15분 / 30분 / 60분
```

하나의 최종 예측 모델을 운영자 기능과 이용자 기능에서 공통으로 사용합니다.

## System Architecture

```text
서울 열린데이터광장
실시간 따릉이 대여정보
기상 데이터
달력 데이터
Kakao Local / Map API
        │
        ▼
Data Collection
        │
        ▼
Preprocessing & Feature Engineering
        │
        ▼
Short-term Net Inventory Forecast Model
        │
        ├───────────────┐
        ▼               ▼
Rebalancing        Station Recommendation
        │               │
        └───────┬───────┘
                ▼
          LLM Explanation
                │
                ▼
       Web Dashboard
   Operator / User Tabs
```

LLM은 예측이나 점수 계산에 사용하지 않으며, 기존 로직이 계산한 구조화된 결과를 자연어로 설명하는 역할만 수행합니다.

## Project Scope

### Service Area

- Gwangjin-gu
- Seongdong-gu

### Model Training Area

- Gwangjin-gu
- Seongdong-gu

### Prediction Horizons

- 15 minutes
- 30 minutes
- 60 minutes

## Data Sources

주요 데이터는 다음과 같습니다.

| Data | Purpose |
|---|---|
| Seoul Bike station master | Station ID, coordinates, capacity |
| Rental / return history | Net inventory change target |
| Real-time station status | Current inventory and validation snapshots |
| Weather data | Prediction features |
| Calendar data | Weekday, holiday, time-pattern features |
| Kakao Local / Map API | Search, coordinates, and map visualization |

UCI Seoul Bike Sharing Demand 데이터는 초기 baseline 방법론 검증에만 사용하며 최종 모델 학습 데이터에는 포함하지 않습니다.

## Repository Structure

```text
src/          Core data, model, recommendation and rebalancing logic
backend/      Backend API and service integration
frontend/     Operator and user dashboard
scripts/      Data collection and operational scripts
notebooks/    EDA and modeling experiments
tests/        Unit and integration tests
config/       Shared project parameters
docs/         Interface, architecture and project documentation
reports/      Weekly, model and validation outputs
data/         Local datasets and reproducibility samples
```

## Team

| Member | Main Responsibility |
|---|---|
| 문지윤 | AI modeling, feature engineering, rebalancing logic, operator dashboard |
| 조성은 | Backend, database, external APIs, service integration |
| 김수연 | Model validation, recommendation validation, user dashboard |

주차별 산출물 제출 책임 및 내부 검토 담당자는 Master Execution Guide의 로테이션을 따릅니다.

## Development Workflow

```text
Issue
  ↓
Feature Branch
  ↓
Implementation
  ↓
Test
  ↓
Pull Request
  ↓
Cross Review
  ↓
Revision
  ↓
Merge to main
```

자신이 작성한 산출물은 본인이 최종 검토하지 않습니다.

### Branch Naming Examples

```text
feat/data-pipeline
feat/feature-engineering
feat/model-lightgbm
feat/realtime-api
feat/rebalancing
feat/operator-dashboard
feat/user-dashboard
feat/llm-insight
test/backtesting
fix/api-fallback
```

## Environment

Python version:

```text
Python 3.11
```

초기 환경 설정:

```bash
git clone <repository-url>
cd seoul-bike-availability-dashboard

python3.11 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
```

Backend 및 frontend의 구체적인 실행 명령은 Week 1 기술 스택 확정 후 추가합니다.

## Configuration

프로젝트 공통 파라미터는 다음 파일에서 관리합니다.

```text
config/params.yaml
```

모델·추천·재배치 로직에서 사용하는 주요 파라미터를 코드 내부에 직접 하드코딩하지 않습니다.

## Evaluation

주요 평가 항목:

| Area | Metric |
|---|---|
| Forecasting | MAE / RMSE |
| Baseline comparison | Improvement over naive baselines |
| Availability classification | Precision / Recall / F1 |
| User recommendation | Top-3 availability hit rate |
| Rebalancing | Shortage-score reduction |
| Reliability | Snapshot completeness / API fallback |
| LLM | Invalid-output rejection rate |

평가는 ALL / ACTIVE / PEAK / ACTIVE ∩ PEAK segment를 구분하여 수행합니다.

## Project Schedule

```text
Week 1–3   Data infrastructure and feature engineering
Week 4–6   Forecasting model and backend integration
Week 7–9   Operator/User dashboard and system integration
Week 10    Validation and backtesting
Week 11    Service stabilization
Week 12    Final demo and report
```

## Documentation

프로젝트 실행 기준 문서는 다음 위치에서 관리합니다.

```text
docs/master-guide.md
```

인터페이스 정의 및 변경사항은 `/docs/interface`에서 관리합니다.

## Security

API keys and credentials must never be committed to this repository.

실제 credential은 `.env`에 저장하며 Git에는 `.env.example`만 포함합니다.

## Status

Academic project for the 2026 Fall semester.

Project period:

```text
2026-09-01 ~ 2026-12-11
```

## Team Workflow

팀 개발 규칙과 작업 위치는 다음 문서를 기준으로 합니다.

- [Team Work Guide](docs/team-work-guide.md)
- [Contributing](CONTRIBUTING.md)
- [Interface Documentation](docs/interface/README.md)
- [Weekly Technical Deliverables](docs/weekly/README.md)

일반 개발 흐름:

```text
Issue
→ Task Branch
→ Pull Request to develop
→ Cross Review
→ Merge to develop
→ Weekly develop-to-main PR
→ Internal Review
→ Merge to main
```

장기 유지 브랜치는 `main`, `develop` 두 개만 사용합니다.
