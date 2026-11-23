package com.example.ddareungi.api.recommendation;

import com.example.ddareungi.mobility.TravelTimeService;
import com.example.ddareungi.mobility.dto.TravelTimeResponse;
import org.springframework.stereotype.Service;
import com.example.ddareungi.api.station.dto.NearbyStation;
import java.util.List;
import java.util.ArrayList;
import com.example.ddareungi.api.recommendation.dto.RecommendationResponse;
import java.util.Map;
import java.util.Comparator;
import java.util.Objects;
import java.util.function.Function;
import java.util.stream.Collectors;
import com.example.ddareungi.api.station.NearbyStationService;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import com.example.ddareungi.ai.dto.AiRecommendationRequest;
import com.example.ddareungi.api.station.dto.StationStatus;
import com.example.ddareungi.api.recommendation.dto.RouteRecommendationResponse;
import java.util.HashMap;
import com.example.ddareungi.api.station.StationStatusService;

@Service
public class RouteRecommendationService {

    private final TravelTimeService travelTimeService;
    private final NearbyStationService nearbyStationService;
    private final RecommendationService recommendationService;
    private final StationStatusService stationStatusService;
    private final RouteRankingPolicy routeRankingPolicy;


    public RouteRecommendationService(
            TravelTimeService travelTimeService,
            NearbyStationService nearbyStationService,
            RecommendationService recommendationService,
            StationStatusService stationStatusService,
            RouteRankingPolicy routeRankingPolicy
    ) {
        this.travelTimeService = travelTimeService;
        this.nearbyStationService = nearbyStationService;
        this.recommendationService = recommendationService;
        this.stationStatusService = stationStatusService;
        this.routeRankingPolicy = routeRankingPolicy;
    }


    public RouteTravelTime calculateRouteTime(
            double originStationLat,
            double originStationLon,
            double destinationStationLat,
            double destinationStationLon,
            int walkToOriginMin,
            int walkToDestinationMin
    ) {
        TravelTimeResponse bikeTravel =
                travelTimeService.estimateTravelTime(
                        originStationLat,
                        originStationLon,
                        destinationStationLat,
                        destinationStationLon,
                        true
                );

        int bikeMin = bikeTravel.getEtaMin();

        int arrivalEtaMin = walkToOriginMin + bikeMin;

        int totalEtaMin =
                arrivalEtaMin + walkToDestinationMin;

        return new RouteTravelTime(
                walkToOriginMin,
                bikeMin,
                walkToDestinationMin,
                arrivalEtaMin,
                totalEtaMin
        );
    }

    public record RouteTravelTime(
            int walkToOriginMin,
            int bikeMin,
            int walkToDestinationMin,
            int arrivalEtaMin,
            int totalEtaMin
    ) {}


    public List<RouteCandidate> createRouteCandidates(
            List<NearbyStation> originStations,
            List<NearbyStation> destinationStations
    ) {
        List<RouteCandidate> routes = new ArrayList<>();

        for (NearbyStation origin : originStations) {
            for (NearbyStation destination : destinationStations) {

                // 같은 대여소끼리는 경로를 만들지 않음
                if (origin.getStationId().equals(destination.getStationId())) {
                    continue;
                }

                RouteTravelTime time = calculateRouteTime(
                        origin.getLatitude(),
                        origin.getLongitude(),
                        destination.getLatitude(),
                        destination.getLongitude(),
                        origin.getWalkMin(),
                        destination.getWalkMin()
                );

                routes.add(new RouteCandidate(
                        origin.getStationId(),
                        origin.getStationName(),
                        destination.getStationId(),
                        destination.getStationName(),
                        time.walkToOriginMin(),
                        time.bikeMin(),
                        time.walkToDestinationMin(),
                        time.arrivalEtaMin(),
                        time.totalEtaMin()
                ));
            }
        }

        return routes;
    }

    public record RouteCandidate(
            String originStationId,
            String originStationName,
            String destinationStationId,
            String destinationStationName,
            int walkToOriginMin,
            int bikeMin,
            int walkToDestinationMin,
            int arrivalEtaMin,
            int totalEtaMin
    ) {}
    public List<NearbyStation> selectTopOriginStations(
            RecommendationResponse aiResponse,
            List<NearbyStation> nearbyStations
    ) {
        if (aiResponse == null || aiResponse.recommendations() == null) {
            return List.of();
        }

        Map<String, NearbyStation> stationMap =
                nearbyStations.stream()
                        .collect(Collectors.toMap(
                                NearbyStation::getStationId,
                                Function.identity(),
                                (first, second) -> first
                        ));

        return aiResponse.recommendations().stream()
                .filter(recommendation -> recommendation.stationId() != null)
                .sorted(Comparator.comparing(
                        RecommendationResponse.Recommendation::rank,
                        Comparator.nullsLast(Comparator.naturalOrder())
                ))
                .limit(3)
                .map(recommendation -> stationMap.get(recommendation.stationId()))
                .filter(Objects::nonNull)
                .toList();
    }


