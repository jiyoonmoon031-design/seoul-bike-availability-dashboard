package com.example.ddareungi.ai;

import com.example.ddareungi.prediction.PredictionProvider;
import com.example.ddareungi.prediction.dto.PredictionRequest;
import com.example.ddareungi.prediction.dto.PredictionResponse;

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
            RestClient.Builder builder,
            @Value("${ai.server.url}") String baseUrl,
            @Value("${ai.server.predict-path}") String predictPath
    ) {
        this.restClient = builder
                .baseUrl(baseUrl)
                .build();

        this.predictPath = predictPath;
    }

    @Override
    public PredictionResponse predict(PredictionRequest request) {

        return restClient.post()
                .uri(predictPath)
                .body(request)
                .retrieve()
                .body(PredictionResponse.class);
    }
}
