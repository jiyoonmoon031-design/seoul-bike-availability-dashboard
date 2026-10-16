const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

export async function getStationStatuses() {
  const response = await fetch(`${API_BASE_URL}/api/v1/stations/status`);

  if (!response.ok) {
    throw new Error("대여소 상태 조회에 실패했습니다.");
  }

  const data = await response.json();

  return data.stations;
}

export async function getNearbyStations(latitude, longitude) {
  const params = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude),
  });
  const response = await fetch(
    `${API_BASE_URL}/api/v1/stations/nearby?${params.toString()}`,
  );

  if (!response.ok) {
    throw new Error(`주변 대여소 조회에 실패했습니다. (${response.status})`);
  }

  return response.json();
}
