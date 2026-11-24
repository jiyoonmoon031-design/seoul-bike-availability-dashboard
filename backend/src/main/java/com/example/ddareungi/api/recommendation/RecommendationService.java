package com.example.ddareungi.api.recommendation;

import com.example.ddareungi.ai.AiRecommendationClient;
import com.example.ddareungi.ai.dto.AiRecommendationRequest;
import com.example.ddareungi.api.recommendation.dto.RecommendationResponse;
import com.example.ddareungi.api.station.NearbyStationService;
import com.example.ddareungi.api.station.StationStatusService;
import com.example.ddareungi.api.station.dto.NearbyStation;
import com.example.ddareungi.api.station.dto.StationStatus;
import com.example.ddareungi.prediction.PredictionProvider;
import com.example.ddareungi.prediction.dto.HorizonResult;
import com.example.ddareungi.prediction.dto.PredictionRequest;
import com.example.ddareungi.prediction.dto.PredictionResponse;
import com.example.ddareungi.prediction.dto.StationPrediction;

import org.springframework.http.HttpStatus;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
public class RecommendationService {

    private static final Logger log =
            LoggerFactory.getLogger(RecommendationService.class);

    private final NearbyStationService nearbyStationService;
    private final StationStatusService stationStatusService;
    private final AiRecommendationClient aiRecommendationClient;
    private final PredictionProvider predictionProvider;

    private static final List<Integer> PREDICTION_HORIZONS =
            List.of(15, 30, 60);

    private static final ZoneId KST = ZoneId.of("Asia/Seoul");

