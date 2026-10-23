const API_BASE_URL = "http://localhost:8080";

export async function getStationStatuses() {
  const response = await fetch(`${API_BASE_URL}/api/v1/stations/status`);

  if (!response.ok) {
    throw new Error("대여소 상태 조회에 실패했습니다.");
  }

  const data = await response.json();

  return data.stations;
}
