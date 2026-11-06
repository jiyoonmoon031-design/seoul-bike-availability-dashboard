---
title: "미래 가용성 기반 서울 따릉이 통합 대시보드"
subtitle: "광진구·성동구 단기 예측, 재배치 지원 및 이용자 Top-3 추천"
author: "문지윤 · 조성은 · 김수연"
date: "2026 Fall"
aspectratio: 169
lang: ko-KR
---

# 문제와 목표

- 현재 재고만 보면 사용자가 도착할 때의 품절·포화를 알 수 없음
- 15·30·60분 순재고 변화를 예측해 두 기능에 공통 활용
- 운영자: 부족·포화 위험과 재배치 우선순위
- 이용자: 출발 자전거·도착 빈 거치대 Top-3
- 대상: 광진구·성동구 기준 221개 대여소

---

# 시스템 구조

```text
서울시 실시간·이용이력 + 기상·달력 + Kakao
                    ↓
          수집·전처리·특성 생성
                    ↓
     Random Forest 15/30/60분 예측
          ↙                         ↘
 운영자 재배치                    이용자 추천
          ↘                         ↙
             LLM 설명 + Web UI
```

- LLM은 계산하지 않고 구조화 결과만 설명
- 예측·점수·순위는 결정적 Python 로직으로 처리

---

# 최종 모델 검증

| Segment | 15분 | 30분 | 60분 |
|---|---:|---:|---:|
| ALL | -2.42% | +2.22% | +7.33% |
| ACTIVE | +0.88% | +5.41% | +10.52% |
| PEAK | +7.19% | +12.61% | +17.83% |
| ACTIVE ∩ PEAK | +10.71% | +16.63% | +21.92% |

![B1 대비 horizon별 MAE](reports/figures/week05_horizon_mae_vs_b1.png){width=72%}

---

# 검증 해석과 한계

- 950,455 test rows, 46 features, 12개 지표 독립 재현
- 저장값과 재계산값 최대 차이 `4.69e-12`
- ALL 15분은 B1보다 2.42% 낮음: 보편적 우수성 주장 금지
- 효과는 혼잡 시간·활동 대여소·긴 horizon에서 커짐
- 08시·17~18시와 돌발 수요 충격에서 오차 증가

![세그먼트별 B1 대비 개선율](reports/figures/week05_baseline_improvement_heatmap.png){width=70%}

---

# 이용자 추천 알고리즘

```text
distance_score = 1 - min(distance_m / 800, 1)
availability_score = min(expected_available / 3, 1)
score = 0.5 × distance_score + 0.5 × availability_score
```

- 도보 ETA에 맞춰 0·15·30·60분 예측을 선형보간
- 출발: 미래 예상 자전거 수 `bikes_expected`
- 도착: 미래 예상 빈 거치대 수 `docks_expected`
- 점수 → 가용 수량 → 거리 → ID 순으로 Top-3 결정

---

# 이용자 화면

![출발·도착 추천 화면](reports/final/assets/user-recommendation-ui.png){width=82%}

- 독립 장소검색과 주변 대여소 지도
- 출발·도착 Top-3, 현재/미래 가용성, 추천 이유
- 세종대→성수역 등 대표 경로 3개 검증

---

# 운영자 화면과 재배치

![운영자 재배치 화면](reports/final/assets/operator-dashboard-ui.png){width=76%}

- 부족·공급 대여소, 이동 대수, 위험 시각, 우선순위
- PR #75 oracle CAP20: shortage 약 23.9% 감소
- 위험 대여소 약 15.2~15.4% 감소
- **oracle upper bound이며 실제 예측 기반 실현 효과가 아님**

---

# 시스템 QA 결과

- 대표 경로 3개: 검색 → 추천 → 지도 → 설명 통과
- 출발·도착 추천 카드 각 3개, 지도 marker 8개
- 짧은 검색어 오류 안내 확인
- 이용자·운영자 탭 전환 오류 발견 후 수정
- 390px 모바일 가로 overflow 없음
- 브라우저 E2E **7/7 통과**

---

# 현재 상태와 남은 검증

| 영역 | 상태 |
|---|---|
| 모델 독립 재현·오류 분석 | 완료 |
| 추천·재배치·AI API | 구현 완료 |
| 이용자·운영자 UI | 구현 및 Mock E2E 완료 |
| 추천 Top-3 공식 hit rate | hold-out snapshot 입력 대기 |
| 재배치 효과 | PR #75 리뷰 대기 |
| 실시간 DB→화면 전체 E2E | 운영환경 통합 검증 필요 |

- 추천 결과는 입력 전까지 수치를 발표하지 않음
- 확정값·provisional·pending을 명확히 구분

---

# 결론

- 하나의 미래 재고 예측을 운영자와 이용자 기능에 공통 활용
- 고수요·혼잡 구간에서 모델의 실질적 개선 확인
- 거리만이 아니라 도착 시점 가용성을 반영한 Top-3 제공
- 기능·UI·재현성 검증 완료, 실시간 통합과 추천 공식 평가가 다음 관문

**핵심 메시지:** 가까운 대여소가 아니라, 도착했을 때 실제로 사용할 수 있는 대여소를 추천한다.