    public RecommendationService(
            NearbyStationService nearbyStationService,
            StationStatusService stationStatusService,
            AiRecommendationClient aiRecommendationClient,
            PredictionProvider predictionProvider
    ) {
        this.nearbyStationService = nearbyStationService;
        this.stationStatusService = stationStatusService;
        this.aiRecommendationClient = aiRecommendationClient;
        this.predictionProvider = predictionProvider;
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

        long totalStarted = System.nanoTime();
        long stageStarted = totalStarted;

        Map<String, StationStatus> statusMap =
                stationStatusService.getStationStatuses()
                        .stream()
                        .collect(Collectors.toMap(
                                StationStatus::getStationId,
                                Function.identity(),
                                (first, second) -> first
                        ));
        long inventoryMs = elapsedMillis(stageStarted);

        stageStarted = System.nanoTime();
        List<NearbyStation> nearbyStations =
                findRecommendationCandidates(
                        latitude,
                        longitude,
                        statusMap
                );
        long candidateMs = elapsedMillis(stageStarted);

        if (nearbyStations.isEmpty()) {
            throw new ResponseStatusException(
                    HttpStatus.NOT_FOUND,
                    "No nearby stations with available status data"
            );
        }

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
                                    status.getCapacity(),
                                    List.of()
                            );
                        })
                        .toList();

        RecommendationResponse response = recommendWithCandidates(
                leg,
                candidates,
                etaMin,
                topN
        );
        log.info(
                "recommendation_latency inventory_ms={} candidate_ms={} total_ms={} candidates={}",
                inventoryMs,
                candidateMs,
                elapsedMillis(totalStarted),
                candidates.size()
        );
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

        return findRecommendationCandidates(
                latitude,
                longitude,
                statusMap
        );
    }

    private List<NearbyStation> findRecommendationCandidates(
            double latitude,
            double longitude,
            Map<String, StationStatus> statusMap
    ) {
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

        long predictionStarted = System.nanoTime();
        PredictionAttachment attachment =
                attachPredictionBundle(candidates);
        List<AiRecommendationRequest.Candidate> enrichedCandidates =
                attachment.candidates();
        long predictionMs = elapsedMillis(predictionStarted);

        AiRecommendationRequest request =
                new AiRecommendationRequest(
                        leg,
                        etaMin,
                        enrichedCandidates,
                        topN
                );

        long recommendationStarted = System.nanoTime();
        RecommendationResponse response =
                aiRecommendationClient.recommend(request);
        long recommendationMs = elapsedMillis(recommendationStarted);

        if (response == null) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_GATEWAY,
                    "AI recommendation server returned an empty response"
            );
        }

        log.info(
                "recommendation_ai_latency prediction_ms={} scoring_ms={} candidates={}",
                predictionMs,
                recommendationMs,
                candidates.size()
        );
        return new RecommendationResponse(
                response.leg(),
                response.etaMin(),
                response.effectiveHorizon(),
                response.recommendations(),
                response.warnings(),
                attachment.predictionResponse().getModelVersion(),
                attachment.predictionResponse().getBaseTime(),
                attachment.predictionResponse().getWarnings()
        );
    }

    List<AiRecommendationRequest.Candidate> attachPredictions(
            List<AiRecommendationRequest.Candidate> candidates
    ) {
        return attachPredictionBundle(candidates).candidates();
    }

    private PredictionAttachment attachPredictionBundle(
            List<AiRecommendationRequest.Candidate> candidates
    ) {
        List<String> stationIds = candidates.stream()
                .map(AiRecommendationRequest.Candidate::stationId)
                .filter(java.util.Objects::nonNull)
                .distinct()
                .toList();

        OffsetDateTime now = OffsetDateTime.now(KST);

        OffsetDateTime baseTime = now
                .withMinute((now.getMinute() / 15) * 15)
                .withSecond(0)
                .withNano(0);

        PredictionResponse predictionResponse;

        try {
            predictionResponse = predictionProvider.predict(
                    new PredictionRequest(
                            UUID.randomUUID().toString(),
                            baseTime,
                            stationIds,
                            PREDICTION_HORIZONS
                    )
            );
        } catch (RuntimeException error) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_GATEWAY,
                    "Prediction service is unavailable",
                    error
            );
        }

        if (predictionResponse == null
                || predictionResponse.getPredictions() == null) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_GATEWAY,
                    "Prediction service returned an empty response"
            );
        }

        Map<String, StationPrediction> predictionMap =
                predictionResponse.getPredictions().stream()
                        .filter(java.util.Objects::nonNull)
                        .filter(prediction -> prediction.getStationId() != null)
                        .collect(Collectors.toMap(
                                StationPrediction::getStationId,
                                Function.identity(),
                                (first, second) -> first
                        ));

        List<AiRecommendationRequest.Candidate> enriched =
                candidates.stream()
                        .map(candidate -> {
                            StationPrediction prediction =
                                    predictionMap.get(candidate.stationId());

                            List<HorizonResult> horizons =
                                    prediction == null
                                            || prediction.getHorizonResults() == null
                                            ? List.of()
                                            : prediction.getHorizonResults();

                            return new AiRecommendationRequest.Candidate(
                                    candidate.stationId(),
                                    candidate.stationName(),
                                    candidate.latitude(),
                                    candidate.longitude(),
                                    candidate.distanceM(),
                                    candidate.walkMin(),
                                    candidate.etaMin(),
                                    candidate.bikesNow(),
                                    candidate.docksNow(),
                                    candidate.capacity(),
                                    horizons
                            );
                        })
                        .toList();

        boolean hasCompletePrediction = enriched.stream()
                .anyMatch(candidate -> hasRequiredHorizons(
                        candidate.horizonResults()
                ));

        if (!hasCompletePrediction) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_GATEWAY,
                    "No complete 15/30/60 minute prediction is available"
            );
        }

        return new PredictionAttachment(enriched, predictionResponse);
    }

    private record PredictionAttachment(
            List<AiRecommendationRequest.Candidate> candidates,
            PredictionResponse predictionResponse
    ) {}

    private boolean hasRequiredHorizons(
            List<HorizonResult> horizons
    ) {
        if (horizons == null) {
            return false;
        }

        Set<Integer> available = horizons.stream()
                .filter(java.util.Objects::nonNull)
                .map(HorizonResult::getHorizonMin)
                .filter(java.util.Objects::nonNull)
                .collect(Collectors.toSet());

        return available.containsAll(PREDICTION_HORIZONS);
    }

    private static long elapsedMillis(long startedNanos) {
        return (System.nanoTime() - startedNanos) / 1_000_000L;
    }

}
