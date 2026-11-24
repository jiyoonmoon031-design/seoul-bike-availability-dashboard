package com.example.ddareungi.mobility;

import com.example.ddareungi.mobility.dto.RouteCoordinate;
import com.example.ddareungi.mobility.dto.TmapFeature;
import com.example.ddareungi.mobility.dto.TmapProperties;
import com.example.ddareungi.mobility.dto.TmapRouteResponse;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class TmapRouteControllerTest {
    private static final String PATH =
            "/api/v1/routes?startLat=37.55&startLon=127.07&endLat=37.54&endLon=127.05";
    private final TmapRouteService tmap = mock(TmapRouteService.class);
    private final TmapRouteResponse route = mock(TmapRouteResponse.class);
    private final MockMvc mvc = MockMvcBuilders.standaloneSetup(
            new TmapRouteController(new TravelTimeService(tmap))).build();

    @BeforeEach
    void stubTmapSummary() {
        TmapFeature feature = mock(TmapFeature.class);
        TmapProperties properties = mock(TmapProperties.class);
        when(tmap.getPedestrianRoute(37.55, 127.07, 37.54, 127.05)).thenReturn(route);
        when(route.getFeatures()).thenReturn(List.of(feature));
        when(feature.getProperties()).thenReturn(properties);
        when(properties.getTotalDistance()).thenReturn(1500);
        when(properties.getTotalTime()).thenReturn(1200);
    }

    @Test
    void returnsTmapPathAndEstimatesBicycleTime() throws Exception {
        when(tmap.extractPath(route)).thenReturn(List.of(
                new RouteCoordinate(37.55, 127.07),
                new RouteCoordinate(37.542, 127.06),
                new RouteCoordinate(37.54, 127.05)));

        mvc.perform(get(PATH + "&bike=true"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.method").value("route_api"))
                .andExpect(jsonPath("$.eta_min").value(6))
                .andExpect(jsonPath("$.path[1].longitude").value(127.06));
    }

    @Test
    void returnsStraightLineWhenTmapHasNoPath() throws Exception {
        when(tmap.extractPath(route)).thenReturn(List.of());

        mvc.perform(get(PATH))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.method").value("straight_line"))
                .andExpect(jsonPath("$.path.length()").value(2));
    }

    @Test
    void rejectsOutOfRangeCoordinates() throws Exception {
        mvc.perform(get(PATH.replace("37.55", "91")))
                .andExpect(status().isBadRequest());
    }
}
