import {
  buildRecommendationMock,
} from "../mocks/recommendationMock";

export async function getRecommendationPreview(
  stations,
  leg,
) {
  /*
   * 조성은 backend recommendation endpoint가
   * 준비되기 전 Week 08 frontend 계약 검증용.
   *
   * frontend는 최종적으로 score를 계산하지 않고
   * backend response를 그대로 표시한다.
   */
  return buildRecommendationMock(
    stations,
    leg,
  );
}
