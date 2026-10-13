import type {
  ShortageStation,
} from '../../types/operator'

type Props = {
  stations: ShortageStation[]
}

export function RiskTable({
  stations,
}: Props) {
  const sorted = [...stations].sort(
    (a, b) =>
      b.priority_score -
      a.priority_score,
  )

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">
            PRIORITY
          </p>
          <h2>재배치 우선순위</h2>
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>순위</th>
              <th>대여소</th>
              <th>예상 재고</th>
              <th>부족량</th>
              <th>긴급도</th>
              <th>수요 가중치</th>
              <th>우선순위</th>
              <th>위험 시각</th>
            </tr>
          </thead>

          <tbody>
            {sorted.map(
              (station, index) => (
                <tr
                  key={
                    station.station_id
                  }
                >
                  <td>
                    <span className="rank">
                      {index + 1}
                    </span>
                  </td>

                  <td>
                    <strong>
                      {
                        station.station_name
                      }
                    </strong>

                    <small>
                      {
                        station.station_id
                      }
                    </small>
                  </td>

                  <td>
                    {station.bikes_expected.toFixed(
                      1,
                    )}
                    대
                  </td>

                  <td>
                    <span className="metric-danger">
                      {station.shortage.toFixed(
                        1,
                      )}
                      대
                    </span>
                  </td>

                  <td>
                    {station.urgency.toFixed(
                      1,
                    )}
                  </td>

                  <td>
                    {station.demand_weight.toFixed(
                      2,
                    )}
                  </td>

                  <td>
                    <strong>
                      {station.priority_score.toFixed(
                        2,
                      )}
                    </strong>
                  </td>

                  <td>
                    {new Date(
                      station.risk_time,
                    ).toLocaleTimeString(
                      'ko-KR',
                      {
                        hour:
                          '2-digit',
                        minute:
                          '2-digit',
                      },
                    )}
                  </td>
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
