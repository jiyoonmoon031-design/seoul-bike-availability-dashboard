package com.example.ddareungi.api.station;

import com.example.ddareungi.api.station.dto.NearbyStation;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

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
            @RequestParam double longitude
    ) {
        // 위도 검증
        if (!Double.isFinite(latitude)
                || latitude < -90 || latitude > 90) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "latitude must be between -90 and 90"
            );
        }

        // 경도 검증
        if (!Double.isFinite(longitude)
                || longitude < -180 || longitude > 180) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "longitude must be between -180 and 180"
            );
        }

        return nearbyStationService.findNearbyStations(
                latitude,
                longitude,
                DEFAULT_RADIUS_M
        );
    }
}
