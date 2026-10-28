import {
  useCallback,
  useState,
} from "react";

import {
  getNearbyStations,
} from "./api/stationApi";

import {
  getRecommendationPreview,
} from "./api/recommendationApi";

import LocationSearch
  from "./components/location/LocationSearch";

import KakaoMap
  from "./components/map/KakaoMap";


function App() {
  const [
    origin,
    setOrigin,
  ] = useState(null);

  const [
    destination,
    setDestination,
  ] = useState(null);

  const [
    originStations,
    setOriginStations,
  ] = useState([]);

  const [
    destinationStations,
    setDestinationStations,
  ] = useState([]);

  const [
    originRecommendation,
    setOriginRecommendation,
  ] = useState(null);

  const [
    destinationRecommendation,
    setDestinationRecommendation,
  ] = useState(null);

  const [
    loadingSide,
    setLoadingSide,
  ] = useState(null);

  const [
    error,
    setError,
  ] = useState("");


  const selectLocation =
    useCallback(
      async (
        side,
        place,
      ) => {
        setError("");
        setLoadingSide(side);

        if (side === "origin") {
          setOrigin(place);
          setOriginStations([]);
          setOriginRecommendation(null);
        } else {
          setDestination(place);
          setDestinationStations([]);
          setDestinationRecommendation(
            null,
          );
        }

        try {
          const stations =
            await getNearbyStations(
              place.latitude,
              place.longitude,
            );

          /*
           * 주변 후보 자체는 충분히 확보하고,
           * Top-3 결정은 recommendation score가 한다.
           */
          const candidates =
            stations.slice(0, 10);

          const recommendation =
            await getRecommendationPreview(
              candidates,
              side,
            );

          const topThree =
            recommendation
              .recommendations;

          if (side === "origin") {
            setOriginStations(
              topThree,
            );

            setOriginRecommendation(
              recommendation,
            );
          } else {
            setDestinationStations(
              topThree,
            );

            setDestinationRecommendation(
              recommendation,
            );
          }
        } catch (
          requestError
        ) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "주변 대여소를 불러오지 못했습니다.",
          );
        } finally {
          setLoadingSide(null);
        }
      },
      [],
    );


  return (
    <main className="app-shell">
      <header className="hero">
        <p className="eyebrow">
          SEOUL BIKE ROUTE
        </p>

        <h1>
          출발과 도착을 정하면
          <br />
          미래 가용성이 보여요.
        </h1>

        <p className="hero-copy">
          단순 현재 재고가 아니라
          실제 도착 예상 시점의
          자전거·빈 거치대 가용성을
          기준으로 추천합니다.
        </p>
      </header>


      <section
        className="search-grid"
        aria-label="출발지와 목적지 검색"
      >
        <LocationSearch
          label="출발지"
          accent="origin"
          selected={origin}
          loading={
            loadingSide ===
            "origin"
          }
          onSelect={(place) =>
            selectLocation(
              "origin",
              place,
            )
          }
        />

        <LocationSearch
          label="목적지"
          accent="destination"
          selected={destination}
          loading={
            loadingSide ===
            "destination"
          }
          onSelect={(place) =>
            selectLocation(
              "destination",
              place,
            )
          }
        />
      </section>


      {error && (
        <div
          className="error-banner"
          role="alert"
        >
          {error}
        </div>
      )}


      <section className="map-card">
        <div className="map-heading">
          <div>
            <p className="eyebrow">
              MAP
            </p>

            <h2>
              추천 대여소
            </h2>
          </div>

          <div
            className="map-legend"
            aria-label="지도 범례"
          >
            <span>
              <i className="legend-dot origin-dot" />
              출발
            </span>

            <span>
              <i className="legend-dot destination-dot" />
              도착
            </span>
          </div>
        </div>

        <KakaoMap
          origin={origin}
          destination={
            destination
          }
          originStations={
            originStations
          }
          destinationStations={
            destinationStations
          }
        />
      </section>


      <section
        className="candidate-grid"
        aria-label="추천 대여소 목록"
      >
        <RecommendationList
          title="출발 Top-3"
          accent="origin"
          leg="origin"
          data={
            originRecommendation
          }
        />

        <RecommendationList
          title="도착 Top-3"
          accent="destination"
          leg="destination"
          data={
            destinationRecommendation
          }
        />
      </section>
    </main>
  );
}


