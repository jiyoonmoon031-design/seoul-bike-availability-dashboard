package com.example.ddareungi.mobility.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public class TravelTimeResponse {

    @JsonProperty("distance_m")
    private double distanceM;

    @JsonProperty("eta_min")
    private int etaMin;

    @JsonProperty("method")
    private String method;

    public TravelTimeResponse(
            double distanceM,
            int etaMin,
            String method
    ){
        this.distanceM = distanceM;
        this.etaMin = etaMin;
        this.method = method;
    }

    public double getDistanceM(){
        return distanceM;
    }

    public int getEtaMin(){
        return etaMin;
    }

    public String getMethod(){
        return method;
    }

}
