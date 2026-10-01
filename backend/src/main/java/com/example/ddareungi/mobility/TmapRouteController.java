package com.example.ddareungi.mobility;

import com.example.ddareungi.mobility.dto.RouteResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/routes")
public class TmapRouteController {

    private final TravelTimeService travelTimeService;

    public TmapRouteController(TravelTimeService travelTimeService) {
        this.travelTimeService = travelTimeService;
    }

    @GetMapping
    public RouteResponse getRoute(
            @RequestParam double startLat,
            @RequestParam double startLon,
            @RequestParam double endLat,
            @RequestParam double endLon,
            @RequestParam(defaultValue = "false") boolean bike
    ) {
        return travelTimeService.getRoute(
                startLat,
                startLon,
                endLat,
                endLon,
                bike
        );
    }
}