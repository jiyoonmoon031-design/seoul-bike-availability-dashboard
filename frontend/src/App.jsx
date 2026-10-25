import { useCallback, useState } from "react";

import { getNearbyStations } from "./api/stationApi";
import LocationSearch from "./components/location/LocationSearch";
import KakaoMap from "./components/map/KakaoMap";

function App() {
  const [origin, setOrigin] = useState(null);
  const [destination, setDestination] = useState(null);
  const [originStations, setOriginStations] = useState([]);
  const [destinationStations, setDestinationStations] = useState([]);
  const [loadingSide, setLoadingSide] = useState(null);
  const [error, setError] = useState("");

  const selectLocation = useCallback(async (side, place) => {
    setError("");
    setLoadingSide(side);

    if (side === "origin") {
      setOrigin(place);
      setOriginStations([]);
    } else {
      setDestination(place);
      setDestinationStations([]);
    }

    try {
      const stations = await getNearbyStations(place.latitude, place.longitude);
      const topThree = stations.slice(0, 3);

      if (side === "origin") {
        setOriginStations(topThree);
      } else {
        setDestinationStations(topThree);
      }
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "주변 대여소를 불러오지 못했습니다.",
      );
    } finally {
      setLoadingSide(null);
    }
  }, []);

  return (
    <main className="app-shell">
      <header className="hero">
        <p className="eyebrow">SEOUL BIKE ROUTE</p>
        <h1>
          출발과 도착을 정하면
          <br />
          가까운 따릉이가 보여요.
        </h1>
        <p className="hero-copy">
          장소를 검색하고 주변 대여소 후보를 지도에서 한 번에 확인하세요.
        </p>
      </header>

      <section className="search-grid" aria-label="출발지와 목적지 검색">
        <LocationSearch
          label="출발지"
          accent="origin"
          selected={origin}
          loading={loadingSide === "origin"}
          onSelect={(place) => selectLocation("origin", place)}
        />
        <LocationSearch
          label="목적지"
          accent="destination"
          selected={destination}
          loading={loadingSide === "destination"}
          onSelect={(place) => selectLocation("destination", place)}
        />
      </section>

      {error && (
        <div className="error-banner" role="alert">
          {error}
        </div>
      )}

      <section className="map-card">
        <div className="map-heading">
          <div>
            <p className="eyebrow">MAP</p>
            <h2>주변 대여소 후보</h2>
          </div>
          <div className="map-legend" aria-label="지도 범례">
            <span>
              <i className="legend-dot origin-dot" />출발
            </span>
            <span>
              <i className="legend-dot destination-dot" />도착
            </span>
          </div>
        </div>

        <KakaoMap
          origin={origin}
          destination={destination}
          originStations={originStations}
          destinationStations={destinationStations}
        />
      </section>

      <section className="candidate-grid" aria-label="주변 대여소 목록">
        <CandidateList title="출발 후보" accent="origin" stations={originStations} />
        <CandidateList
          title="도착 후보"
          accent="destination"
          stations={destinationStations}
        />
      </section>
    </main>
  );
}

function CandidateList({ title, accent, stations }) {
  return (
    <article className={`candidate-panel ${accent}`}>
      <div className="panel-title">
        <h2>{title}</h2>
        <span>{stations.length}/3</span>
      </div>

      {stations.length === 0 ? (
        <p className="empty-copy">장소를 선택하면 가까운 대여소가 표시됩니다.</p>
      ) : (
        <ol className="candidate-list">
          {stations.map((station, index) => (
            <li key={station.station_id}>
              <span className="candidate-rank">{index + 1}</span>
              <div>
                <strong>{station.station_name}</strong>
                <small>
                  {Math.round(station.distance_m)}m · 도보 {station.walk_min}분
                </small>
              </div>
            </li>
          ))}
        </ol>
      )}
    </article>
  );
}

export default App;