    public List<RouteCandidate> buildRouteCandidates(
            RecommendationResponse originAiResponse,
            List<NearbyStation> originNearbyStations,
            double destinationLat,
            double destinationLon
    ) {
        // 1. AI 추천 출발 대여소 Top3 선택
        List<NearbyStation> topOriginStations =
                selectTopOriginStations(
                        originAiResponse,
                        originNearbyStations
                );

        if (topOriginStations.isEmpty()) {
            return List.of();
        }

        // 2. 실시간 상태 정보가 있는 도착 대여소 검색
        List<NearbyStation> destinationStations =
                recommendationService.findRecommendationCandidates(
                        destinationLat,
                        destinationLon
                );

        if (destinationStations.isEmpty()) {
            return List.of();
        }

        // 3. 출발 Top3 × 도착 후보 경로 생성
        return createRouteCandidates(
                topOriginStations,
                destinationStations
        );
    }

    public List<RouteCandidate> recommendRouteCandidates(
            double originLat,
            double originLon,
            double destinationLat,
            double destinationLon
    ) {
        // 1. 출발지 주변 대여소 후보 검색
        List<NearbyStation> originStations =
                recommendationService.findRecommendationCandidates(
                        originLat,
                        originLon
                );

        if (originStations.isEmpty()) {
            throw new ResponseStatusException(
                    HttpStatus.NOT_FOUND,
                    "No nearby origin stations"
            );
        }

        // 2. AI로 출발 대여소 Top3 추천
        RecommendationResponse originAiResponse =
                recommendationService.recommend(
                        "origin",
                        originLat,
                        originLon,
                        5,
                        3
                );

        // 3. AI 추천 출발 Top3와 도착 후보 연결
        return buildRouteCandidates(
                originAiResponse,
                originStations,
                destinationLat,
                destinationLon
        );
    }

    public List<AiRecommendationRequest.Candidate>
    buildDestinationAiCandidates(
            List<RouteCandidate> routeCandidates,
            List<NearbyStation> destinationStations,
            Map<String, StationStatus> statusMap
    ) {
        Map<String, NearbyStation> destinationMap =
                destinationStations.stream()
                        .collect(Collectors.toMap(
                                NearbyStation::getStationId,
                                Function.identity(),
                                (first, second) -> first
                        ));

        return routeCandidates.stream()
                .filter(route ->
                        destinationMap.containsKey(
                                route.destinationStationId()
                        ))
                .filter(route ->
                        statusMap.containsKey(
                                route.destinationStationId()
                        ))
                .map(route -> {
                    NearbyStation station =
                            destinationMap.get(
                                    route.destinationStationId()
                            );

                    StationStatus status =
                            statusMap.get(
                                    route.destinationStationId()
                            );

                    return new AiRecommendationRequest.Candidate(
                            station.getStationId(),
                            station.getStationName(),
                            station.getLatitude(),
                            station.getLongitude(),
                            station.getDistanceM(),
                            station.getWalkMin(),
                            route.arrivalEtaMin(),
                            status.getBikesNow(),
                            status.getDocksNow(),
                            status.getCapacity(),
                            List.of()
                    );
                })
                .toList();
    }

    public Map<String, RecommendationResponse> recommendDestinationByOrigin(
            List<RouteCandidate> routeCandidates,
            List<NearbyStation> destinationStations,
            Map<String, StationStatus> statusMap
    ) {
        // 출발 대여소 ID별 경로 후보 그룹화
        Map<String, List<RouteCandidate>> routesByOrigin =
                routeCandidates.stream()
                        .collect(Collectors.groupingBy(
                                RouteCandidate::originStationId
                        ));

        Map<String, RecommendationResponse> results =
                new java.util.HashMap<>();

        for (Map.Entry<String, List<RouteCandidate>> entry
                : routesByOrigin.entrySet()) {

            String originStationId = entry.getKey();
            List<RouteCandidate> originRoutes = entry.getValue();

            // 해당 출발 대여소의 도착 후보 AI 요청 데이터 생성
            List<AiRecommendationRequest.Candidate> candidates =
                    buildDestinationAiCandidates(
                            originRoutes,
                            destinationStations,
                            statusMap
                    );

            if (candidates.isEmpty()) {
                continue;
            }

            // 후보별 eta_min이 있으므로 공통 ETA는 호환용 기본값
            RecommendationResponse aiResponse =
                    recommendationService.recommendWithCandidates(
                            "destination",
                            candidates,
                            0,
                            candidates.size()
                    );

            results.put(originStationId, aiResponse);
        }

        return results;
    }


