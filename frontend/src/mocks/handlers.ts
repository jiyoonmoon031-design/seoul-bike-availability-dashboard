import {
  http,
  HttpResponse,
} from 'msw/http'
import {
  delay,
} from 'msw/utils/delay'

import {
  getOperatorFixture,
} from './operatorFixture'
import {
  nearbyStationFixture,
  routeRecommendationFixture,
  searchPlaceFixture,
} from './userFixtures'

export const handlers = [
  http.get(
    '*/api/v1/search/places',
    ({ request }) => {
      const query =
        new URL(request.url)
          .searchParams.get('query') ?? ''

      return HttpResponse.json(
        searchPlaceFixture(query),
      )
    },
  ),

  http.get(
    '*/api/v1/search/addresses',
    () => HttpResponse.json([]),
  ),

  http.get(
    '*/api/v1/stations/nearby',
    ({ request }) => {
      const url = new URL(request.url)
      const latitude = Number(
        url.searchParams.get('latitude'),
      )
      const longitude = Number(
        url.searchParams.get('longitude'),
      )

      return HttpResponse.json(
        nearbyStationFixture(
          latitude,
          longitude,
        ),
      )
    },
  ),

  http.get(
    '*/api/v1/routes/recommendations',
    ({ request }) => {
      const url = new URL(request.url)

      return HttpResponse.json(
        routeRecommendationFixture(
          Number(url.searchParams.get('originLat')),
          Number(url.searchParams.get('originLon')),
          Number(url.searchParams.get('destinationLat')),
          Number(url.searchParams.get('destinationLon')),
        ),
      )
    },
  ),

  http.get('*/api/v1/routes', ({ request }) => {
    const params = new URL(request.url).searchParams
    const start = {
      latitude: Number(params.get('startLat')),
      longitude: Number(params.get('startLon')),
    }
    const end = {
      latitude: Number(params.get('endLat')),
      longitude: Number(params.get('endLon')),
    }
    const bike = params.get('bike') === 'true'

    return HttpResponse.json({
      distance_m: 500,
      eta_min: bike ? 2 : 8,
      method: bike ? 'route_api' : 'straight_line',
      path: bike ? [start, { latitude: start.latitude, longitude: end.longitude }, end]
        : [start, end],
    })
  }),

  http.get(
    '/api/v1/operator/rebalancing',
    async ({ request }) => {
      const url =
        new URL(request.url)

      const baseTime =
        url.searchParams.get(
          'base_time',
        ) ??
        '2026-10-08T08:00:00+09:00'

      const horizon =
        Number(
          url.searchParams.get(
            'horizon',
          ) ?? 30,
        )

      const topN =
        Number(
          url.searchParams.get(
            'top_n',
          ) ?? 10,
        )

      await delay(450)

      const fixture =
        getOperatorFixture(
          horizon,
          baseTime,
        )

      return HttpResponse.json({
        ...fixture,
        shortage_top:
          [...fixture.shortage_top]
            .sort(
              (a, b) =>
                b.priority_score -
                a.priority_score,
            )
            .slice(0, topN),

        surplus_top:
          fixture.surplus_top.slice(
            0,
            topN,
          ),

        move_matches:
          fixture.move_matches.slice(
            0,
            topN,
          ),
      })
    },
  ),
]
