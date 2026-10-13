export type PredictionSource =
  | 'model'
  | 'baseline_fallback'

export type ShortageStation = {
  station_id: string
  station_name: string
  lat: number
  lon: number
  bikes_expected: number
  s_min: number
  shortage: number
  urgency: number
  demand_weight: number
  priority_score: number
  risk_time: string
}

export type SurplusStation = {
  station_id: string
  docks_expected: number
  supply_slack: number
}

export type MoveMatch = {
  from_station_id: string
  to_station_id: string
  distance_km: number
  move_qty: number
}

export type RebalancingResponse = {
  base_time: string
  horizon_min: number
  source: PredictionSource
  shortage_top: ShortageStation[]
  surplus_top: SurplusStation[]
  move_matches: MoveMatch[]
}

export type StationMeta = {
  station_id: string
  station_name: string
  lat: number
  lon: number
  district?: string
  capacity?: number | null
  bikes_now?: number | null
  docks_now?: number | null
  collected_at?: string

  // Mock 단계 호환용.
  // 실제 backend station/status 응답에는 이 필드가 없다.
  status?: 'shortage' | 'surplus' | 'normal'
}


export type StationStatusApi = {
  station_id: string
  station_name: string
  district: string
  latitude: number
  longitude: number
  capacity: number | null
  bikes_now: number | null
  docks_now: number | null
  collected_at: string
}

export type StationStatusResponseApi = {
  stations: StationStatusApi[]
}
