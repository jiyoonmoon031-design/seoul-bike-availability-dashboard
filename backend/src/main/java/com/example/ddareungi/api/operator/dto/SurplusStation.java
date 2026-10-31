package com.example.ddareungi.api.operator.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record SurplusStation(

        @JsonProperty("station_id")
        String stationId,

        @JsonProperty("docks_expected")
        double docksExpected,

        @JsonProperty("supply_slack")
        double supplySlack

) {}
