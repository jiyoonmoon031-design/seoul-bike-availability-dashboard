import type {
  RebalancingResponse,
  StationMeta,
} from '../types/operator'

const BASE_TIME =
  '2026-10-08T08:00:00+09:00'

const shortage15 = [
  ['D-001', '건대입구역 2번출구', 37.5406, 127.0692, 1.8, 4, 2.2, 4, 1.7, 14.96, '2026-10-08T08:15:00+09:00'],
  ['D-002', '성수역 3번출구', 37.5445, 127.0558, 2.3, 5, 2.7, 4, 1.3, 14.04, '2026-10-08T08:15:00+09:00'],
  ['D-003', '서울숲역', 37.5437, 127.0447, 1.5, 4, 2.5, 4, 1.2, 12.00, '2026-10-08T08:15:00+09:00'],
  ['D-004', '왕십리역 6번출구', 37.5611, 127.0370, 2.1, 4, 1.9, 4, 1.4, 10.64, '2026-10-08T08:15:00+09:00'],
  ['D-005', '어린이대공원역', 37.5483, 127.0748, 2.8, 5, 2.2, 4, 1.1, 9.68, '2026-10-08T08:15:00+09:00'],
  ['D-006', '뚝섬역 5번출구', 37.5475, 127.0473, 3.2, 5, 1.8, 4, 1.0, 7.20, '2026-10-08T08:15:00+09:00'],
]

const shortage30 = [
  ['D-001', '건대입구역 2번출구', 37.5406, 127.0692, 2.0, 4, 2.0, 2, 1.7, 6.80, '2026-10-08T08:30:00+09:00'],
  ['D-002', '성수역 3번출구', 37.5445, 127.0558, 2.6, 5, 2.4, 2, 1.3, 6.24, '2026-10-08T08:30:00+09:00'],
  ['D-003', '서울숲역', 37.5437, 127.0447, 2.1, 4, 1.9, 2, 1.2, 4.56, '2026-10-08T08:30:00+09:00'],
  ['D-004', '왕십리역 6번출구', 37.5611, 127.0370, 2.4, 4, 1.6, 2, 1.4, 4.48, '2026-10-08T08:30:00+09:00'],
  ['D-005', '어린이대공원역', 37.5483, 127.0748, 3.2, 5, 1.8, 2, 1.1, 3.96, '2026-10-08T08:30:00+09:00'],
  ['D-006', '뚝섬역 5번출구', 37.5475, 127.0473, 3.5, 5, 1.5, 2, 1.0, 3.00, '2026-10-08T08:30:00+09:00'],
]

const shortage60 = [
  ['D-001', '건대입구역 2번출구', 37.5406, 127.0692, 1.2, 4, 2.8, 1, 1.7, 4.76, '2026-10-08T09:00:00+09:00'],
  ['D-002', '성수역 3번출구', 37.5445, 127.0558, 2.1, 5, 2.9, 1, 1.3, 3.77, '2026-10-08T09:00:00+09:00'],
  ['D-003', '서울숲역', 37.5437, 127.0447, 1.5, 4, 2.5, 1, 1.2, 3.00, '2026-10-08T09:00:00+09:00'],
  ['D-004', '왕십리역 6번출구', 37.5611, 127.0370, 1.9, 4, 2.1, 1, 1.4, 2.94, '2026-10-08T09:00:00+09:00'],
  ['D-005', '어린이대공원역', 37.5483, 127.0748, 3.0, 5, 2.0, 1, 1.1, 2.20, '2026-10-08T09:00:00+09:00'],
  ['D-006', '뚝섬역 5번출구', 37.5475, 127.0473, 3.2, 5, 1.8, 1, 1.0, 1.80, '2026-10-08T09:00:00+09:00'],
]

function makeShortage(
  rows: (string | number)[][],
) {
  return rows.map((row) => ({
    station_id: String(row[0]),
    station_name: String(row[1]),
    lat: Number(row[2]),
    lon: Number(row[3]),
    bikes_expected: Number(row[4]),
    s_min: Number(row[5]),
    shortage: Number(row[6]),
    urgency: Number(row[7]),
    demand_weight: Number(row[8]),
    priority_score: Number(row[9]),
    risk_time: String(row[10]),
  }))
}

