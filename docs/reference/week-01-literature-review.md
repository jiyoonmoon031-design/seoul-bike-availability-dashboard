# Week 01 선행연구 분석

## 1. 목적과 검토 범위

서울시 공공자전거, 특히 따릉이 수요예측과 직접 관련된 국내 연구를 검토하고 다음 설계 결정에 반영한다.

- 예측 대상: 대여량 중심 수요인지, 대여소별 재고·가용성인지
- 예측 공간 단위: 서울시 전체, 시간대, 대여소 또는 대여소군
- 예측 시간 단위와 horizon
- 기상·달력·공간 변수를 포함한 입력 구성
- 모델 계열과 비교 기준
- 평가 지표와 검증 분할
- 본 프로젝트에서 보완할 연구 공백

논문 원문에 접근하지 못한 경우에는 Crossref 서지정보와 공개 초록에서 확인되는 내용만 기록했으며, 정확한 수치나 세부 전처리는 추정하지 않는다.

## 2. 연구별 요약

| 연구 | 데이터·대상 | 방법 | 평가·주요 결과 | 본 프로젝트와의 관련성 |
|---|---|---|---|---|
| Sathishkumar & Cho (2020), *A rule-based model for Seoul Bike sharing demand prediction using weather data* | 서울 따릉이 수요와 기상 변수 | 기상정보를 이용한 rule-based 예측 | 기상 조건을 활용한 수요예측 가능성을 검토 | 날씨를 입력 feature로 포함할 근거를 제공하지만, 규칙 기반 결과를 대여소별 단기 순재고 변화 예측의 기준 모델로 사용하기에는 한계가 있다. |
| Hong et al. (2021), *Estimation of Shared Bicycle Demand Using the SARIMAX Model: Focusing on the COVID-19 Impact of Seoul* | 서울 공유자전거 수요, 코로나19 전후 영향 | 외생변수를 포함하는 SARIMAX 시계열 모형 | 코로나19라는 구조적 변화가 수요에 미친 영향을 고려 | 외생변수와 구조적 변화 처리가 중요하다는 근거다. 단, SARIMAX의 집계 시계열 접근은 station별 재고 제약과 개별 대여소 이질성을 직접 표현하기 어렵다. |
| Min & Jung (2021), *Comparative study of prediction models for public bicycle demand in Seoul* | 서울 공공자전거 수요 | 복수 예측모형 비교 | 제목과 서지정보로 서울 공공자전거 모델 비교 연구임을 확인 | 단일 모델의 성능보다 동일 데이터·동일 분할에서 모델을 비교하는 설계가 필요하다는 근거다. 세부 모델·수치 인용은 원문 확인 후 보완한다. |
| Kim & Lim (2022), *Development of Demand Forecasting Algorithms based on ARIMA Model Variations for Public Shared Bike Service in Seoul* | 서울 공공자전거 이용 수요 | ARIMA 변형 알고리즘 | ARIMA 계열을 활용한 서울 공공자전거 수요예측 알고리즘 개발 | 계절성과 자기상관을 활용하는 통계적 baseline 후보를 제공한다. 다만 본 프로젝트는 15/30/60분 horizon과 결측 source interval을 별도로 관리해야 한다. |
| Somtham, Kim & Kim (2023), *An Analysis of the Machine Learning Model-Based Demand Prediction for Public Bike Sharing Services in Seoul* | 서울 시간대별 자전거 대여 수요 | SVC, KNN, Decision Tree, Random Forest, Gradient Boosting 5개 분류모형과 Grid Search CV | 시간대별 대여 수요를 3개 class로 나누어 예측했으며 공개 초록상 SVC와 Gradient Boosting이 상대적으로 우수 | 수요를 class로 예측하는 접근은 가용성 판정과 연결되지만, 연속적인 순재고 변화량 예측의 오차와는 목적이 다르다. 본 프로젝트는 회귀 예측과 availability classification을 분리한다. |

## 3. 기존 연구에서 확인되는 공통 패턴

### 3.1 입력 변수

