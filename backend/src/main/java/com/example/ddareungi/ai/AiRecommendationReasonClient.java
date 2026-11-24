package com.example.ddareungi.ai;

import com.example.ddareungi.ai.dto.LlmReasonRequest;
import com.example.ddareungi.ai.dto.LlmReasonResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class AiRecommendationReasonClient {

    private final RestClient restClient;

    public AiRecommendationReasonClient(
            RestClient.Builder builder,
            @Value("${ai.server.url}") String baseUrl
    ) {
        this.restClient = builder.baseUrl(baseUrl).build();
    }

    public LlmReasonResponse getReasons(LlmReasonRequest request) {
        return restClient.post()
                .uri("/llm/recommendation-reasons")
                .body(request)
                .retrieve()
                .body(LlmReasonResponse.class);
    }
}