const surplus = [
  {
    station_id: 'S-001',
    docks_expected: 1.0,
    supply_slack: 15,
  },
  {
    station_id: 'S-002',
    docks_expected: 2.0,
    supply_slack: 11,
  },
  {
    station_id: 'S-003',
    docks_expected: 1.5,
    supply_slack: 9,
  },
  {
    station_id: 'S-004',
    docks_expected: 2.4,
    supply_slack: 7,
  },
]

const matches = [
  {
    from_station_id: 'S-001',
    to_station_id: 'D-001',
    distance_km: 0.82,
    move_qty: 2,
  },
  {
    from_station_id: 'S-002',
    to_station_id: 'D-002',
    distance_km: 1.14,
    move_qty: 2,
  },
  {
    from_station_id: 'S-003',
    to_station_id: 'D-003',
    distance_km: 1.48,
    move_qty: 2,
  },
  {
    from_station_id: 'S-004',
    to_station_id: 'D-004',
    distance_km: 1.76,
    move_qty: 1,
  },
]

export const operatorFixtures:
  Record<number, RebalancingResponse> = {
    15: {
      base_time: BASE_TIME,
      horizon_min: 15,
      source: 'model',
      shortage_top: makeShortage(shortage15),
      surplus_top: surplus,
      move_matches: matches,
    },
    30: {
      base_time: BASE_TIME,
      horizon_min: 30,
      source: 'model',
      shortage_top: makeShortage(shortage30),
      surplus_top: surplus,
      move_matches: matches,
    },
    60: {
      base_time: BASE_TIME,
      horizon_min: 60,
      source: 'baseline_fallback',
      shortage_top: makeShortage(shortage60),
      surplus_top: surplus,
      move_matches: matches,
    },
  }

export const stationMetaFixture:
  Record<string, StationMeta> = {
    'D-001': { station_id: 'D-001', station_name: '건대입구역 2번출구', lat: 37.5406, lon: 127.0692, status: 'shortage', bikes_now: 4, capacity: 20 },
    'D-002': { station_id: 'D-002', station_name: '성수역 3번출구', lat: 37.5445, lon: 127.0558, status: 'shortage', bikes_now: 5, capacity: 25 },
    'D-003': { station_id: 'D-003', station_name: '서울숲역', lat: 37.5437, lon: 127.0447, status: 'shortage', bikes_now: 4, capacity: 20 },
    'D-004': { station_id: 'D-004', station_name: '왕십리역 6번출구', lat: 37.5611, lon: 127.0370, status: 'shortage', bikes_now: 4, capacity: 20 },
    'D-005': { station_id: 'D-005', station_name: '어린이대공원역', lat: 37.5483, lon: 127.0748, status: 'shortage', bikes_now: 5, capacity: 25 },
    'D-006': { station_id: 'D-006', station_name: '뚝섬역 5번출구', lat: 37.5475, lon: 127.0473, status: 'shortage', bikes_now: 5, capacity: 25 },

    'S-001': { station_id: 'S-001', station_name: '성수대교 북단', lat: 37.5387, lon: 127.0450, status: 'surplus', bikes_now: 19, capacity: 20 },
    'S-002': { station_id: 'S-002', station_name: '서울숲 남문', lat: 37.5418, lon: 127.0389, status: 'surplus', bikes_now: 17, capacity: 20 },
    'S-003': { station_id: 'S-003', station_name: '자양사거리', lat: 37.5357, lon: 127.0730, status: 'surplus', bikes_now: 16, capacity: 20 },
    'S-004': { station_id: 'S-004', station_name: '한양대역', lat: 37.5555, lon: 127.0437, status: 'surplus', bikes_now: 14, capacity: 20 },

    'N-001': { station_id: 'N-001', station_name: '세종대학교 정문', lat: 37.5503, lon: 127.0731, status: 'normal', bikes_now: 9, capacity: 20 },
    'N-002': { station_id: 'N-002', station_name: '서울숲 북문', lat: 37.5486, lon: 127.0425, status: 'normal', bikes_now: 10, capacity: 20 },
  }

export function getOperatorFixture(
  horizon: number,
  baseTime: string,
): RebalancingResponse {
  const fixture =
    operatorFixtures[horizon] ??
    operatorFixtures[30]

  return {
    ...fixture,
    base_time: baseTime,
  }
}