기존 연구는 대체로 과거 이용량, 시간대·요일 같은 달력 변수, 기상 변수를 조합한다. 따라서 본 프로젝트의 다음 후보는 선행연구와 일관된다.

- 현재 관측 재고
- 최근 15·30·60분 대여량·반납량
- 시간대, 요일, 공휴일, peak 여부
- 기온, 강수량, 습도, 풍속

기상 변수는 수요와의 상관이 인과효과를 의미하지 않으므로 EDA에서는 기술통계와 상관관계로 보고하고, 예측 성능 개선 여부는 시간순 holdout에서 별도로 검증한다.

### 3.2 모델 계열

문헌에서 확인되는 접근은 다음 세 가지다.

1. **규칙 기반**: 해석 가능하고 운영에 적용하기 쉽지만, 비선형 상호작용과 station별 차이를 충분히 반영하기 어렵다.
2. **통계적 시계열**: ARIMA/SARIMAX는 자기상관과 외생변수를 명시적으로 다루며 강한 baseline이 될 수 있다. 반면 station 수가 많고 관측 간격·결측이 불규칙하면 station별 모델 관리가 복잡해진다.
3. **머신러닝 분류·회귀**: 여러 feature의 비선형 관계를 학습할 수 있다. 그러나 분류 accuracy만으로는 실제 자전거 수 오차나 품절 위험을 설명하기 어렵고, 시간순 분할과 leakage 통제가 필수다.

## 4. 본 프로젝트 설계에 반영할 점

### 4.1 예측 target을 대여량이 아닌 순재고 변화량으로 정의

기존 연구 다수는 대여 수요 또는 이용량을 예측한다. 본 프로젝트는 서비스 목적이 미래 가용성 판단과 재배치 지원이므로 다음 target을 사용한다.

```text
Delta(station_id, t, h) = return_count - rent_count
```

`h`는 15, 30, 60분이며, 예측 결과는 미래 예상 자전거 수와 빈 거치대 수로 변환한다. 이를 통해 대여량이 많아도 반납량이 함께 많은 대여소를 단순히 부족하다고 판단하는 문제를 줄인다.

### 4.2 대여소 단위와 시간순 검증

서울시 전체 또는 시간대 집계만으로 평가하면 특정 대여소의 품절·과잉 문제를 놓칠 수 있다. 따라서 `station_id × base_time`을 분석 단위로 고정하고, train/validation/test를 시간순으로 분리한다.

- train: validation 이전 기간
- validation: test 직전 14개 완결일
- test: 최근 28개 완결일
- feature에는 기준시각 `t`까지의 정보만 사용
- 미래 target과 미래 weather observation을 feature에서 제외

### 4.3 baseline과 지표를 분리

기존 연구의 모델 비교 결과를 그대로 가져오기보다, 동일한 데이터 계약에서 재현 가능한 baseline을 먼저 둔다.

- 주 baseline: 동일 station·horizon의 persistence, `Delta(t-h, h)`
- 보조 baseline: 순재고 변화량 0
- 회귀: MAE, RMSE, naive 대비 MAE 개선율
- 가용성: Precision, Recall, F1
- 추천: 대여/반납 Top-3 hit rate
- 재배치: shortage/overflow score reduction

분류 accuracy만으로 모델을 선택하지 않는 이유는, 가용 자전거 부족 사례의 누락 비용과 대여소별 수요 규모가 다르기 때문이다.

### 4.4 결측과 운영 개입 처리

선행연구 결과를 비교할 때 source gap을 0 수요로 채웠는지 확인해야 한다. 본 프로젝트에서는 다음을 지킨다.

- missing source interval과 실제 zero activity를 구분
- 필수 target이 없는 행은 해당 horizon 평가에서 제외
- snapshot이 없는 미래값을 임의 보간하지 않음
- 재배치 개입으로 발생한 inventory 변화와 순수 이용 수요를 구분

## 5. 기존 연구의 한계와 연구 공백

