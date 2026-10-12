package com.example.ddareungi.api.station;

import com.example.ddareungi.api.station.dto.NearbyStation;
import com.example.ddareungi.domain.station.Station;
import com.example.ddareungi.domain.station.StationRepository;
import com.example.ddareungi.mobility.TravelTimeService;
import org.springframework.stereotype.Service;
import com.example.ddareungi.mobility.dto.TravelTimeResponse;

import java.util.AbstractMap;
import java.util.Comparator;
import java.util.List;

@Service
public class NearbyStationService {

    private final StationRepository stationRepository;
    private final TravelTimeService travelTimeService;
    private static final int MAX_NEARBY_STATIONS = 20;

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

                // 대여소별 직선거리 계산
                .map(station -> new AbstractMap.SimpleEntry<>(
                        station,
                        travelTimeService.calculateHaversineDistanceKm(
                                latitude,
                                longitude,
                                station.getLatitude(),
                                station.getLongitude()
                        ) * 1000.0
                ))

                // 직선거리 기준 반경 내 대여소 필터링
                .filter(entry -> entry.getValue() <= radiusM)

                // 직선거리 기준 가까운 순서로 정렬
                .sorted(Comparator.comparingDouble(
                        entry -> entry.getValue()
                ))

                // TMAP 호출 전 후보 최대 20개로 제한
                .limit(MAX_NEARBY_STATIONS)

                // 선정된 후보만 실제 도보 경로 계산
                .map(entry -> toNearbyStation(
                        entry.getKey(),
                        latitude,
                        longitude
                ))

                // 실제 보행거리 기준 반경 내 대여소 필터링
                .filter(station -> station.getDistanceM() <= radiusM)

                // 실제 보행거리 기준 가까운 순서로 정렬
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
