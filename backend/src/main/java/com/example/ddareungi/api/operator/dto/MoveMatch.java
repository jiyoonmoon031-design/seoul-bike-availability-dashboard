package com.example.ddareungi.api.operator.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record MoveMatch(

        @JsonProperty("from_station_id")
        String fromStationId,

        @JsonProperty("to_station_id")
        String toStationId,

        @JsonProperty("distance_km")
        double distanceKm,

        @JsonProperty("move_qty")
        int moveQty

) {}
