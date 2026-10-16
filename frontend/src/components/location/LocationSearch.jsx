import { useState } from "react";

import { searchLocations } from "../../api/searchApi";

function LocationSearch({ label, accent, selected, loading, onSelect }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [message, setMessage] = useState("");

  async function submit(event) {
    event.preventDefault();
    setMessage("");
    setSearching(true);

    try {
      const nextResults = await searchLocations(query);
      setResults(nextResults.slice(0, 5));
      if (nextResults.length === 0) {
        setMessage("검색 결과가 없습니다.");
      }
    } catch (error) {
      setResults([]);
      setMessage(error instanceof Error ? error.message : "검색하지 못했습니다.");
    } finally {
      setSearching(false);
    }
  }

  function choose(place) {
    setQuery(place.name);
    setResults([]);
    onSelect(place);
  }

  return (
    <article className={`search-card ${accent}`}>
      <div className="search-label">
        <span className="location-mark">{accent === "origin" ? "O" : "D"}</span>
        <div>
          <p>{label}</p>
          <small>{selected ? selected.address : "장소명이나 주소를 입력하세요"}</small>
        </div>
      </div>

      <form className="search-form" onSubmit={submit}>
        <input
          type="search"
          value={query}
          placeholder={label === "출발지" ? "예: 세종대학교" : "예: 성수역"}
          aria-label={`${label} 검색어`}
          onChange={(event) => setQuery(event.target.value)}
        />
        <button type="submit" disabled={searching || loading}>
          {searching ? "검색 중" : "검색"}
        </button>
      </form>

      {message && (
        <p className="search-message" role="status">
          {message}
        </p>
      )}

      {results.length > 0 && (
        <ul className="search-results">
          {results.map((place) => (
            <li key={`${place.name}-${place.latitude}-${place.longitude}`}>
              <button type="button" onClick={() => choose(place)}>
                <strong>{place.name}</strong>
                <span>{place.address}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {loading && (
        <p className="search-message" role="status">
          주변 대여소 확인 중...
        </p>
      )}
    </article>
  );
}

export default LocationSearch;
