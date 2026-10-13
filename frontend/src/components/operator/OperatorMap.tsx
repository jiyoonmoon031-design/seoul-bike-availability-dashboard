import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

import {
  loadKakaoMaps,
} from '../../lib/kakaoMaps'
import type {
  RebalancingResponse,
  StationMeta,
} from '../../types/operator'

type Props = {
  data: RebalancingResponse
  stationMeta:
    Record<string, StationMeta>
}

type MapStation =
  StationMeta & {
    detail: string
  }

export function OperatorMap({
  data,
  stationMeta,
}: Props) {
  const containerRef =
    useRef<HTMLDivElement | null>(
      null,
    )

  const [
    selected,
    setSelected,
  ] =
    useState<MapStation | null>(
      null,
    )

  const [
    mapReady,
    setMapReady,
  ] =
    useState(false)

  const [
    mapError,
    setMapError,
  ] =
    useState<string | null>(null)

  const stations =
    useMemo(() => {
      const shortageMap =
        new Map(
          data.shortage_top.map(
            (station) => [
              station.station_id,
              station,
            ],
          ),
        )

      const surplusMap =
        new Map(
          data.surplus_top.map(
            (station) => [
              station.station_id,
              station,
            ],
          ),
        )

      return Object
        .values(stationMeta)
        .filter((meta) => {
          if (
            meta.status ===
            'shortage'
          ) {
            return shortageMap.has(
              meta.station_id,
            )
          }

          if (
            meta.status ===
            'surplus'
          ) {
            return surplusMap.has(
              meta.station_id,
            )
          }

          return true
        })
        .map(
          (meta):
            MapStation => {
            const shortage =
              shortageMap.get(
                meta.station_id,
              )

            const surplus =
              surplusMap.get(
                meta.station_id,
              )

            if (shortage) {
              return {
                ...meta,
                status: 'shortage',
                detail:
                  `예상 ${shortage.bikes_expected.toFixed(1)}대 · ` +
                  `부족 ${shortage.shortage.toFixed(1)}대 · ` +
                  `점수 ${shortage.priority_score.toFixed(2)}`,
              }
            }

            if (surplus) {
              return {
                ...meta,
                status: 'surplus',
                detail:
                  `공급여유 ${surplus.supply_slack.toFixed(1)}대`,
              }
            }

            return {
              ...meta,
              status: 'normal',
              detail:
                `현재 ${meta.bikes_now ?? '-'}대`,
            }
          },
        )
    }, [
      data.shortage_top,
      data.surplus_top,
      stationMeta,
    ])

  useEffect(() => {
    const container =
      containerRef.current

    if (!container) {
      return
    }

    let cancelled = false

    setMapReady(false)
    setMapError(null)
    setSelected(null)

    void loadKakaoMaps()
      .then((maps) => {
        if (
          cancelled ||
          !containerRef.current
        ) {
          return
        }

        const node =
          containerRef.current

        node.replaceChildren()

        const map =
          new maps.Map(
            node,
            {
              center:
                new maps.LatLng(
                  37.548,
                  127.055,
                ),
              level: 6,
            },
          )

        const bounds =
          new maps.LatLngBounds()

        for (
          const station
          of stations
        ) {
          const position =
            new maps.LatLng(
              station.lat,
              station.lon,
            )

          bounds.extend(position)

          const marker =
            document.createElement(
              'button',
            )

          marker.type =
            'button'

          marker.className =
            `kakao-station-marker ` +
            `kakao-${station.status}`

          marker.textContent =
            station.station_id

          marker.title =
            station.station_name

          marker.setAttribute(
            'aria-label',
            `${station.station_name} ${station.status}`,
          )

          marker.addEventListener(
            'click',
            () =>
              setSelected(
                station,
              ),
          )

          new maps.CustomOverlay({
            map,
            position,
            content: marker,
            clickable: true,
            xAnchor: 0.5,
            yAnchor: 0.5,
            zIndex:
              station.status ===
              'shortage'
                ? 5
                : 4,
          })
        }

        for (
          const match
          of data.move_matches
        ) {
          const from =
            stationMeta[
              match.from_station_id
            ]

          const to =
            stationMeta[
              match.to_station_id
            ]

          if (!from || !to) {
            continue
          }

          const fromPosition =
            new maps.LatLng(
              from.lat,
              from.lon,
            )

          const toPosition =
            new maps.LatLng(
              to.lat,
              to.lon,
            )

          new maps.Polyline({
            map,
            path: [
              fromPosition,
              toPosition,
            ],
            strokeWeight: 3,
            strokeColor:
              '#557b98',
            strokeOpacity: 0.78,
            strokeStyle:
              'dashed',
            endArrow: true,
            zIndex: 2,
          })

          const midpoint =
            new maps.LatLng(
              (
                from.lat +
                to.lat
              ) / 2,
              (
                from.lon +
                to.lon
              ) / 2,
            )

          const label =
            document.createElement(
              'div',
            )

          label.className =
            'kakao-move-label'

          label.textContent =
            `${Math.floor(match.move_qty)}대`

          new maps.CustomOverlay({
            map,
            position: midpoint,
            content: label,
            xAnchor: 0.5,
            yAnchor: 1.2,
            zIndex: 3,
          })
        }

        if (
          stations.length > 0
        ) {
          map.setBounds(bounds)
        }

        map.relayout()

        setMapReady(true)
      })
      .catch((error) => {
        if (cancelled) {
          return
        }

        setMapError(
          error instanceof Error
            ? error.message
            : 'Kakao Map loading failed',
        )
      })

    return () => {
      cancelled = true

      container.replaceChildren()
    }
  }, [
    data.move_matches,
    stationMeta,
    stations,
  ])

  return (
    <section className="panel map-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">
            OPERATOR MAP
          </p>

          <h2>
            대여소 수급 위험 지도
          </h2>
        </div>

        <div className="map-legend">
          <span>
            <i className="dot dot-shortage" />
            부족
          </span>

          <span>
            <i className="dot dot-surplus" />
            포화
          </span>

          <span>
            <i className="dot dot-normal" />
            정상
          </span>
        </div>
      </div>

      <div className="kakao-map-shell">
        <div
          ref={containerRef}
          className="kakao-map-canvas"
        />

        {!mapReady &&
          !mapError && (
            <div className="map-sdk-status">
              Kakao Map을
              불러오는 중입니다...
            </div>
          )}

        {mapError && (
          <div className="map-sdk-status map-sdk-error">
            <strong>
              Kakao Map을
              불러오지 못했습니다.
            </strong>

            <span>
              {mapError}
            </span>

            <small>
              JavaScript Key와
              localhost:5173 도메인
              등록을 확인하세요.
            </small>
          </div>
        )}

        {selected && (
          <div className="station-popup">
            <button
              type="button"
              className="popup-close"
              onClick={() =>
                setSelected(null)
              }
            >
              ×
            </button>

            <span
              className={
                `popup-status ` +
                `popup-${selected.status}`
              }
            >
              {selected.status ===
              'shortage'
                ? '부족 위험'
                : selected.status ===
                    'surplus'
                  ? '공급 후보'
                  : '정상'}
            </span>

            <strong>
              {
                selected.station_name
              }
            </strong>

            <small>
              {selected.station_id}
            </small>

            <p>
              {selected.detail}
            </p>

            <small>
              현재 재고:{' '}
              {selected.bikes_now ??
                '-'}
              대
              {' / '}
              capacity:{' '}
              {selected.capacity ??
                '-'}
            </small>
          </div>
        )}

        {mapReady && (
          <div className="kakao-map-badge">
            Kakao Map
          </div>
        )}
      </div>
    </section>
  )
}
