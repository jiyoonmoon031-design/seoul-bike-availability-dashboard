import ReactMarkdown from 'react-markdown'
import { useState } from 'react'
import {
  requestOperatorCopilot,
  type CopilotAction,
} from '../../api/llm'

import type {
  RebalancingResponse,
} from '../../types/operator'

type Props = {
  data: RebalancingResponse
}

function extractText(
  result: Record<string, unknown>,
  action: CopilotAction,
): string {
  const direct = result[action]

  if (typeof direct === 'string') {
    return direct
  }

  if (
    direct &&
    typeof direct === 'object' &&
    'text' in direct &&
    typeof direct.text === 'string'
  ) {
    return direct.text
  }

  if (typeof result.text === 'string') {
    return result.text
  }

  return JSON.stringify(result, null, 2)
}

export function OperatorCopilot({ data }: Props) {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] =
    useState<CopilotAction | null>(null)

  const run = async (action: CopilotAction) => {
    if (loading) return

    if (action === 'qa' && !question.trim()) {
      setError('질문을 입력해주세요.')
      return
    }

    setLoading(action)
    setError('')
    setResult('')

    const context = {
      base_time: data.base_time,
      horizon_min: data.horizon_min,

      shortage_top: data.shortage_top.map((s) => ({
        station_id: s.station_id,
        station_name: s.station_name,
        lat: s.lat,
        lon: s.lon,
        bikes_expected: s.bikes_expected,
        s_min: s.s_min,
        shortage: s.shortage,
        urgency: s.urgency,
        demand_weight: s.demand_weight,
        priority_score: s.priority_score,
        risk_time: s.risk_time,
      })),

      surplus_top: data.surplus_top.map((s) => ({
        station_id: s.station_id,
        docks_expected: s.docks_expected,
        supply_slack: s.supply_slack,
      })),

      move_matches: data.move_matches.map((m) => ({
        from_station_id: m.from_station_id,
        to_station_id: m.to_station_id,
        distance_km: m.distance_km,
        move_qty: m.move_qty,
      })),
    }

    try {
      const response = await requestOperatorCopilot(
        action,
        context,
        question.trim(),
      )

      setResult(extractText(response, action))
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'AI 요청에 실패했습니다.',
      )
    } finally {
      setLoading(null)
    }
  }

  return (
    <section className="copilot-panel">
      <div className="copilot-heading">
        <p className="eyebrow">AI OPERATOR COPILOT</p>
        <h2>AI 운영 지원</h2>
        <p>
          현재 조회된 재배치 결과를 기반으로
          운영 상황을 설명합니다.
        </p>
      </div>

      <div className="copilot-actions">
        <button
          type="button"
          disabled={loading !== null}
          onClick={() => void run('briefing')}
        >
          운영 브리핑
        </button>

        <button
          type="button"
          disabled={loading !== null}
          onClick={() => void run('diagnosis')}
        >
          운영 상황 진단
        </button>
      </div>

      <form
        className="copilot-question"
        onSubmit={(event) => {
          event.preventDefault()
          void run('qa')
        }}
      >
        <input
          value={question}
          maxLength={500}
          onChange={(event) =>
            setQuestion(event.target.value)
          }
          placeholder="재배치 우선순위가 가장 높은 대여소는?"
        />

        <button
          type="submit"
          disabled={loading !== null || !question.trim()}
        >
          질문하기
        </button>
      </form>

      {loading && (
        <p role="status">
          AI가 운영 데이터를 분석하고 있습니다...
        </p>
      )}

      {error && (
        <p role="alert" className="copilot-error">
          {error}
        </p>
      )}

      {result && (
        <div className="copilot-result">
          <ReactMarkdown skipHtml>
            {result}
          </ReactMarkdown>
        </div>
      )}
    </section>
  )
}
