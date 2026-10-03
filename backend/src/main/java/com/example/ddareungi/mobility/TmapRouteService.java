package com.example.ddareungi.mobility;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import com.example.ddareungi.mobility.dto.TmapRouteResponse;
import com.example.ddareungi.mobility.dto.RouteCoordinate;
import com.example.ddareungi.mobility.dto.TmapFeature;

import java.util.ArrayList;
import java.util.List;

import java.util.Map;

@Service
public class TmapRouteService {

    private final RestClient restClient;
    private final String appKey;

    public TmapRouteService(
            @Value("${tmap.api.key}") String appKey
    ) {
        this.appKey = appKey;

        this.restClient = RestClient.builder()
                .baseUrl("https://apis.openapi.sk.com")
                .build();
    }

    public TmapRouteResponse getPedestrianRoute(
            double startLat,
            double startLon,
            double endLat,
            double endLon
    ) {

        Map<String, Object> requestBody = Map.of(
                "startX", startLon,
                "startY", startLat,
                "endX", endLon,
                "endY", endLat,
                "reqCoordType", "WGS84GEO",
                "resCoordType", "WGS84GEO",
                "startName", "출발",
                "endName", "도착"
        );

        return restClient.post()
                .uri("/tmap/routes/pedestrian?version=1")
                .header("appKey", appKey)
                .header("Content-Type", "application/json")
                .body(requestBody)
                .retrieve()
                .body(TmapRouteResponse.class);
    }

    public List<RouteCoordinate> extractPath(TmapRouteResponse route) {

        List<RouteCoordinate> path = new ArrayList<>();

        if (route == null || route.getFeatures() == null) {
            return path;
        }

        for (TmapFeature feature : route.getFeatures()) {

            if (feature.getGeometry() == null) {
                continue;
            }

            // 실제 경로선만 사용
            if (!"LineString".equals(feature.getGeometry().getType())) {
                continue;
            }

            Object coordinates = feature.getGeometry().getCoordinates();

            if (!(coordinates instanceof List<?> coordinateList)) {
                continue;
            }

            for (Object coordinate : coordinateList) {

                if (!(coordinate instanceof List<?> point)) {
                    continue;
                }

                if (point.size() < 2) {
                    continue;
                }

                // TMAP 좌표 순서: [longitude, latitude]
                double longitude =
                        ((Number) point.get(0)).doubleValue();

                double latitude =
                        ((Number) point.get(1)).doubleValue();

                if (!path.isEmpty()) {
                    RouteCoordinate last = path.get(path.size() - 1);

                    if (last.getLatitude() == latitude
                            && last.getLongitude() == longitude) {
                        continue;
                    }
                }

                path.add(
                        new RouteCoordinate(
                                latitude,
                                longitude
                        )
                );
            }
        }

        return path;
    }
}
