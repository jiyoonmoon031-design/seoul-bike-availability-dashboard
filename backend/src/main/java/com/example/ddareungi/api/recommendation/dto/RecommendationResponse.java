package com.example.ddareungi.api.recommendation.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Map;

public record RecommendationResponse(

        @JsonProperty("leg")
        String leg,

        @JsonProperty("eta_min")
        Integer etaMin,

        @JsonProperty("effective_horizon")
        Map<String, Object> effectiveHorizon,

        @JsonProperty("recommendations")
        List<Recommendation> recommendations,

        @JsonProperty("warnings")
        List<String> warnings

) {
    public record Recommendation(

            @JsonProperty("station_id")
            String stationId,

            @JsonProperty("station_name")
            String stationName,

            @JsonProperty("rank")
            Integer rank,

            @JsonProperty("score")
            Double score,

            @JsonProperty("reason")
            String reason,

            @JsonProperty("distance_m")
            Double distanceM,

            @JsonProperty("walk_min")
            Integer walkMin,

            @JsonProperty("bikes_now")
            Integer bikesNow,

            @JsonProperty("docks_now")
            Integer docksNow,

            @JsonProperty("bikes_expected")
            Double bikesExpected,

            @JsonProperty("docks_expected")
            Double docksExpected,

            @JsonProperty("score_breakdown")
            Map<String, Object> scoreBreakdown
    ) {}
}