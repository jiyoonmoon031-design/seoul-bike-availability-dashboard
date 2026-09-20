package com.example.ddareungi.prediction.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public class PredictionWarning {
    @JsonProperty("station_id")
    private String stationId;
    @JsonProperty("horizon_min")
    private Integer horizonMin;
    private String code;
    private String message;

    public PredictionWarning(
            String stationId,
            Integer horizonMin,
            String code,
            String message
    ){
        this.stationId = stationId;
        this.horizonMin = horizonMin;
        this.code = code;
        this.message = message;
    }

    public String getStationId(){
        return stationId;
    }

    public Integer getHorizonMin(){
        return horizonMin;
    }

    public String getCode(){
        return code;
    }

    public String getMessage(){
        return message;
    }
}