    public List<RouteCandidate> selectTopRoutes(
            List<RouteCandidate> routeCandidates,
            RecommendationResponse originAiResponse,
            Map<String, RecommendationResponse> destinationAiResults
    ) {
        if (routeCandidates == null || routeCandidates.isEmpty()
                || originAiResponse == null
                || originAiResponse.recommendations() == null
                || destinationAiResults == null) {
            return List.of();
        }

        Map<String, RecommendationResponse.Recommendation> originMap =
                originAiResponse.recommendations().stream()
                        .filter(r -> r.stationId() != null)
                        .collect(Collectors.toMap(
                                RecommendationResponse.Recommendation::stationId,
                                Function.identity(),
                                (first, second) -> first
                        ));

        Map<String, Map<String, RecommendationResponse.Recommendation>>
                destinationMap = new HashMap<>();

        for (Map.Entry<String, RecommendationResponse> entry
                : destinationAiResults.entrySet()) {

            RecommendationResponse response = entry.getValue();

            if (response == null || response.recommendations() == null) {
                continue;
            }

            Map<String, RecommendationResponse.Recommendation> byStation =
                    response.recommendations().stream()
                            .filter(r -> r.stationId() != null)
                            .collect(Collectors.toMap(
                                    RecommendationResponse.Recommendation::stationId,
                                    Function.identity(),
                                    (first, second) -> first
                            ));

            destinationMap.put(entry.getKey(), byStation);
        }

        return routeCandidates.stream()
                .filter(route -> {
                    RecommendationResponse.Recommendation origin =
                            originMap.get(route.originStationId());

                    Map<String, RecommendationResponse.Recommendation> byStation =
                            destinationMap.get(route.originStationId());

                    RecommendationResponse.Recommendation destination =
                            byStation == null
                                    ? null
                                    : byStation.get(route.destinationStationId());

                    return origin != null
                            && origin.score() != null
                            && destination != null
                            && destination.score() != null;
                })
                .sorted(
                        Comparator.comparingDouble(
                                        (RouteCandidate route) -> {
                                            double originScore =
                                                    originMap.get(route.originStationId())
                                                            .score();

                                            double destinationScore =
                                                    destinationMap
                                                            .get(route.originStationId())
                                                            .get(route.destinationStationId())
                                                            .score();

                                            return routeRankingPolicy.calculate(
                                                    originScore,
                                                    destinationScore,
                                                    route.totalEtaMin(),
                                                    route.walkToOriginMin(),
                                                    route.walkToDestinationMin()
                                            ).total();
                                        }
                                ).reversed()
                                .thenComparingInt(RouteCandidate::totalEtaMin)
                                .thenComparingInt(route ->
                                        route.walkToOriginMin()
                                                + route.walkToDestinationMin()
                                )
                                .thenComparing(RouteCandidate::originStationId)
                                .thenComparing(RouteCandidate::destinationStationId)
                )
                .limit(3)
                .toList();
    }