function RecommendationList({
  title,
  accent,
  leg,
  data,
}) {
  const recommendations =
    data?.recommendations ?? [];

  return (
    <article
      className={
        `candidate-panel ${accent}`
      }
    >
      <div className="panel-title">
        <div>
          <h2>{title}</h2>

          {data && (
            <small className="horizon-label">
              ETA{" "}
              {Number(
                data.eta_min,
              ).toFixed(0)}
              분 ·{" "}
              {formatHorizon(
                data.effective_horizon,
              )}
            </small>
          )}
        </div>

        <span>
          {recommendations.length}/3
        </span>
      </div>


      {data?.mock && (
        <p className="mock-note">
          추천 API 연결 전
          UI 계약 검증용 Mock 예측
        </p>
      )}


      {recommendations.length ===
      0 ? (
        <p className="empty-copy">
          장소를 선택하면
          미래 가용성 기반
          추천 Top-3가 표시됩니다.
        </p>
      ) : (
        <ol className="candidate-list recommendation-list">
          {recommendations.map(
            (station) => (
              <li
                key={
                  station.station_id
                }
              >
                <span className="candidate-rank">
                  {station.rank}
                </span>

                <div className="recommendation-content">
                  <div className="recommendation-heading">
                    <strong>
                      {
                        station.station_name
                      }
                    </strong>

                    <span className="score-badge">
                      점수{" "}
                      {station.score.toFixed(
                        2,
                      )}
                    </span>
                  </div>

                  <small>
                    {Math.round(
                      station.distance_m,
                    )}
                    m · 도보{" "}
                    {Number(
                      station.walk_min,
                    ).toFixed(0)}
                    분
                  </small>

                  <div className="inventory-grid">
                    <div className="inventory-main">
                      <span>
                        {leg ===
                        "origin"
                          ? "도착 시 예상 자전거"
                          : "도착 시 예상 빈 거치대"}
                      </span>

                      <strong>
                        {(
                          leg ===
                          "origin"
                            ? station.bikes_expected
                            : station.docks_expected
                        ).toFixed(1)}
                        대
                      </strong>
                    </div>

                    <div className="inventory-current">
                      <span>
                        현재{" "}
                        {leg ===
                        "origin"
                          ? "자전거"
                          : "빈 거치대"}
                      </span>

                      <strong>
                        {(
                          leg ===
                          "origin"
                            ? station.bikes_now
                            : station.docks_now
                        ).toFixed(1)}
                        대
                      </strong>
                    </div>
                  </div>

                  <div className="score-breakdown">
                    <span>
                      거리{" "}
                      {station.score_breakdown.distance.toFixed(
                        2,
                      )}
                    </span>

                    <span>
                      가용성{" "}
                      {station.score_breakdown.availability.toFixed(
                        2,
                      )}
                    </span>
                  </div>

                  <p className="recommendation-reason">
                    {buildReason(
                      leg,
                      station,
                    )}
                  </p>
                </div>
              </li>
            ),
          )}
        </ol>
      )}
    </article>
  );
}


function formatHorizon(
  horizon,
) {
  if (!horizon) {
    return "";
  }

  if (
    horizon.method ===
    "clamp"
  ) {
    return "60분 예측 사용";
  }

  const [left, right] =
    horizon.anchors ?? [];

  return `${left}-${right}분 보간`;
}


function buildReason(
  leg,
  station,
) {
  if (leg === "origin") {
    return (
      `도보 ${Math.round(
        station.walk_min,
      )}분 · ` +
      `예상 자전거 ${station.bikes_expected.toFixed(
        1,
      )}대`
    );
  }

  return (
    `도보 ${Math.round(
      station.walk_min,
    )}분 · ` +
    `예상 빈 거치대 ${station.docks_expected.toFixed(
      1,
    )}대`
  );
}


export default App;
