package com.example.ddareungi.api.station;

import com.example.ddareungi.api.station.dto.NearbyStation;
import com.example.ddareungi.domain.station.Station;
import com.example.ddareungi.domain.station.StationRepository;
import com.example.ddareungi.mobility.TravelTimeService;
import org.springframework.stereotype.Service;
import com.example.ddareungi.mobility.dto.TravelTimeResponse;

import java.util.Comparator;
import java.util.List;

@Service
public class NearbyStationService {

    private final StationRepository stationRepository;
    private final TravelTimeService travelTimeService;

    public NearbyStationService(
            StationRepository stationRepository,
            TravelTimeService travelTimeService
    ) {
        this.stationRepository = stationRepository;
        this.travelTimeService = travelTimeService;
    }

    public List<NearbyStation> findNearbyStations(
            double latitude,
            double longitude,
            double radiusM
    ) {

        return stationRepository.findAll().stream()

                // 먼저 직선거리로 800m 이내인지 판단
                .filter(station -> {
                    double straightDistanceM =
                            travelTimeService.calculateHaversineDistanceKm(
                                    latitude,
                                    longitude,
                                    station.getLatitude(),
                                    station.getLongitude()
                            ) * 1000.0;

                    return straightDistanceM <= radiusM;
                })

                // 통과한 대여소만 사용자용 이동거리/시간 계산
                .map(station -> toNearbyStation(
                        station,
                        latitude,
                        longitude
                ))

                // 실제 보행 경로도 요청 반경 이내인 대여소만 반환
                .filter(station -> station.getDistanceM() <= radiusM)

                .sorted(Comparator.comparing(NearbyStation::getDistanceM))

                .toList();
    }

    private NearbyStation toNearbyStation(
            Station station,
            double latitude,
            double longitude
    ) {

        TravelTimeResponse travelTime =
                travelTimeService.estimateTravelTime(
                        latitude,
                        longitude,
                        station.getLatitude(),
                        station.getLongitude(),
                        false   // false = 도보
                );

        return new NearbyStation(
                station.getStationId(),
                station.getStationName(),
                station.getLatitude(),
                station.getLongitude(),
                travelTime.getDistanceM(),
                travelTime.getEtaMin(),
                travelTime.getMethod()
        );
    }
}