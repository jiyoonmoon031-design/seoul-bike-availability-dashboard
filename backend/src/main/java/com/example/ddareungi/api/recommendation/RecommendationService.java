package com.example.ddareungi.api.recommendation;

import com.example.ddareungi.ai.AiRecommendationClient;
import com.example.ddareungi.ai.dto.AiRecommendationRequest;
import com.example.ddareungi.api.recommendation.dto.RecommendationResponse;
import com.example.ddareungi.api.station.NearbyStationService;
import com.example.ddareungi.api.station.StationStatusService;
import com.example.ddareungi.api.station.dto.NearbyStation;
import com.example.ddareungi.api.station.dto.StationStatus;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
public class RecommendationService {

    private final NearbyStationService nearbyStationService;
    private final StationStatusService stationStatusService;
    private final AiRecommendationClient aiRecommendationClient;

    public RecommendationService(
            NearbyStationService nearbyStationService,
            StationStatusService stationStatusService,
            AiRecommendationClient aiRecommendationClient
    ) {
        this.nearbyStationService = nearbyStationService;
        this.stationStatusService = stationStatusService;
        this.aiRecommendationClient = aiRecommendationClient;
    }

    public RecommendationResponse recommend(
            String leg,
            double latitude,
            double longitude,
            int etaMin,
            int topN
    ) {
        if (!"origin".equals(leg) && !"destination".equals(leg)) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "leg must be origin or destination"
            );
        }

        if (etaMin < 0 || topN < 1 || topN > 100) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "Invalid recommendation parameters"
            );
        }

        // 1. 실시간 상태 정보가 있는 주변 대여소 검색
        List<NearbyStation> nearbyStations =
                findRecommendationCandidates(latitude, longitude);

        if (nearbyStations.isEmpty()) {
            throw new ResponseStatusException(
                    HttpStatus.NOT_FOUND,
                    "No nearby stations with available status data"
            );
        }

        // 2. 실시간 대여소 상태 조회
        Map<String, StationStatus> statusMap =
                stationStatusService.getStationStatuses()
                        .stream()
                        .collect(Collectors.toMap(
                                StationStatus::getStationId,
                                Function.identity(),
                                (first, second) -> first
                        ));

        // 3. AI 요청 후보 생성
        List<AiRecommendationRequest.Candidate> candidates =
                nearbyStations.stream()
                        .map(station -> {
                            StationStatus status =
                                    statusMap.get(station.getStationId());

                            return new AiRecommendationRequest.Candidate(
                                    station.getStationId(),
                                    station.getStationName(),
                                    station.getLatitude(),
                                    station.getLongitude(),
                                    station.getDistanceM(),
                                    station.getWalkMin(),
                                    station.getWalkMin(),
                                    status.getBikesNow(),
                                    status.getDocksNow(),
                                    status.getCapacity()
                            );
                        })
                        .toList();

        // 4. Python AI에 추천 요청
        AiRecommendationRequest request =
                new AiRecommendationRequest(
                        leg,
                        etaMin,
                        candidates,
                        topN
                );

        RecommendationResponse response =
                aiRecommendationClient.recommend(request);

        if (response == null) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_GATEWAY,
                    "AI recommendation server returned an empty response"
            );
        }

        return response;
    }

    // 실시간 상태 정보가 있는 주변 대여소 후보 조회
    public List<NearbyStation> findRecommendationCandidates(
            double latitude,
            double longitude
    ) {
        Map<String, StationStatus> statusMap =
                stationStatusService.getStationStatuses()
                        .stream()
                        .collect(Collectors.toMap(
                                StationStatus::getStationId,
                                Function.identity(),
                                (first, second) -> first
                        ));

        // 800m 이내 검색
        List<NearbyStation> stations =
                nearbyStationService.findNearbyStations(
                        latitude, longitude, 800
                );

        List<NearbyStation> candidates = stations.stream()
                .filter(station ->
                        statusMap.containsKey(station.getStationId()))
                .toList();

        // 후보가 없으면 1,200m까지 확대
        if (candidates.isEmpty()) {
            stations = nearbyStationService.findNearbyStations(
                    latitude, longitude, 1200
            );

            candidates = stations.stream()
                    .filter(station ->
                            statusMap.containsKey(station.getStationId()))
                    .toList();
        }

        return candidates;
    }

    public RecommendationResponse recommendWithCandidates(
            String leg,
            List<AiRecommendationRequest.Candidate> candidates,
            int etaMin,
            int topN
    ) {
        if (!"origin".equals(leg) && !"destination".equals(leg)) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "leg must be origin or destination"
            );
        }

        if (candidates == null || candidates.isEmpty()) {
            throw new ResponseStatusException(
                    HttpStatus.NOT_FOUND,
                    "No recommendation candidates"
            );
        }

        if (etaMin < 0 || topN < 1 || topN > 100) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "Invalid recommendation parameters"
            );
        }

        AiRecommendationRequest request =
                new AiRecommendationRequest(
                        leg,
                        etaMin,
                        candidates,
                        topN
                );

        RecommendationResponse response =
                aiRecommendationClient.recommend(request);

        if (response == null) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_GATEWAY,
                    "AI recommendation server returned an empty response"
            );
        }

        return response;
    }

}
