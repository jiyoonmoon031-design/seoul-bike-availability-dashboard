package com.example.ddareungi.api.recommendation;

import com.example.ddareungi.api.recommendation.dto.RouteRecommendationResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/routes")
public class RouteRecommendationController {

    private final RouteRecommendationService routeRecommendationService;

    public RouteRecommendationController(
            RouteRecommendationService routeRecommendationService
    ) {
        this.routeRecommendationService = routeRecommendationService;
    }

    @GetMapping("/recommendations")
    public RouteRecommendationResponse recommendRoutes(
            @RequestParam double originLat,
            @RequestParam double originLon,
            @RequestParam double destinationLat,
            @RequestParam double destinationLon
    ) {
        return routeRecommendationService.recommendRoutes(
                originLat,
                originLon,
                destinationLat,
                destinationLon
        );
    }
}
