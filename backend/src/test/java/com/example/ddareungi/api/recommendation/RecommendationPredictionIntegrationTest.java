package com.example.ddareungi.api.recommendation;

import com.example.ddareungi.ai.AiRecommendationClient;
import com.example.ddareungi.ai.dto.AiRecommendationRequest;
import com.example.ddareungi.api.station.NearbyStationService;
import com.example.ddareungi.api.station.StationStatusService;
import com.example.ddareungi.prediction.PredictionProvider;
import com.example.ddareungi.prediction.dto.HorizonResult;
import com.example.ddareungi.prediction.dto.PredictionRequest;
import com.example.ddareungi.prediction.dto.PredictionResponse;
import com.example.ddareungi.prediction.dto.StationPrediction;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.time.OffsetDateTime;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class RecommendationPredictionIntegrationTest {

    @Test
    void attachesThreePredictionHorizonsBeforeRecommendation() {
        PredictionProvider predictionProvider = mock(PredictionProvider.class);
        RecommendationService service = service(predictionProvider);

        when(predictionProvider.predict(org.mockito.ArgumentMatchers.any()))
                .thenReturn(predictionResponse(List.of(
                        horizon(15, -0.2),
                        horizon(30, -0.4),
                        horizon(60, -0.8)
                )));

        List<AiRecommendationRequest.Candidate> result =
                service.attachPredictions(List.of(candidate()));

        assertEquals(1, result.size());
        assertEquals(3, result.getFirst().horizonResults().size());
        assertEquals(
                List.of(15, 30, 60),
                result.getFirst().horizonResults().stream()
                        .map(HorizonResult::getHorizonMin)
                        .toList()
        );

        ArgumentCaptor<PredictionRequest> request =
                ArgumentCaptor.forClass(PredictionRequest.class);

        verify(predictionProvider).predict(request.capture());
        assertEquals(List.of("ST-382"), request.getValue().getStationIds());
        assertEquals(List.of(15, 30, 60), request.getValue().getHorizons());
        assertTrue(request.getValue().getBaseTime().getSecond() == 0);
        assertEquals(
                0,
                request.getValue().getBaseTime().getMinute() % 15
        );
        assertEquals(
                java.time.ZoneOffset.ofHours(9),
                request.getValue().getBaseTime().getOffset()
        );
    }

    @Test
    void rejectsEmptyPredictionsInsteadOfReturningEmptySuccess() {
        PredictionProvider predictionProvider = mock(PredictionProvider.class);
        RecommendationService service = service(predictionProvider);

        when(predictionProvider.predict(org.mockito.ArgumentMatchers.any()))
                .thenReturn(predictionResponse(List.of()));

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.attachPredictions(List.of(candidate()))
        );

        assertEquals(HttpStatus.BAD_GATEWAY, error.getStatusCode());
    }

    @Test
    void reportsPredictionServiceFailureAsBadGateway() {
        PredictionProvider predictionProvider = mock(PredictionProvider.class);
        RecommendationService service = service(predictionProvider);

        when(predictionProvider.predict(org.mockito.ArgumentMatchers.any()))
                .thenThrow(new RuntimeException("forced failure"));

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.attachPredictions(List.of(candidate()))
        );

        assertEquals(HttpStatus.BAD_GATEWAY, error.getStatusCode());
    }

    private RecommendationService service(
            PredictionProvider predictionProvider
    ) {
        return new RecommendationService(
                mock(NearbyStationService.class),
                mock(StationStatusService.class),
                mock(AiRecommendationClient.class),
                predictionProvider
        );
    }

    private AiRecommendationRequest.Candidate candidate() {
        return new AiRecommendationRequest.Candidate(
                "ST-382",
                "세종대학교 대양AI센터",
                37.5504,
                127.0759,
                120.0,
                2,
                2,
                10,
                10,
                20,
                List.of()
        );
    }

    private PredictionResponse predictionResponse(
            List<HorizonResult> horizons
    ) {
        StationPrediction prediction = new StationPrediction(
                "ST-382",
                20,
                10,
                "realtime",
                horizons
        );

        return new PredictionResponse(
                "request-test",
                OffsetDateTime.parse("2026-11-23T20:00:00+09:00"),
                "test-model",
                List.of(prediction),
                List.of()
        );
    }

    private HorizonResult horizon(
            int horizon,
            double delta
    ) {
        return new HorizonResult(
                horizon,
                delta,
                10 + delta,
                10 - delta,
                "baseline_fallback"
        );
    }
}
