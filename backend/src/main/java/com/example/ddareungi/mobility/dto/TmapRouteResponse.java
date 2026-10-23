package com.example.ddareungi.mobility.dto;

import java.util.List;

public class TmapRouteResponse {

    private String type;
    private List<TmapFeature> features;

    public String getType() {
        return type;
    }

    public List<TmapFeature> getFeatures() {
        return features;
    }
}
