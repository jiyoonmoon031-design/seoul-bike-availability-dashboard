package com.example.ddareungi.prediction.dto;

import java.time.OffsetDateTime;
import java.util.List;
import com.fasterxml.jackson.annotation.JsonProperty;

public class PredictionRequest {
    @JsonProperty("request_id")
    private String requestId;
    @JsonProperty("base_time")
    private OffsetDateTime baseTime;
    @JsonProperty("station_ids")
    private List<String> stationIds;
    private List<Integer> horizons;

    public PredictionRequest(){
    }

    public PredictionRequest(
            String requestId,
            OffsetDateTime baseTime,
            List<String> stationIds,
            List<Integer> horizons
    ){
        this.requestId=requestId;
        this.baseTime = baseTime;
        this.stationIds = stationIds;
        this.horizons = horizons;
    }

    public String getRequestId(){
        return requestId;
    }

    public OffsetDateTime getBaseTime(){
        return baseTime;
    }

    public List<String> getStationIds(){
        return stationIds;
    }

    public List<Integer> getHorizons(){
        return horizons;
    }
}
