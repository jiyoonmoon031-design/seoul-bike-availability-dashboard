const places = [
  ['세종대학교', '서울 광진구 능동로 209', 37.5503, 127.0731],
  ['성수역', '서울 성동구 아차산로 100', 37.5446, 127.0559],
  ['건대입구역', '서울 광진구 아차산로 243', 37.5404, 127.0692],
  ['서울숲', '서울 성동구 뚝섬로 273', 37.5444, 127.0374],
  ['어린이대공원', '서울 광진구 능동로 216', 37.5494, 127.0812],
  ['왕십리역', '서울 성동구 왕십리광장로 17', 37.5612, 127.0371],
] as const

export function searchPlaceFixture(
  query: string,
) {
  const normalized = query.trim()

  return places
    .filter(([name]) =>
      name.includes(normalized),
    )
    .map(([
      name,
      address,
      latitude,
      longitude,
    ]) => ({
      placeName: name,
      roadAddress: address,
      address,
      latitude,
      longitude,
    }))
}

export function nearbyStationFixture(
  latitude: number,
  longitude: number,
) {
  return [
    {
      station_id: `QA-${latitude}-1`,
      station_name: '가까운 대여소',
      latitude: latitude + 0.001,
      longitude: longitude + 0.001,
      distance_m: 120,
      walk_min: 2,
      capacity: 20,
      bikes_now: 6,
    },
    {
      station_id: `QA-${latitude}-2`,
      station_name: '가용성 우수 대여소',
      latitude: latitude - 0.001,
      longitude: longitude + 0.0015,
      distance_m: 280,
      walk_min: 4,
      capacity: 25,
      bikes_now: 9,
    },
    {
      station_id: `QA-${latitude}-3`,
      station_name: '보조 대여소',
      latitude: latitude + 0.0015,
      longitude: longitude - 0.001,
      distance_m: 430,
      walk_min: 6,
      capacity: 18,
      bikes_now: 4,
    },
    {
      station_id: `QA-${latitude}-4`,
      station_name: '후순위 대여소',
      latitude: latitude - 0.002,
      longitude: longitude - 0.001,
      distance_m: 720,
      walk_min: 10,
      capacity: 15,
      bikes_now: 2,
    },
  ]
}

export function routeRecommendationFixture(
  originLatitude: number,
  originLongitude: number,
  destinationLatitude: number,
  destinationLongitude: number,
) {
  const names = [
    ['가용성 우수 출발 대여소', '반납 안정 도착 대여소'],
    ['가까운 출발 대여소', '가까운 도착 대여소'],
    ['보조 출발 대여소', '보조 도착 대여소'],
  ] as const

  return {
    routes: names.map((namePair, index) => {
      const rank = index + 1
      const originScore = 0.32 - index * 0.03
      const destinationScore = 0.31 - index * 0.03
      const etaScore = 0.12 - index * 0.01
      const walkingScore = 0.12 - index * 0.01

      return {
        rank,
        origin_station_id: `ROUTE-O-${rank}`,
        origin_station_name: namePair[0],
        destination_station_id: `ROUTE-D-${rank}`,
        destination_station_name: namePair[1],
        walk_to_origin_min: 2 + index * 2,
        bike_min: 18 + index * 2,
        walk_to_destination_min: 3 + index,
        total_eta_min: 23 + index * 5,
        score:
          originScore +
          destinationScore +
          etaScore +
          walkingScore,
        score_breakdown: {
          origin_station: originScore,
          destination_station: destinationScore,
          eta: etaScore,
          walking: walkingScore,
        },
        reason:
          '출발 자전거와 도착 빈 거치대의 미래 가용성, 양쪽 도보시간, 총 이동시간을 함께 고려한 경로입니다.',
        origin_latitude:
          originLatitude + 0.001 * rank,
        origin_longitude:
          originLongitude + 0.001 * rank,
        destination_latitude:
          destinationLatitude - 0.001 * rank,
        destination_longitude:
          destinationLongitude - 0.001 * rank,
        origin_bikes_now: 7 - index,
        origin_bikes_expected: 6.4 - index,
        destination_docks_now: 8 - index,
        destination_docks_expected: 7.5 - index,
        walk_to_origin_m: 120 + index * 140,
        walk_to_destination_m: 160 + index * 130,
        origin_eta_min: 2 + index * 2,
        destination_eta_min: 20 + index * 4,
      }
    }),
  }
}
