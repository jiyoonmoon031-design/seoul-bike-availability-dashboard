function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function expectedFromCurrent(
  station,
  leg,
  index,
) {
  const capacity =
    Number(station.capacity ?? 20);

  const bikesNow =
    Number(station.bikes_now ?? 0);

  /*
   * Week 08 UI contract validation only.
   * 실제 서비스에서는 backend recommendation endpoint가
   * Python recommendation 결과를 반환해야 한다.
   */
  const demoDelta =
    leg === "origin"
      ? [-0.8, 0.4, -1.2][index] ?? 0
      : [0.6, -0.5, 0.2][index] ?? 0;

  const bikesExpected = clamp(
    bikesNow + demoDelta,
    0,
    capacity,
  );

  return {
    bikesNow,
    docksNow: capacity - bikesNow,
    bikesExpected,
    docksExpected:
      capacity - bikesExpected,
  };
}

function scoreDemo(
  station,
  available,
) {
  const distance =
    Number(station.distance_m ?? 800);

  const distanceScore =
    1 -
    Math.min(distance / 800, 1);

  const availabilityScore =
    Math.min(
      Math.max(available, 0) / 3,
      1,
    );

  const distanceComponent =
    0.5 * distanceScore;

  const availabilityComponent =
    0.5 * availabilityScore;

  return {
    score:
      distanceComponent +
      availabilityComponent,

    score_breakdown: {
      distance:
        distanceComponent,
      availability:
        availabilityComponent,
    },
  };
}

export function buildRecommendationMock(
  stations,
  leg,
) {
  const etaMin =
    leg === "origin"
      ? Math.max(
          1,
          Number(
            stations[0]?.walk_min ?? 6,
          ),
        )
      : 30;

  const recommendations =
    stations.map((station, index) => {
      const inventory =
        expectedFromCurrent(
          station,
          leg,
          index,
        );

      const available =
        leg === "origin"
          ? inventory.bikesExpected
          : inventory.docksExpected;

      const scoring =
        scoreDemo(
          station,
          available,
        );

      return {
        ...station,

        bikes_now:
          inventory.bikesNow,

        docks_now:
          inventory.docksNow,

        bikes_expected:
          inventory.bikesExpected,

        docks_expected:
          inventory.docksExpected,

        score:
          scoring.score,

        score_breakdown:
          scoring.score_breakdown,
      };
    });

  recommendations.sort(
    (a, b) =>
      b.score - a.score ||
      a.distance_m - b.distance_m,
  );

  return {
    leg,
    eta_min: etaMin,

    effective_horizon: {
      method: "interpolation",
      anchors:
        etaMin <= 15
          ? [0, 15]
          : etaMin <= 30
            ? [15, 30]
            : etaMin <= 60
              ? [30, 60]
              : [60, 60],

      value_at:
        etaMin,
    },

    recommendations:
      recommendations
        .slice(0, 3)
        .map(
          (station, index) => ({
            ...station,
            rank: index + 1,
          }),
        ),

    mock: true,
  };
}
