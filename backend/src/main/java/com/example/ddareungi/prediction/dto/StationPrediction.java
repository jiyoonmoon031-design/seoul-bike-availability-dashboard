package com.example.ddareungi.prediction.dto;

import java.util.List;
import com.fasterxml.jackson.annotation.JsonProperty;

public class StationPrediction {
    @JsonProperty("station_id")
    private String stationId;
    private Integer capacity;
    @JsonProperty("bikes_now")
    private Integer bikesNow;
    @JsonProperty("inventory_source")
    private String inventorySource;
    @JsonProperty("horizon_results")
    private List<HorizonResult> horizonResults;

    public StationPrediction(
        String stationId,
        Integer capacity,
        Integer bikesNow,
        String inventorySource,
        List<HorizonResult> horizonResults
    ){
        this.stationId = stationId;
        this.capacity = capacity;
        this.bikesNow = bikesNow;
        this.inventorySource = inventorySource;
        this.horizonResults = horizonResults;
    }

    public String getStationId(){
        return stationId;
    }

    public Integer getCapacity(){
        return capacity;
    }

    public Integer getBikesNow(){
        return bikesNow;
    }

    public String getInventorySource(){
        return inventorySource;
    }

    public List<HorizonResult> getHorizonResults(){
        return horizonResults;
    }

}
