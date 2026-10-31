package com.example.ddareungi.ai.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record AiRecommendationRequest(
        @JsonProperty("leg")
        String leg,

        @JsonProperty("eta_min")
        Integer etaMin,

        @JsonProperty("candidates")
        List<Candidate> candidates,

        @JsonProperty("top_n")
        Integer topN
) {
    public record Candidate(
            @JsonProperty("station_id")
            String stationId,

            @JsonProperty("station_name")
            String stationName,

            Double latitude,
            Double longitude,

            @JsonProperty("distance_m")
            Double distanceM,

            @JsonProperty("walk_min")
            Integer walkMin,

            @JsonProperty("eta_min")
            Integer etaMin,

            @JsonProperty("bikes_now")
            Integer bikesNow,

            @JsonProperty("docks_now")
            Integer docksNow,

            Integer capacity
    ) {}
}
