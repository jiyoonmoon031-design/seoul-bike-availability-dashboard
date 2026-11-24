package com.example.ddareungi.mobility;

import com.example.ddareungi.mobility.dto.TravelTimeResponse;
import org.springframework.stereotype.Service;
import com.example.ddareungi.mobility.dto.TmapRouteResponse;
import com.example.ddareungi.mobility.dto.TmapProperties;
import com.example.ddareungi.mobility.dto.RouteCoordinate;
import com.example.ddareungi.mobility.dto.RouteResponse;

import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.client.RestClientResponseException;

@Service
public class TravelTimeService {

    private static final Logger log =
            LoggerFactory.getLogger(TravelTimeService.class);

    private static final double EARTH_RADIUS_KM = 6371.0;
    private static final double DETOUR_FACTOR = 1.3;

    private static final double WALK_SPEED_KMH = 4.0;
    private static final double BIKE_SPEED_KMH = 15.0;

    private final TmapRouteService tmapRouteService;

    private int calculateEta(double distanceM, boolean bike) {

        double distanceKm = distanceM / 1000.0;

        double speedKmh = bike
                ? BIKE_SPEED_KMH
                : WALK_SPEED_KMH;

        double etaMinutes = (distanceKm / speedKmh) * 60.0;

        return (int) Math.ceil(etaMinutes);
    }

    public TravelTimeService(TmapRouteService tmapRouteService) {
        this.tmapRouteService = tmapRouteService;
    }

    public double calculateHaversineDistanceKm(
            double startLat,
            double startLon,
            double endLat,
            double endLon
    ){
        double latDistance = Math.toRadians(endLat - startLat);
        double lonDistance = Math.toRadians(endLon - startLon);

        double startLatRad = Math.toRadians(startLat);
        double endLatRad = Math.toRadians(endLat);

        double a =
                Math.sin(latDistance/2) * Math.sin(latDistance/2)
                + Math.cos(startLatRad)
                * Math.cos(endLatRad)
                * Math.sin(lonDistance/2)
                * Math.sin(lonDistance/2);

        double c = 2 * Math.atan2(
                Math.sqrt(a),
                Math.sqrt(1 - a)
        );

        return EARTH_RADIUS_KM * c;
    }

    public TravelTimeResponse estimateByStraightLine(
            double startLat,
            double startLon,
            double endLat,
            double endLon,
            boolean bike
    ){
        double straightDistanceKm = calculateHaversineDistanceKm(
                startLat,
                startLon,
                endLat,
                endLon
        );

        double estimatedDistanceKm = straightDistanceKm * DETOUR_FACTOR;

        double distanceM = estimatedDistanceKm * 1000.0;

        int etaMin = calculateEta(distanceM, bike);

        return new TravelTimeResponse(
                distanceM,
                etaMin,
                "straight_line"
        );
    }

    public TravelTimeResponse estimateTravelTime(
            double startLat,
            double startLon,
            double endLat,
            double endLon,
            boolean bike
    ) {
        try {
            TmapRouteResponse route = tmapRouteService.getPedestrianRoute(
                    startLat,
                    startLon,
                    endLat,
                    endLon
            );

            if (route == null
                    || route.getFeatures() == null
                    || route.getFeatures().isEmpty()
                    || route.getFeatures().get(0).getProperties() == null
                    || route.getFeatures().get(0).getProperties().getTotalDistance() == null) {

                return estimateByStraightLine(
                        startLat,
                        startLon,
                        endLat,
                        endLon,
                        bike
                );
            }

            TmapProperties properties =
                    route.getFeatures().get(0).getProperties();

            double distanceM = properties.getTotalDistance();

            int etaMin;

            if (bike) {
                // 자전거: TMAP 보행 경로의 거리를 이용해서 직접 추정
                etaMin = calculateEta(distanceM, true);
            } else {
                // 도보: TMAP에서 계산한 보행시간 사용
                Integer totalTime = properties.getTotalTime();

                if (totalTime == null) {
                    etaMin = calculateEta(distanceM, false);
                } else {
                    etaMin = (int) Math.ceil(totalTime / 60.0);
                }
            }

            return new TravelTimeResponse(
                    distanceM,
                    etaMin,
                    "route_api"
            );

        } catch (Exception e) {
            log.warn(
                    "tmap_route_fallback error_type={}",
                    e.getClass().getSimpleName()
            );
            return estimateByStraightLine(
                    startLat,
                    startLon,
                    endLat,
                    endLon,
                    bike
            );
        }
    }

    private RouteResponse getStraightLineRoute(
            double startLat,
            double startLon,
            double endLat,
            double endLon,
            boolean bike
    ) {
        TravelTimeResponse travelTime =
                estimateByStraightLine(
                        startLat,
                        startLon,
                        endLat,
                        endLon,
                        bike
                );

        List<RouteCoordinate> path = List.of(
                new RouteCoordinate(startLat, startLon),
                new RouteCoordinate(endLat, endLon)
        );

        return new RouteResponse(
                travelTime.getDistanceM(),
                travelTime.getEtaMin(),
                travelTime.getMethod(),
                path
        );
    }

    public RouteResponse getRoute(
            double startLat,
            double startLon,
            double endLat,
            double endLon,
            boolean bike
    ) {
        try {
            TmapRouteResponse route = tmapRouteService.getPedestrianRoute(
                    startLat,
                    startLon,
                    endLat,
                    endLon
            );

            if (route == null
                    || route.getFeatures() == null
                    || route.getFeatures().isEmpty()
                    || route.getFeatures().get(0).getProperties() == null
                    || route.getFeatures().get(0).getProperties().getTotalDistance() == null) {

                return getStraightLineRoute(
                        startLat,
                        startLon,
                        endLat,
                        endLon,
                        bike
                );
            }

            TmapProperties properties =
                    route.getFeatures().get(0).getProperties();

            double distanceM = properties.getTotalDistance();

            int etaMin;

            if (bike) {
                // 자전거: TMAP 경로 거리 + 15km/h 기준
                etaMin = calculateEta(distanceM, true);

            } else {
                // 도보: TMAP이 제공한 보행시간 우선 사용
                Integer totalTime = properties.getTotalTime();

                if (totalTime != null) {
                    etaMin = (int) Math.ceil(totalTime / 60.0);
                } else {
                    etaMin = calculateEta(distanceM, false);
                }
            }

            List<RouteCoordinate> path =
                    tmapRouteService.extractPath(route);

            if (path.size() < 2) {
                return getStraightLineRoute(startLat, startLon, endLat, endLon, bike);
            }

            return new RouteResponse(
                    distanceM,
                    etaMin,
                    "route_api",
                    path
            );

        } catch (Exception e) {

            if (e instanceof RestClientResponseException responseError) {
                log.warn("tmap_geometry_fallback upstream_status={}", responseError.getStatusCode().value());
            } else {
                log.warn("tmap_geometry_fallback error_type={}", e.getClass().getSimpleName());
            }

            return getStraightLineRoute(
                    startLat,
                    startLon,
                    endLat,
                    endLon,
                    bike
            );
        }
    }

}
