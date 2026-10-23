package com.example.ddareungi.api.mobility;

import com.example.ddareungi.mobility.TravelTimeService;
import com.example.ddareungi.mobility.dto.TravelTimeResponse;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import com.example.ddareungi.mobility.TmapRouteService;
import com.example.ddareungi.mobility.dto.RouteResponse;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class TravelTimeServiceTest {

    private final TravelTimeService travelTimeService =
            new TravelTimeService(null);

    @Test
    void sameLocationReturnsZeroDistance() {

        double distance = travelTimeService.calculateHaversineDistanceKm(
                37.547,
                127.071,
                37.547,
                127.071
        );

        assertEquals(0.0, distance, 0.0001);
    }

    @Test
    void estimateByStraightLine_walk_returnsEstimatedTravelTime() {

        TravelTimeResponse result =
                travelTimeService.estimateByStraightLine(
                        37.550638,
                        127.074259,
                        37.551638,
                        127.074259,
                        false       // 도보
                );

        assertTrue(result.getDistanceM() > 0);
        assertTrue(result.getEtaMin() > 0);
        assertEquals("straight_line", result.getMethod());
    }

    @Test
    void estimateByStraightLine_bike_isFasterThanWalking() {

        TravelTimeResponse walk =
                travelTimeService.estimateByStraightLine(
                        37.550638,
                        127.074259,
                        37.560638,
                        127.074259,
                        false
                );

        TravelTimeResponse bike =
                travelTimeService.estimateByStraightLine(
                        37.550638,
                        127.074259,
                        37.560638,
                        127.074259,
                        true
                );

        assertEquals(
                walk.getDistanceM(),
                bike.getDistanceM(),
                0.001
        );

        assertTrue(bike.getEtaMin() < walk.getEtaMin());

        assertEquals("straight_line", bike.getMethod());
    }

    @Test
    void estimateTravelTime_whenTmapFails_usesStraightLineFallback() {

        // TMAP 서비스를 가짜 객체로 생성
        TmapRouteService tmapRouteService = mock(TmapRouteService.class);

        // TMAP 호출 시 장애가 발생했다고 가정
        when(tmapRouteService.getPedestrianRoute(
                37.539182674872,
                127.074711902268,
                37.544,
                127.070
        )).thenThrow(new RuntimeException("TMAP API failure"));

        TravelTimeService service =
                new TravelTimeService(tmapRouteService);

        TravelTimeResponse result =
                service.estimateTravelTime(
                        37.539182674872,
                        127.074711902268,
                        37.544,
                        127.070,
                        false
                );

        assertTrue(result.getDistanceM() > 0);
        assertTrue(result.getEtaMin() > 0);

        // TMAP 실패 → Haversine fallback을 사용했는지 확인
        assertEquals("straight_line", result.getMethod());
    }

    @Test
    void getRoute_whenTmapFails_returnsStraightLinePath() {

        TmapRouteService tmapRouteService = mock(TmapRouteService.class);

        when(tmapRouteService.getPedestrianRoute(
                37.539182674872,
                127.074711902268,
                37.544,
                127.070
        )).thenThrow(new RuntimeException("TMAP API failure"));

        TravelTimeService service =
                new TravelTimeService(tmapRouteService);

        RouteResponse result =
                service.getRoute(
                        37.539182674872,
                        127.074711902268,
                        37.544,
                        127.070,
                        false
                );

        assertEquals("straight_line", result.getMethod());

        // fallback 경로는 출발점 + 도착점만 존재
        assertEquals(2, result.getPath().size());

        assertEquals(
                37.539182674872,
                result.getPath().get(0).getLatitude(),
                0.000001
        );

        assertEquals(
                127.074711902268,
                result.getPath().get(0).getLongitude(),
                0.000001
        );

        assertEquals(
                37.544,
                result.getPath().get(1).getLatitude(),
                0.000001
        );

        assertEquals(
                127.070,
                result.getPath().get(1).getLongitude(),
                0.000001
        );
    }
}
