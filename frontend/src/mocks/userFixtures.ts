const places = [
  ['세종대학교', '서울 광진구 능동로 209', 37.5503, 127.0731],
  ['성수역', '서울 성동구 아차산로 100', 37.5446, 127.0559],
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
