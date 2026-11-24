package com.example.ddareungi.ai;

import com.example.ddareungi.prediction.PredictionProvider;
import com.example.ddareungi.prediction.dto.PredictionRequest;
import com.example.ddareungi.prediction.dto.PredictionResponse;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

@Service
@Profile("!mock")
public class AiPredictionClient implements PredictionProvider {

    private final RestClient restClient;
    private final String predictPath;

    public AiPredictionClient(
            @Qualifier("aiRestClient") RestClient aiRestClient,
            @Value("${ai.server.predict-path}") String predictPath
    ) {
        this.restClient = aiRestClient;

        this.predictPath = predictPath;
    }

    @Override
    public PredictionResponse predict(PredictionRequest request) {

        String kstBaseTime = java.time.OffsetDateTime
                .parse(String.valueOf(request.getBaseTime()))
                .withOffsetSameInstant(
                        java.time.ZoneOffset.ofHours(9)
                )
                .toString();

        java.util.Map<String, Object> payload =
                new java.util.LinkedHashMap<>();

        payload.put(
                "request_id",
                request.getRequestId()
        );
        payload.put(
                "base_time",
                kstBaseTime
        );
        payload.put(
                "station_ids",
                request.getStationIds()
        );
        payload.put(
                "horizons",
                request.getHorizons()
        );

        return restClient.post()
                .uri(predictPath)
                .body(payload)
                .retrieve()
                .body(PredictionResponse.class);
    }
}
