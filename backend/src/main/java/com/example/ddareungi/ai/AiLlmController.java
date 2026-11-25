package com.example.ddareungi.ai;

import java.util.Map;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestClient;

@RestController
@RequestMapping("/api/v1/llm")
public class AiLlmController {

    private final RestClient restClient;
    private final AiLlmClient aiLlmClient;

    public AiLlmController(
            @Qualifier("aiRestClient") RestClient aiRestClient,
            AiLlmClient aiLlmClient
    ) {
        this.restClient = aiRestClient;
        this.aiLlmClient = aiLlmClient;
    }

    @PostMapping(
            value = "/recommendation-reasons",
            produces = MediaType.APPLICATION_JSON_VALUE
    )
    public String recommendationReasons(
            @RequestBody Map<String, Object> request
    ) {
        return aiLlmClient.getRecommendationReasons(request);
    }

    @PostMapping(
            value = "/operator-copilot/briefing",
            produces = MediaType.APPLICATION_JSON_VALUE
    )
    public String briefing(
            @RequestBody Map<String, Object> request
    ) {
        return callAi("/llm/operator-copilot/briefing", request);
    }

    @PostMapping(
            value = "/operator-copilot/diagnosis",
            produces = MediaType.APPLICATION_JSON_VALUE
    )
    public String diagnosis(
            @RequestBody Map<String, Object> request
    ) {
        return callAi("/llm/operator-copilot/diagnosis", request);
    }

    @PostMapping(
            value = "/operator-copilot/qa",
            produces = MediaType.APPLICATION_JSON_VALUE
    )
    public String qa(
            @RequestBody Map<String, Object> request
    ) {
        return callAi("/llm/operator-copilot/qa", request);
    }

    @PostMapping(
            value = "/route-reasons",
            produces = MediaType.APPLICATION_JSON_VALUE
    )
    public String routeReasons(
            @RequestBody Map<String, Object> request
    ) {
        return callAi(
                "/llm/route-reasons",
                request
        );
    }

    private String callAi(
            String path,
            Map<String, Object> request
    ) {
        return restClient.post()
                .uri(path)
                .contentType(MediaType.APPLICATION_JSON)
                .body(request)
                .retrieve()
                .body(String.class);
    }
}
