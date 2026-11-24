
package com.example.ddareungi.ai.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record LlmReasonResponse(
        List<Reason> reasons
) {
    public record Reason(
            Integer rank,
            @JsonProperty("station_name") String stationName,
            String text
    ) {}
}
