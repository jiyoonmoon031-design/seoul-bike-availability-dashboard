package com.example.ddareungi.mobility.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

public class RouteResponse {

    @JsonProperty("distance_m")
    private double distanceM;

    @JsonProperty("eta_min")
    private int etaMin;

    private String method;

    private List<RouteCoordinate> path;

    public RouteResponse(
            double distanceM,
            int etaMin,
            String method,
            List<RouteCoordinate> path
    ) {
        this.distanceM = distanceM;
        this.etaMin = etaMin;
        this.method = method;
        this.path = path;
    }

    public double getDistanceM() {
        return distanceM;
    }

    public int getEtaMin() {
        return etaMin;
    }

    public String getMethod() {
        return method;
    }

    public List<RouteCoordinate> getPath() {
        return path;
    }
}