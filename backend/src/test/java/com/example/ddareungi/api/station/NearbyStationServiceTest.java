package com.example.ddareungi.api.station;

import com.example.ddareungi.api.station.dto.NearbyStation;
import com.example.ddareungi.domain.station.Station;
import com.example.ddareungi.domain.station.StationRepository;
import com.example.ddareungi.mobility.TmapRouteService;
import com.example.ddareungi.mobility.TravelTimeService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyDouble;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class NearbyStationServiceTest {

    private StationRepository stationRepository;
    private TmapRouteService tmapRouteService;
    private NearbyStationService nearbyStationService;

    @BeforeEach
    void setUp() {

        stationRepository = mock(StationRepository.class);

        // 실제 TMAP API를 호출하지 않도록 mock 생성
        tmapRouteService = mock(TmapRouteService.class);

        // TMAP 호출 실패 상황을 가정
        when(tmapRouteService.getPedestrianRoute(
                anyDouble(),
                anyDouble(),
                anyDouble(),
                anyDouble()
        )).thenThrow(new RuntimeException("TMAP API unavailable"));

        TravelTimeService travelTimeService =
                new TravelTimeService(tmapRouteService);

        nearbyStationService = new NearbyStationService(
                stationRepository,
                travelTimeService
        );
    }

    @Test
    void findNearbyStations_filtersByRadiusAndSortsByDistance() {

        Station nearStation = new Station(
                "ST001",
                "가까운 대여소",
                "광진구",
                37.5510,
                127.0743,
                "서울 광진구",
                20
        );

        Station middleStation = new Station(
                "ST002",
                "중간 대여소",
                "광진구",
                37.5540,
                127.0743,
                "서울 광진구",
                20
        );

        Station farStation = new Station(
                "ST003",
                "먼 대여소",
                "광진구",
                37.5700,
                127.0743,
                "서울 광진구",
                20
        );

        when(stationRepository.findAll())
                .thenReturn(List.of(
                        farStation,
                        middleStation,
                        nearStation
                ));

        List<NearbyStation> result =
                nearbyStationService.findNearbyStations(
                        37.550638,
                        127.074259,
                        800
                );

        // 800m 직선거리 후보 안에는 ST001, ST002만 포함
        assertEquals(2, result.size());

        NearbyStation first = result.get(0);

        // 가장 가까운 대여소가 ST001인지
        assertEquals("ST001", first.getStationId());

        // TMAP 실패 → Haversine fallback을 사용했는지
        assertEquals("straight_line", first.getMethod());

        // 도보 시간이 계산됐는지
        assertEquals(1, first.getWalkMin());

        // 예상 이동거리가 정상적으로 계산됐는지
        assertTrue(first.getDistanceM() > 0);
        assertTrue(first.getDistanceM() < 100);

        // 거리순으로 정렬되어 두 번째가 ST002인지
        assertEquals("ST002", result.get(1).getStationId());
    }
}