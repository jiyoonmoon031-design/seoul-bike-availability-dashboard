import type {
  MoveMatch,
  ShortageStation,
  SurplusStation,
} from '../../types/operator'

type Props = {
  matches: MoveMatch[]
  shortages: ShortageStation[]
  surpluses: SurplusStation[]
}

export function RebalancingList({
  matches,
  shortages,
  surpluses,
}: Props) {
  const shortageById =
    new Map(
      shortages.map(
        (station) => [
          station.station_id,
          station,
        ],
      ),
    )

  const surplusById =
    new Map(
      surpluses.map(
        (station) => [
          station.station_id,
          station,
        ],
      ),
    )

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">
            MOVE PLAN
          </p>
          <h2>재배치 이동 매칭</h2>
        </div>

        <span className="count-badge">
          {matches.length}건
        </span>
      </div>

      <div className="match-list">
        {matches.length === 0 ? (
          <div className="empty-state">
            현재 이동 권고가 없습니다.
          </div>
        ) : (
          matches.map((match) => {
            const shortage =
              shortageById.get(
                match.to_station_id,
              )

            const surplus =
              surplusById.get(
                match.from_station_id,
              )

            return (
              <article
                className="match-card"
                key={
                  `${match.from_station_id}-` +
                  `${match.to_station_id}`
                }
              >
                <div>
                  <div className="station-code supply-code">
                    {
                      match.from_station_id
                    }
                  </div>

                  <small className="station-subtext">
                    공급여유{' '}
                    {surplus
                      ? surplus.supply_slack.toFixed(
                          1,
                        )
                      : '-'}
                    대
                  </small>
                </div>

                <div className="match-arrow">
                  <span>
                    {match.distance_km.toFixed(
                      2,
                    )}{' '}
                    km
                  </span>

                  <div className="arrow-line">
                    →
                  </div>

                  <strong>
                    {Math.floor(
                      match.move_qty,
                    )}
                    대 이동
                  </strong>
                </div>

                <div>
                  <div className="station-code demand-code">
                    {match.to_station_id}
                  </div>

                  <small className="station-subtext">
                    부족{' '}
                    {shortage
                      ? shortage.shortage.toFixed(
                          1,
                        )
                      : '-'}
                    대
                  </small>
                </div>
              </article>
            )
          })
        )}
      </div>
    </section>
  )
}