    public RouteRecommendationResponse recommendRoutes(
            double originLat,
            double originLon,
            double destinationLat,
            double destinationLon
    ) {
        // 1. 출발 대여소 후보 검색
        List<NearbyStation> originStations =
                recommendationService.findRecommendationCandidates(
                        originLat, originLon
                );

        if (originStations.isEmpty()) {
            throw new ResponseStatusException(
                    HttpStatus.NOT_FOUND,
                    "No nearby origin stations"
            );
        }

        // 2. 출발 대여소 AI 추천 (한 번만 호출)
        RecommendationResponse originAiResponse =
                recommendationService.recommend(
                        "origin",
                        originLat,
                        originLon,
                        5,
                        3
                );

        // 3. 출발 AI Top3와 목적지 대여소 조합
        List<RouteCandidate> routeCandidates =
                buildRouteCandidates(
                        originAiResponse,
                        originStations,
                        destinationLat,
                        destinationLon
                );

        if (routeCandidates.isEmpty()) {
            return new RouteRecommendationResponse(List.of());
        }

        // 4. 도착 대여소 후보 검색
        List<NearbyStation> destinationStations =
                recommendationService.findRecommendationCandidates(
                        destinationLat,
                        destinationLon
                );

        // 5. 현재 대여소 상태 조회
        Map<String, StationStatus> statusMap =
                stationStatusService.getStationStatuses()
                        .stream()
                        .collect(Collectors.toMap(
                                StationStatus::getStationId,
                                Function.identity(),
                                (first, second) -> first
                        ));

        // 6. 출발 대여소별 도착 AI 평가
        Map<String, RecommendationResponse> destinationAiResults =
                recommendDestinationByOrigin(
                        routeCandidates,
                        destinationStations,
                        statusMap
                );

        // 7. 최종 경로 Top3 선정
        List<RouteCandidate> topRoutes =
                selectTopRoutes(
                        routeCandidates,
                        originAiResponse,
                        destinationAiResults
                );

        // 8. 대여소 정보 조회용 Map
        Map<String, NearbyStation> originStationMap =
                originStations.stream()
                        .collect(Collectors.toMap(
                                NearbyStation::getStationId,
                                Function.identity(),
                                (first, second) -> first
                        ));

        Map<String, NearbyStation> destinationStationMap =
                destinationStations.stream()
                        .collect(Collectors.toMap(
                                NearbyStation::getStationId,
                                Function.identity(),
                                (first, second) -> first
                        ));

        // 9. 출발 AI 추천 결과 보존
        Map<String, RecommendationResponse.Recommendation>
                originAiMap = new HashMap<>();

        if (originAiResponse != null
                && originAiResponse.recommendations() != null) {

            for (RecommendationResponse.Recommendation ai
                    : originAiResponse.recommendations()) {

                if (ai.stationId() != null) {
                    originAiMap.putIfAbsent(ai.stationId(), ai);
                }
            }
        }

        // 10. 최종 응답 생성
        List<RouteRecommendationResponse.Route> routes =
                new ArrayList<>();

        for (int i = 0; i < topRoutes.size(); i++) {

            RouteCandidate route = topRoutes.get(i);

            NearbyStation originStation =
                    originStationMap.get(route.originStationId());

            NearbyStation destinationStation =
                    destinationStationMap.get(
                            route.destinationStationId()
                    );

            StationStatus originStatus =
                    statusMap.get(route.originStationId());

            StationStatus destinationStatus =
                    statusMap.get(route.destinationStationId());

            RecommendationResponse.Recommendation originAi =
                    originAiMap.get(route.originStationId());

            // 해당 출발 대여소에 대한 도착 AI 결과
            RecommendationResponse destinationAiResponse =
                    destinationAiResults.get(
                            route.originStationId()
                    );

            RecommendationResponse.Recommendation destinationAi =
                    null;

            if (destinationAiResponse != null
                    && destinationAiResponse.recommendations() != null) {

                destinationAi =
                        destinationAiResponse.recommendations()
                                .stream()
                                .filter(ai ->
                                        route.destinationStationId()
                                                .equals(ai.stationId())
                                )
                                .findFirst()
                                .orElse(null);
            }

            // 종합 점수 = 출발·도착 가용성 + 총 ETA + 양쪽 도보시간
            Double score = null;
            Map<String, Double> scoreBreakdown = Map.of();
            String reason = null;

            if (originAi != null
                    && originAi.score() != null
                    && destinationAi != null
                    && destinationAi.score() != null) {

                RouteRankingPolicy.RouteScore routeScore =
                        routeRankingPolicy.calculate(
                                originAi.score(),
                                destinationAi.score(),
                                route.totalEtaMin(),
                                route.walkToOriginMin(),
                                route.walkToDestinationMin()
                        );

                score = routeScore.total();
                scoreBreakdown = Map.of(
                        "origin_station", routeScore.originStation(),
                        "destination_station", routeScore.destinationStation(),
                        "eta", routeScore.eta(),
                        "walking", routeScore.walking()
                );
                reason = routeRankingPolicy.reason(
                        routeScore,
                        route.totalEtaMin()
                );
            }

            routes.add(new RouteRecommendationResponse.Route(
                    i + 1,

                    route.originStationId(),
                    route.originStationName(),

                    route.destinationStationId(),
                    route.destinationStationName(),

                    route.walkToOriginMin(),
                    route.bikeMin(),
                    route.walkToDestinationMin(),
                    route.totalEtaMin(),
                    score,
                    scoreBreakdown,
                    reason,

                    // 출발 대여소 좌표
                    originStation == null
                            ? null : originStation.getLatitude(),
                    originStation == null
                            ? null : originStation.getLongitude(),

                    // 도착 대여소 좌표
                    destinationStation == null
                            ? null : destinationStation.getLatitude(),
                    destinationStation == null
                            ? null : destinationStation.getLongitude(),

                    // 출발 대여소 현재·예상 자전거 수
                    originStatus == null
                            ? null : originStatus.getBikesNow(),
                    originAi == null
                            ? null : originAi.bikesExpected(),

                    // 도착 대여소 현재·예상 빈 거치대 수
                    destinationStatus == null
                            ? null : destinationStatus.getDocksNow(),
                    destinationAi == null
                            ? null : destinationAi.docksExpected(),

                    // 도보 거리
                    originStation == null
                            ? null : originStation.getDistanceM(),
                    destinationStation == null
                            ? null : destinationStation.getDistanceM(),

                    // 대여소 도착 예상시간
                    route.walkToOriginMin(),
                    route.arrivalEtaMin()
            ));
        }

        return new RouteRecommendationResponse(routes);
    }


}
