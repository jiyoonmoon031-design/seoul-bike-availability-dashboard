import {
  keepPreviousData,
  useQuery,
} from '@tanstack/react-query'
import {
  useMemo,
  useState,
} from 'react'

import {
  fetchOperatorRebalancing,
} from '../api/operator'
import {
  OperatorControls,
} from '../components/operator/OperatorControls'
import {
  OperatorMap,
} from '../components/operator/OperatorMap'
import {
  RebalancingList,
} from '../components/operator/RebalancingList'
import {
  RiskTable,
} from '../components/operator/RiskTable'
import {
  SourceBadge,
} from '../components/operator/SourceBadge'
import {
  fetchStationMetadata,
} from '../api/stations'

type AppliedQuery = {
  baseTime: string
  horizon: number
  topN: number
}

const DEFAULT_BASE_TIME =
  '2026-10-08T08:00'

function toApiTime(
  value: string,
) {
  return `${value}:00+09:00`
}

export function OperatorPage() {
  const [baseTime, setBaseTime] =
    useState(DEFAULT_BASE_TIME)

  const [horizon, setHorizon] =
    useState(30)

  const [topN, setTopN] =
    useState(10)

  const [query, setQuery] =
    useState<AppliedQuery>({
      baseTime: DEFAULT_BASE_TIME,
      horizon: 30,
      topN: 10,
    })

  const operatorQuery =
    useQuery({
      queryKey: [
        'operator-rebalancing',
        query.baseTime,
        query.horizon,
        query.topN,
      ],

      queryFn: () =>
        fetchOperatorRebalancing({
          baseTime:
            toApiTime(
              query.baseTime,
            ),
          horizon:
            query.horizon,
          topN:
            query.topN,
        }),

      placeholderData:
        keepPreviousData,
    })


  const stationQuery =
    useQuery({
      queryKey: [
        'station-status',
      ],

      queryFn:
        fetchStationMetadata,

      staleTime: 60_000,
    })

  const activeError =
    operatorQuery.error ??
    stationQuery.error

  const data =
    operatorQuery.data

  const shortageTop =
    useMemo(() => {
      if (!data) {
        return []
      }

      return [
        ...data.shortage_top,
      ].sort(
        (a, b) =>
          b.priority_score -
          a.priority_score,
      )
    }, [data])

  const shortageIds =
    useMemo(
      () =>
        new Set(
          shortageTop.map(
            (station) =>
              station.station_id,
          ),
        ),
      [shortageTop],
    )

  const moveMatches =
    useMemo(() => {
      if (!data) {
        return []
      }

      return data.move_matches.filter(
        (match) =>
          shortageIds.has(
            match.to_station_id,
          ),
      )
    }, [
      data,
      shortageIds,
    ])

  const totalMove =
    moveMatches.reduce(
      (sum, item) =>
        sum + item.move_qty,
      0,
    )

  return (
    <main className="app-shell">
      <header className="page-header">
        <div>
          <p className="eyebrow">
            SEOUL BIKE · OPERATOR
          </p>

          <h1>
            따릉이 운영자 재배치
            대시보드
          </h1>

          <p className="page-description">
            광진구·성동구 대여소의
            단기 부족·포화 위험과
            이동 권고를 확인합니다.
          </p>
        </div>

        <div className="status-chip">
          <i />
          Week 07 UI v1
        </div>
      </header>

      {data && (
        <SourceBadge
          source={data.source}
        />
      )}

      <OperatorControls
        baseTime={baseTime}
        horizon={horizon}
        topN={topN}
        onBaseTimeChange={
          setBaseTime
        }
        onHorizonChange={
          setHorizon
        }
        onTopNChange={
          setTopN
        }
        onSubmit={() =>
          setQuery({
            baseTime,
            horizon,
            topN,
          })
        }
      />

      {(
        operatorQuery.isFetching ||
        stationQuery.isFetching
      ) && (
        <div className="query-status loading-status">
          운영자 데이터를
          불러오는 중입니다...
        </div>
      )}

      {(
        operatorQuery.isError ||
        stationQuery.isError
      ) && (
        <div className="query-status error-status">
          <div>
            <strong>
              운영자 데이터를
              불러오지 못했습니다.
            </strong>

            <span>
              {activeError
                instanceof Error
                ? activeError.message
                : 'Unknown error'}
            </span>
          </div>

          <button
            type="button"
            onClick={() =>
              operatorQuery.refetch()
            }
          >
            다시 시도
          </button>
        </div>
      )}

      {data && (
        <>
          <section className="summary-grid">
            <article className="summary-card">
              <span>부족 위험</span>

              <strong>
                {shortageTop.length}
              </strong>

              <small>대여소</small>
            </article>

            <article className="summary-card">
              <span>공급 후보</span>

              <strong>
                {
                  data.surplus_top
                    .length
                }
              </strong>

              <small>대여소</small>
            </article>

            <article className="summary-card">
              <span>이동 매칭</span>

              <strong>
                {moveMatches.length}
              </strong>

              <small>건</small>
            </article>

            <article className="summary-card accent">
              <span>권장 이동</span>

              <strong>
                {totalMove}
              </strong>

              <small>대</small>
            </article>
          </section>

          <section className="dashboard-grid">
            <OperatorMap
              data={{
                ...data,
                move_matches:
                  moveMatches,
              }}
              stationMeta={
                stationQuery.data ??
                {}
              }
            />

            <RebalancingList
              matches={
                moveMatches
              }
              shortages={
                shortageTop
              }
              surpluses={
                data.surplus_top
              }
            />
          </section>

          <RiskTable
            stations={
              shortageTop
            }
          />

          <footer className="page-footer">
            base_time:{' '}
            {data.base_time}
            {' · '}
            horizon:{' '}
            {data.horizon_min}분
            {' · '}
            source:{' '}
            {data.source}
          </footer>
        </>
      )}
    </main>
  )
}
