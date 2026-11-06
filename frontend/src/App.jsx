import {
  useEffect,
  useState,
} from "react";

import {
  getRouteRecommendations,
} from "./api/recommendationApi";

import LocationSearch
  from "./components/location/LocationSearch";

import KakaoMap
  from "./components/map/KakaoMap";


function App() {
  const [origin, setOrigin] =
    useState(null);
  const [destination, setDestination] =
    useState(null);
  const [routes, setRoutes] =
    useState([]);
  const [loading, setLoading] =
    useState(false);
  const [error, setError] =
    useState("");

  useEffect(() => {
    if (!origin || !destination) {
      return undefined;
    }

    let cancelled = false;

    getRouteRecommendations(
      origin,
      destination,
    )
      .then((nextRoutes) => {
        if (!cancelled) {
          setRoutes(
            nextRoutes.slice(0, 3),
          );
        }
      })
      .catch((requestError) => {
        if (!cancelled) {
          setRoutes([]);
          setError(
            requestError instanceof Error
              ? requestError.message
              : "추천 경로를 불러오지 못했습니다.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [origin, destination]);

  const selectLocation = (
    side,
    place,
  ) => {
    const nextOrigin =
      side === "origin"
        ? place
        : origin;
    const nextDestination =
      side === "destination"
        ? place
        : destination;

    setError("");
    setRoutes([]);
    setLoading(Boolean(
      nextOrigin && nextDestination,
    ));

    if (side === "origin") {
      setOrigin(place);
    } else {
      setDestination(place);
    }
  };

  return (
    <main className="app-shell">
      <header className="hero">
        <p className="eyebrow">
          SEOUL BIKE ROUTE
        </p>

        <h1>
          빌리는 곳부터 반납하는 곳까지
          <br />
          가장 안정적인 경로를 추천해요.
        </h1>

        <p className="hero-copy">
          출발 자전거와 도착 빈 거치대의
          미래 가용성, 도보시간과 총 이동시간을
          함께 비교한 Best 3 경로입니다.
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
          loading={false}
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
          loading={false}
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
            <h2>Best 3 추천 경로</h2>
          </div>

          <div
            className="map-legend"
            aria-label="지도 범례"
          >
            <span>
              <i className="legend-dot origin-dot" />
              출발 대여소
            </span>
            <span>
              <i className="legend-dot destination-dot" />
              도착 대여소
            </span>
          </div>
        </div>

        <KakaoMap
          origin={origin}
          destination={destination}
          routes={routes}
        />
      </section>

      <RouteRecommendations
        routes={routes}
        loading={loading}
        ready={Boolean(
          origin && destination,
        )}
      />
    </main>
  );
}


function RouteRecommendations({
  routes,
  loading,
  ready,
}) {
  return (
    <article className="route-panel">
      <div className="panel-title">
        <div>
          <p className="eyebrow">
            ROUTE RECOMMENDATION
          </p>
          <h2>Best 3 추천 경로</h2>
        </div>
        <span>{routes.length}/3</span>
      </div>

      {loading && (
        <p
          className="empty-copy"
          role="status"
        >
          출발·도착 가용성과 이동시간을
          함께 계산하고 있습니다.
        </p>
      )}

      {!loading && routes.length === 0 && (
        <p className="empty-copy">
          {ready
            ? "조건을 만족하는 추천 경로가 없습니다."
            : "출발지와 목적지를 모두 선택하면 Best 3 경로가 표시됩니다."}
        </p>
      )}

      {!loading && routes.length > 0 && (
        <ol className="route-list">
          {routes.map((route) => (
            <RouteCard
              key={`${route.origin_station_id}-${route.destination_station_id}`}
              route={route}
            />
          ))}
        </ol>
      )}
    </article>
  );
}


function RouteCard({ route }) {
  return (
    <li className="route-card">
      <div className="route-rank">
        <span>BEST</span>
        <strong>{route.rank}</strong>
      </div>

      <div className="route-content">
        <div className="route-heading">
          <div>
            <strong>
              {route.origin_station_name}
            </strong>
            <span aria-hidden="true">→</span>
            <strong>
              {route.destination_station_name}
            </strong>
          </div>
          <span className="score-badge">
            경로점수 {Number(route.score).toFixed(2)}
          </span>
        </div>

        <div className="journey-steps">
          <span>
            출발지 도보 {route.walk_to_origin_min}분
          </span>
          <span>
            자전거 {route.bike_min}분
          </span>
          <span>
            목적지 도보 {route.walk_to_destination_min}분
          </span>
          <strong>
            총 {route.total_eta_min}분
          </strong>
        </div>

        <div className="route-availability">
          <div className="origin-availability">
            <span>출발 도착 시 예상 자전거</span>
            <strong>
              {Number(
                route.origin_bikes_expected,
              ).toFixed(1)}대
            </strong>
            <small>
              현재 {route.origin_bikes_now}대
            </small>
          </div>

          <div className="destination-availability">
            <span>반납 시 예상 빈 거치대</span>
            <strong>
              {Number(
                route.destination_docks_expected,
              ).toFixed(1)}대
            </strong>
            <small>
              현재 {route.destination_docks_now}대
            </small>
          </div>
        </div>

        <div className="route-score-breakdown">
          <span>
            출발 {formatScore(
              route.score_breakdown?.origin_station,
            )}
          </span>
          <span>
            도착 {formatScore(
              route.score_breakdown?.destination_station,
            )}
          </span>
          <span>
            ETA {formatScore(
              route.score_breakdown?.eta,
            )}
          </span>
          <span>
            도보 {formatScore(
              route.score_breakdown?.walking,
            )}
          </span>
        </div>

        <p className="route-reason">
          {route.reason}
        </p>
      </div>
    </li>
  );
}


function formatScore(value) {
  return Number(value ?? 0).toFixed(2);
}


export default App;
