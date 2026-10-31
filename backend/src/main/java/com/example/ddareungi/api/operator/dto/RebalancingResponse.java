package com.example.ddareungi.api.operator.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.OffsetDateTime;
import java.util.List;

public record RebalancingResponse(

        @JsonProperty("base_time")
        OffsetDateTime baseTime,

        @JsonProperty("horizon_min")
        int horizonMin,

        @JsonProperty("shortage_top")
        List<ShortageStation> shortageTop,

        @JsonProperty("surplus_top")
        List<SurplusStation> surplusTop,

        @JsonProperty("move_matches")
        List<MoveMatch> moveMatches

) {
}
