package com.example.ddareungi.prediction.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public class HorizonResult {
    @JsonProperty("horizon_min")
    private Integer horizonMin;
    @JsonProperty("delta_net")
    private double deltaNet;
    @JsonProperty("bikes_expected")
    private double bikesExpected;
    @JsonProperty("docks_expected")
    private double docksExpected;
    @JsonProperty("prediction_source")
    private String predictionSource;

    public HorizonResult(
            Integer horizonMin,
            double deltaNet,
            double bikesExpected,
            Double docksExpected,
            String predictionSource
    ){
        this.horizonMin = horizonMin;
        this.deltaNet = deltaNet;
        this.bikesExpected = bikesExpected;
        this.docksExpected = docksExpected;
        this.predictionSource = predictionSource;
    }

    public Integer getHorizonMin(){
        return horizonMin;
    }

    public double getDeltaNet(){
        return deltaNet;
    }

    public double getBikesExpected(){
        return bikesExpected;
    }

    public double getDocksExpected(){
        return docksExpected;
    }

    public String getPredictionSource(){
        return predictionSource;
    }
}
