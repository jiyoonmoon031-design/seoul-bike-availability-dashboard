package com.example.ddareungi.ai;

import com.example.ddareungi.ai.dto.AiRecommendationRequest;
import com.example.ddareungi.api.recommendation.dto.RecommendationResponse;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class AiRecommendationClient {

    private final RestClient restClient;
    private final String recommendPath;

    public AiRecommendationClient(
            RestClient.Builder builder,
            @Value("${ai.server.url}") String baseUrl,
            @Value("${ai.server.recommend-path}") String recommendPath
    ) {
        this.restClient = builder.baseUrl(baseUrl).build();
        this.recommendPath = recommendPath;
    }

    public RecommendationResponse recommend(
            AiRecommendationRequest request
    ) {
        return restClient.post()
                .uri(recommendPath)
                .body(request)
                .retrieve()
                .body(RecommendationResponse.class);
    }
}
