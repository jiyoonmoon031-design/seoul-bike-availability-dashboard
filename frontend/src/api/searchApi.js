const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

async function fetchJson(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);

  if (!response.ok) {
    throw new Error(`장소 검색에 실패했습니다. (${response.status})`);
  }

  return response.json();
}

export async function searchLocations(query) {
  const normalized = query.trim();

  if (normalized.length < 2) {
    throw new Error("검색어를 두 글자 이상 입력해 주세요.");
  }

  const encoded = encodeURIComponent(normalized);
  const places = await fetchJson(`/api/v1/search/places?query=${encoded}`);

  if (places.length > 0) {
    return places.map((place) => ({
      name: place.placeName,
      address: place.roadAddress || place.address,
      latitude: place.latitude,
      longitude: place.longitude,
    }));
  }

  const addresses = await fetchJson(`/api/v1/search/addresses?query=${encoded}`);
  return addresses.map((place) => ({
    name: place.roadAddress || place.address,
    address: place.address,
    latitude: place.latitude,
    longitude: place.longitude,
  }));
}
