import type {
  RebalancingResponse,
} from '../types/operator'

export type OperatorQuery = {
  baseTime: string
  horizon: number
  topN: number
}

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? ''

export async function fetchOperatorRebalancing(
  query: OperatorQuery,
): Promise<RebalancingResponse> {
  const params = new URLSearchParams({
    basetime: query.baseTime,
    horizon: String(query.horizon),
    topn: String(query.topN),
  })

  const controller =
    new AbortController()

  const timeoutId =
    window.setTimeout(
      () => controller.abort(),
      60_000,
    )

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/operator/rebalancing?${params.toString()}`,
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
        `Operator API failed: ${response.status}`,
      )
    }

    return await response.json()
  } catch (error) {
    if (
      error instanceof DOMException &&
      error.name === 'AbortError'
    ) {
      throw new Error(
        'Operator API timeout (60s)',
      )
    }

    throw error
  } finally {
    window.clearTimeout(timeoutId)
  }
}
