package com.example.ddareungi.ai.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record LlmReasonRequest(
        String leg,
        @JsonProperty("eta_min") Integer etaMin,
        List<Candidate> candidates
) {
    public record Candidate(
            Integer rank,
            @JsonProperty("station_name") String stationName,
            @JsonProperty("distance_m") Double distanceM,
            @JsonProperty("bikes_expected") Double bikesExpected,
            @JsonProperty("docks_expected") Double docksExpected
    ) {}
}
