package com.example.ddareungi.api.station;

import com.example.ddareungi.collector.BikeApiService;
import com.example.ddareungi.api.station.dto.StationStatus;
import com.example.ddareungi.collector.BikeStation;
import com.example.ddareungi.domain.station.Station;
import com.example.ddareungi.domain.station.StationRepository;

import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class StationStatusService {

    private final StationRepository stationRepository;
    private final BikeApiService bikeApiService;

    public StationStatusService(
            StationRepository stationRepository,
            BikeApiService bikeApiService
    ) {
        this.stationRepository = stationRepository;
        this.bikeApiService = bikeApiService;
    }

    public List<StationStatus> getStationStatuses() {

        List<Station> stations = stationRepository.findAll();
        List<BikeStation> realtimeData =
                bikeApiService.getRealtimeBikeData();

        Map<String, BikeStation> realtimeMap = new HashMap<>();

        for (BikeStation bike : realtimeData) {
            realtimeMap.put(bike.getStationId(), bike);
        }

        List<StationStatus> result = new ArrayList<>();

        Instant collectedAt = Instant.now();

        for (Station station : stations) {

            BikeStation bike =
                    realtimeMap.get(station.getStationId());

            if (bike == null) {
                continue;
            }

            int capacity = Integer.parseInt(bike.getRackTotCnt());
            int bikesNow = Integer.parseInt(
                    bike.getParkingBikeTotCnt()
            );

            int docksNow = Math.max(capacity - bikesNow, 0);

            result.add(new StationStatus(
                    station.getStationId(),
                    station.getStationName(),
                    station.getDistrict(),
                    station.getLatitude(),
                    station.getLongitude(),
                    capacity,
                    bikesNow,
                    docksNow,
                    collectedAt
            ));
        }

        return result;
    }
}
