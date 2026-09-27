package com.example.ddareungi.api.station.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.Instant;

public class StationStatus {
    @JsonProperty("station_id")
    private String stationId;
    @JsonProperty("station_name")
    private String stationName;
    @JsonProperty("district")
    private String district;
    @JsonProperty("latitude")
    private Double latitude;
    @JsonProperty("longitude")
    private Double longitude;
    @JsonProperty("capacity")
    private Integer capacity;
    @JsonProperty("bikes_now")
    private Integer bikesNow;
    @JsonProperty("docks_now")
    private Integer docksNow;
    @JsonProperty("collected_at")
    private Instant collectedAt;

    public StationStatus(
        String stationId,
        String stationName,
        String district,
        Double latitude,
        Double longitude,
        Integer capacity,
        Integer bikesNow,
        Integer docksNow,
        Instant collectedAt
    ){
        this.stationId = stationId;
        this.stationName = stationName;
        this.district = district;
        this.latitude = latitude;
        this.longitude = longitude;
        this.capacity = capacity;
        this.bikesNow = bikesNow;
        this.docksNow = docksNow;
        this.collectedAt = collectedAt;
    }

    public String getStationId(){
        return stationId;
    }

    public String getStationName(){
        return stationName;
    }

    public String getDistrict(){
        return district;
    }

    public Double getLatitude(){
        return latitude;
    }

    public Double getLongitude(){
        return longitude;
    }

    public Integer getCapacity(){
        return capacity;
    }

    public Integer getBikesNow(){
        return bikesNow;
    }

    public Integer getDocksNow() {
        return docksNow;
    }

    public Instant getCollectedAt(){
        return collectedAt;
    }
}
