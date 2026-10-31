package com.example.ddareungi.api.recommendation;

import com.example.ddareungi.api.recommendation.dto.RecommendationResponse;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/recommendations")
public class RecommendationController {

    private final RecommendationService recommendationService;

    public RecommendationController(
            RecommendationService recommendationService
    ) {
        this.recommendationService = recommendationService;
    }

    @GetMapping
    public RecommendationResponse getRecommendations(
            @RequestParam String leg,
            @RequestParam double latitude,
            @RequestParam double longitude,
            @RequestParam(defaultValue = "5") int etaMin,
            @RequestParam(defaultValue = "3") int topN
    ) {
        return recommendationService.recommend(
                leg,
                latitude,
                longitude,
                etaMin,
                topN
        );
    }
}