1. **대여소 단위 가용성의 직접 평가 부족**: 대여량 또는 시간대별 총수요 예측이 서비스 availability로 바로 이어지지 않는다.
2. **다중 단기 horizon 비교 부족**: 15/30/60분을 동일한 station-level 계약으로 비교하고 horizon별 결측을 공개할 필요가 있다.
3. **재현 가능한 baseline 부족**: 논문별 데이터 기간, split, 전처리, baseline 정의가 다르면 모델 성능을 직접 비교할 수 없다.
4. **미래 정보 누출 위험**: random split 또는 전체 기간 통계로 feature를 만들면 실제 운영 성능이 과대평가될 수 있다.
5. **대여소 population 변화 처리 부족**: 신규·폐쇄·비활성 대여소를 하나의 모집단으로 취급하면 station 수요 분포가 왜곡될 수 있다.
6. **불균형한 운영 비용 반영 부족**: 가용성 분류에서 false negative와 false positive의 비용이 같지 않으므로 Precision/Recall/F1을 함께 보고해야 한다.

## 6. 프로젝트 적용 결론

선행연구는 기상·달력·과거 이용량 feature와 ARIMA/SARIMAX·머신러닝 비교의 필요성을 뒷받침한다. 그러나 본 프로젝트의 차별점은 모델 자체보다 다음 평가 계약에 있다.

- 광진구·성동구의 station-level 분석
- KST 기준 15/30/60분 단기 horizon
- 순재고 변화량 target
- missing source와 zero activity의 분리
- persistence 및 zero baseline과의 비교
- 회귀, 가용성, 추천, 재배치 지표의 분리
- 시간순 holdout과 leakage 검사

따라서 1차 모델링에서는 persistence baseline을 기준으로 feature 기반 회귀모형을 비교하고, 이후 필요할 때 SARIMAX 또는 tree-based model을 보조 비교하는 순서가 합리적이다. 논문 간 절대 성능 수치를 직접 비교하지 않고, 동일한 내부 데이터·분할·지표에서 재현한 결과만 최종 모델 선택에 사용한다.

## 7. 참고문헌

1. Sathishkumar, V. E., & Cho, Yongyun. (2020). *A rule-based model for Seoul Bike sharing demand prediction using weather data*. European Journal of Remote Sensing, 53, 166-183. https://doi.org/10.1080/22797254.2020.1725789
2. Hong, Jungyeol, Han, Eunryong, Choi, Changho, Lee, Minseo, & Park, Dongjoo. (2021). *Estimation of Shared Bicycle Demand Using the SARIMAX Model: Focusing on the COVID-19 Impact of Seoul*. The Journal of The Korea Institute of Intelligent Transport Systems, 20, 10-21. https://doi.org/10.12815/kits.2021.20.1.10
3. Min, Soah, & Jung, Yoonsuh. (2021). *Comparative study of prediction models for public bicycle demand in Seoul*. Journal of the Korean Data and Information Science Society, 32, 585-592. https://doi.org/10.7465/jkdi.2021.32.3.585
4. Kim, Do Hee, & Lim, Heejong. (2022). *Development of Demand Forecasting Algorithms based on ARIMA Model Variations for Public Shared Bike Service in Seoul*. International Telecommunications Policy Review, 29, 49-74. https://doi.org/10.37793/itpr.29.1.3
5. Somtham, Athip, Kim, Chang-Jae, & Kim, Jong-Hyuk. (2023). *An Analysis of the Machine Learning Model-Based Demand Prediction for Public Bike Sharing Services in Seoul*. The e-Business Studies, 24, 31-47. https://doi.org/10.20462/tebs.2023.6.24.3.31

## 8. 검토 한계

- 일부 국내 학술 DB는 원문·초록을 기관 인증 뒤에 제공하므로, 공개적으로 확인 가능한 범위를 넘는 정확한 성능 수치와 feature 목록은 이 문서에 단정하지 않았다.
- 논문 간 데이터 기간, 공간 단위, target 정의, 평가 분할이 다르므로 본 프로젝트 결과와 문헌 성능을 직접 순위 비교하지 않는다.
- 원문 확보 후 각 연구의 표본 기간, 세부 변수, train/test split, MAE/RMSE 또는 accuracy 수치를 보완할 수 있다.
