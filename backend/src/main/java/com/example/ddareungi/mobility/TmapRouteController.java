package com.example.ddareungi.mobility;

import com.example.ddareungi.mobility.dto.RouteResponse;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

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
        if (!(Math.abs(startLat) <= 90 && Math.abs(endLat) <= 90
                && Math.abs(startLon) <= 180 && Math.abs(endLon) <= 180)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid route coordinates");
        }
        return travelTimeService.getRoute(
                startLat,
                startLon,
                endLat,
                endLon,
                bike
        );
    }
}
