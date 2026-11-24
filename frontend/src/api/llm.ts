const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? ''

export type CopilotAction =
  | 'briefing'
  | 'diagnosis'
  | 'qa'

export async function requestLlm(
  path: string,
  payload: unknown,
) {
  const controller = new AbortController()
  const timeout = window.setTimeout(
    () => controller.abort(),
    90_000,
  )

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/llm/${path}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      },
    )

    if (!response.ok) {
      throw new Error(
        `GPT API 요청 실패 (${response.status})`,
      )
    }

    return await response.json()
  } finally {
    window.clearTimeout(timeout)
  }
}

export function requestOperatorCopilot(
  action: CopilotAction,
  context: unknown,
  question?: string,
) {
  const payload =
    action === 'qa'
      ? { context, question }
      : { context }

  return requestLlm(
    `operator-copilot/${action}`,
    payload,
  )
}

export type RouteReasonCandidate = {
  rank: number
  origin_station_name: string
  destination_station_name: string
  walk_to_origin_min: number
  bike_min: number
  walk_to_destination_min: number
  total_eta_min: number
  origin_bikes_expected: number
  destination_docks_expected: number
  score: number
}

export async function requestRouteReasons(
  routes: RouteReasonCandidate[],
) {
  return requestLlm(
    'route-reasons',
    {
      routes: routes.map((r) => ({
        rank: r.rank,
        origin_station_name: r.origin_station_name,
        destination_station_name:
          r.destination_station_name,
        walk_to_origin_min: r.walk_to_origin_min,
        bike_min: r.bike_min,
        walk_to_destination_min:
          r.walk_to_destination_min,
        total_eta_min: r.total_eta_min,
        origin_bikes_expected:
          r.origin_bikes_expected,
        destination_docks_expected:
          r.destination_docks_expected,
        score: r.score,
      })),
    },
  )
}
