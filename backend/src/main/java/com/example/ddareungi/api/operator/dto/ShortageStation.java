package com.example.ddareungi.api.operator.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.OffsetDateTime;

public record ShortageStation(

        @JsonProperty("station_id")
        String stationId,

        @JsonProperty("station_name")
        String stationName,

        @JsonProperty("lat")
        double lat,

        @JsonProperty("lon")
        double lon,

        @JsonProperty("bikes_expected")
        double bikesExpected,

        @JsonProperty("s_min")
        int sMin,

        @JsonProperty("shortage")
        double shortage,

        @JsonProperty("urgency")
        double urgency,

        @JsonProperty("demand_weight")
        double demandWeight,

        @JsonProperty("priority_score")
        double priorityScore,

        @JsonProperty("risk_time")
        OffsetDateTime riskTime

) {}
