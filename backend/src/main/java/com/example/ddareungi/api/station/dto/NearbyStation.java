package com.example.ddareungi.api.station.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public class NearbyStation {

    @JsonProperty("station_id")
    private String stationId;

    @JsonProperty("station_name")
    private String stationName;

    private Double latitude;
    private Double longitude;

    @JsonProperty("distance_m")
    private Double distanceM;

    @JsonProperty("walk_min")
    private Integer walkMin;

    private String method;

    public NearbyStation(
            String stationId,
            String stationName,
            Double latitude,
            Double longitude,
            Double distanceM,
            Integer walkMin,
            String method
    ) {
        this.stationId = stationId;
        this.stationName = stationName;
        this.latitude = latitude;
        this.longitude = longitude;
        this.distanceM = distanceM;
        this.walkMin = walkMin;
        this.method = method;
    }

    public String getStationId() {
        return stationId;
    }

    public String getStationName() {
        return stationName;
    }

    public Double getLatitude() {
        return latitude;
    }

    public Double getLongitude() {
        return longitude;
    }

    public Double getDistanceM() {
        return distanceM;
    }

    public Integer getWalkMin() {
        return walkMin;
    }

    public String getMethod() {
        return method;
    }
}