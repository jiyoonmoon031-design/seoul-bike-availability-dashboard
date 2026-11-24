const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  "http://localhost:8080";

export async function getRouteRecommendations(
  origin,
  destination,
) {
  const params = new URLSearchParams({
    originLat: String(origin.latitude),
    originLon: String(origin.longitude),
    destinationLat: String(destination.latitude),
    destinationLon: String(destination.longitude),
  });
  const response = await fetch(
    `${API_BASE_URL}/api/v1/routes/recommendations?${params.toString()}`,
  );

  if (!response.ok) {
    throw new Error(
      `추천 경로를 불러오지 못했습니다. (${response.status})`,
    );
  }

  const payload = await response.json();
  return (payload.routes ?? []).map((route) => ({
    ...route,
    model_version: payload.model_version ?? null,
    prediction_base_time: payload.prediction_base_time ?? null,
    prediction_warnings: payload.prediction_warnings ?? [],
    route_geometry_source: route.route_geometry_source ?? "straight_line",
  }));
}
