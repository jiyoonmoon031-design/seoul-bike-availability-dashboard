import {
  http,
  HttpResponse,
} from 'msw/http'

import {
  stationMetaFixture,
} from './operatorFixture'

function districtFor(
  longitude: number,
) {
  return longitude >= 127.06
    ? '광진구'
    : '성동구'
}

export const stationHandlers = [
  http.get(
    '/api/v1/stations/status',
    () => {
      const stations =
        Object.values(
          stationMetaFixture,
        ).map((station) => {
          const capacity =
            station.capacity ?? 20

          const bikesNow =
            station.bikes_now ?? 10

          return {
            station_id:
              station.station_id,
            station_name:
              station.station_name,
            district:
              districtFor(
                station.lon,
              ),
            latitude:
              station.lat,
            longitude:
              station.lon,
            capacity,
            bikes_now:
              bikesNow,
            docks_now:
              Math.max(
                capacity -
                  bikesNow,
                0,
              ),
            collected_at:
              '2026-10-08T00:00:00Z',
          }
        })

      return HttpResponse.json({
        stations,
      })
    },
  ),
]
