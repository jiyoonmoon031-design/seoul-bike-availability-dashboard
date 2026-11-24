package com.example.ddareungi.ai;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.util.Map;

@Component
public class AiLlmClient {

    private final RestClient restClient;
    private final String operatorBriefingPath;
    private final String recommendationReasonsPath;

    public AiLlmClient(
            @Qualifier("aiRestClient") RestClient aiRestClient,
            @Value("${ai.server.operator-briefing-path:/llm/operator-briefing}")
            String operatorBriefingPath,
            @Value("${ai.server.recommendation-reasons-path:/llm/recommendation-reasons}")
            String recommendationReasonsPath
    ) {
        this.restClient = aiRestClient;

        this.operatorBriefingPath = operatorBriefingPath;
        this.recommendationReasonsPath = recommendationReasonsPath;
    }

    public String getOperatorBriefing(Map<String, Object> request) {
        return restClient.post()
                .uri(operatorBriefingPath)
                .body(request)
                .retrieve()
                .body(String.class);
    }

    public String getRecommendationReasons(Map<String, Object> request) {
        return restClient.post()
                .uri(recommendationReasonsPath)
                .body(request)
                .retrieve()
                .body(String.class);
    }
}
