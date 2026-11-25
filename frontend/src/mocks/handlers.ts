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

  http.get(
    '/api/v1/operator/rebalancing',
    async ({ request }) => {
      const url =
        new URL(request.url)

      const baseTime =
        url.searchParams.get(
          'basetime',
        )

      const horizon =
        Number(
          url.searchParams.get(
            'horizon',
          ) ?? 30,
        )

      const topN =
        Number(
          url.searchParams.get(
            'topn',
          ),
        )

      if (
        !baseTime ||
        !Number.isFinite(topN)
      ) {
        return HttpResponse.json(
          {
            error:
              'basetime and topn are required',
          },
          { status: 400 },
        )
      }

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
