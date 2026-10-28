import type {
  StationMeta,
  StationStatusApi,
  StationStatusResponseApi,
} from '../types/operator'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? ''

const SERVICE_DISTRICTS =
  new Set([
    '광진구',
    '성동구',
  ])

function isFiniteCoordinate(
  value: number,
) {
  return Number.isFinite(value)
}

export function adaptStationStatus(
  station: StationStatusApi,
): StationMeta {
  return {
    station_id:
      station.station_id,
    station_name:
      station.station_name,
    district:
      station.district,
    lat:
      station.latitude,
    lon:
      station.longitude,
    capacity:
      station.capacity,
    bikes_now:
      station.bikes_now,
    docks_now:
      station.docks_now,
    collected_at:
      station.collected_at,
  }
}

export function adaptStationStatusResponse(
  payload: StationStatusResponseApi,
): Record<string, StationMeta> {
  const result:
    Record<string, StationMeta> = {}

  for (const station of payload.stations) {
    if (
      !SERVICE_DISTRICTS.has(
        station.district,
      )
    ) {
      continue
    }

    if (
      !isFiniteCoordinate(
        station.latitude,
      ) ||
      !isFiniteCoordinate(
        station.longitude,
      )
    ) {
      continue
    }

    result[station.station_id] =
      adaptStationStatus(station)
  }

  return result
}

export async function fetchStationMetadata():
  Promise<Record<string, StationMeta>> {
  const controller =
    new AbortController()

  const timeoutId =
    window.setTimeout(
      () => controller.abort(),
      10_000,
    )

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/stations/status`,
      {
        method: 'GET',
        headers: {
          Accept: 'application/json',
        },
        signal: controller.signal,
      },
    )

    if (!response.ok) {
      throw new Error(
        `Station API failed: ${response.status}`,
      )
    }

    const payload =
      (await response.json()) as
        StationStatusResponseApi

    if (
      !payload ||
      !Array.isArray(
        payload.stations,
      )
    ) {
      throw new Error(
        'Invalid station status response',
      )
    }

    return adaptStationStatusResponse(
      payload,
    )
  } catch (error) {
    if (
      error instanceof DOMException &&
      error.name === 'AbortError'
    ) {
      throw new Error(
        'Station API timeout (10s)',
      )
    }

    throw error
  } finally {
    window.clearTimeout(
      timeoutId,
    )
  }
}
