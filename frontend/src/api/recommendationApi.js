const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

export async function getRouteRecommendations(
  origin,
  destination,
  signal,
) {
  const params = new URLSearchParams({
    originLat: String(origin.latitude),
    originLon: String(origin.longitude),
    destinationLat: String(destination.latitude),
    destinationLon: String(destination.longitude),
  });
  const response = await fetch(
    `${API_BASE_URL}/api/v1/routes/recommendations?${params.toString()}`,
    { signal },
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
  }));
}

export async function getRouteGeometry(origin, destination, routes, signal) {
  const requests = new Map();

  const getLeg = (start, end, bike) => {
    const fallback = { method: "straight_line", path: [start, end] };
    const params = new URLSearchParams({
      startLat: String(start.latitude),
      startLon: String(start.longitude),
      endLat: String(end.latitude),
      endLon: String(end.longitude),
      bike: String(bike),
    });
    const query = params.toString();

    if (!requests.has(query)) {
      requests.set(query, fetch(`${API_BASE_URL}/api/v1/routes?${query}`, { signal })
        .then(async (response) => {
          if (!response.ok) return fallback;
          const { method, path } = await response.json();
          const validPath = Array.isArray(path) && path.length >= 2
            && path.every((point) => Number.isFinite(point?.latitude)
              && Number.isFinite(point?.longitude)
              && Math.abs(point.latitude) <= 90
              && Math.abs(point.longitude) <= 180);
          return method === "route_api" && validPath ? { method, path } : fallback;
        })
        .catch(() => fallback));
    }
    return requests.get(query);
  };

  return Object.fromEntries(await Promise.all(routes.map(async (route) => {
    const rental = { latitude: route.origin_latitude, longitude: route.origin_longitude };
    const returnStation = {
      latitude: route.destination_latitude,
      longitude: route.destination_longitude,
    };
    const legs = await Promise.all([
      getLeg(origin, rental, false),
      getLeg(rental, returnStation, true),
      getLeg(returnStation, destination, false),
    ]);
    return [route.rank, legs];
  })));
}
