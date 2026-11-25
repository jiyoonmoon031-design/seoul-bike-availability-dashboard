import { requestRouteReasons } from "./api/llm";
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
  const [selectedRouteRank, setSelectedRouteRank] =
    useState(null);

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
          const bestRoutes = nextRoutes.slice(0, 3);
          setRoutes(bestRoutes);
          setSelectedRouteRank(
            bestRoutes[0]?.rank ?? null,
          );
        }
      })
      .catch((requestError) => {
        if (!cancelled) {
          setRoutes([]);
          setSelectedRouteRank(null);
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
    setSelectedRouteRank(null);
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

        <p className="empty-copy">
          점선은 추천 대여소 간 직선 연결이며 실제 도로 경로가 아닙니다.
        </p>

        <KakaoMap
          origin={origin}
          destination={destination}
          routes={routes}
          selectedRouteRank={selectedRouteRank}
          onSelectRoute={setSelectedRouteRank}
        />

        {selectedRouteRank && (
          <p
            className="route-selection-status"
            role="status"
            aria-live="polite"
          >
            추천 {selectedRouteRank}위 경로를 지도에서 강조했습니다.
          </p>
        )}
      </section>

      <RouteRecommendations
          key={JSON.stringify(routes)}
        routes={routes}
        loading={loading}
        ready={Boolean(
          origin && destination,
        )}
        selectedRouteRank={selectedRouteRank}
        onSelectRoute={setSelectedRouteRank}
      />
    </main>
  );
}


function RouteRecommendations({
  routes,
  loading,
  ready,
  selectedRouteRank,
  onSelectRoute,
}) {
  const [aiReasons, setAiReasons] = useState({});
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState("");

  const loadAiReasons = async () => {
    if (aiLoading || !routes.length) return;

    setAiLoading(true);
    setAiError("");

    try {
      const response = await requestRouteReasons(routes);

      if (!Array.isArray(response.reasons)) {
        throw new Error("잘못된 AI 응답입니다.");
      }

      const reasons = {};

      for (const item of response.reasons) {
        if (typeof item.text !== "string") {
          throw new Error("잘못된 AI 설명입니다.");
        }
        reasons[item.rank] = item.text;
      }

      if (!routes.every((r) => reasons[r.rank])) {
        throw new Error("일부 AI 설명이 누락되었습니다.");
      }

      setAiReasons(reasons);

    } catch {
      setAiError(
        "AI 설명을 불러오지 못했습니다. "
        + "기존 추천 결과는 계속 이용할 수 있습니다."
      );
    } finally {
      setAiLoading(false);
    }
  };

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
        <div className="route-ai-toolbar">
          <div>
            <strong>AI 추천 설명</strong>
            <p>
              추천 경로의 가용성과 이동시간을 비교합니다.
            </p>
          </div>
          <button
            type="button"
            disabled={aiLoading}
            onClick={() => void loadAiReasons()}
          >
            {aiLoading
              ? "AI 분석 중..."
              : Object.keys(aiReasons).length
                ? "AI 설명 다시 생성"
                : "AI 추천 설명 보기"}
          </button>
        </div>
      )}

      {aiError && (
        <p role="alert" className="copilot-error">
          {aiError}
        </p>
      )}

      {!loading && routes.length > 0 && (
        <ol className="route-list">
          {routes.map((route) => (
            <RouteCard
              key={`${route.origin_station_id}-${route.destination_station_id}`}
              route={route}
              selected={route.rank === selectedRouteRank}
              onSelect={() => onSelectRoute(route.rank)}
              aiReason={aiReasons[route.rank]}
            />
          ))}
        </ol>
      )}
    </article>
  );
}


function RouteCard({
  route,
  selected,
  onSelect,
  aiReason,
}) {
  return (
    <li
      className={`route-card${selected ? " selected" : ""}`}
    >
      <button
        type="button"
        className="route-select-button"
        aria-pressed={selected}
        aria-label={`${route.rank}위 경로 선택: ${route.origin_station_name}에서 ${route.destination_station_name}까지, 총 ${route.total_eta_min}분`}
        onClick={onSelect}
      >
        <div className="route-rank" aria-hidden="true">
          <span>추천</span>
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

        {aiReason && (
          <div className="route-ai-reason">
            <strong>AI 추천 설명</strong>
            <p>{aiReason}</p>
            <small>
              예측 결과 기반 설명이며
              실제 대여·반납을 보장하지 않습니다.
            </small>
          </div>
        )}
        </div>
      </button>
    </li>
  );
}


function formatScore(value) {
  return Number(value ?? 0).toFixed(2);
}


export default App;
