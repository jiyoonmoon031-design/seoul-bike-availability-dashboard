package com.example.ddareungi.api.station;

import com.example.ddareungi.api.station.dto.NearbyStation;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/stations")
public class NearbyStationController {

    private static final double DEFAULT_RADIUS_M = 800.0;

    private final NearbyStationService nearbyStationService;

    public NearbyStationController(
            NearbyStationService nearbyStationService
    ) {
        this.nearbyStationService = nearbyStationService;
    }

    @GetMapping("/nearby")
    public List<NearbyStation> getNearbyStations(
            @RequestParam double latitude,
            @RequestParam double longitude,
            @RequestParam(defaultValue = "800") double radius
    ) {
        return nearbyStationService.findNearbyStations(
                latitude,
                longitude,
                radius
        );
    }
}