package com.example.ddareungi.ai.dto;

import com.example.ddareungi.prediction.dto.PredictionResponse;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

public record AiRebalancingRequest(
        @JsonProperty("prediction_response")
        PredictionResponse predictionResponse,

        @JsonProperty("station_contexts")
        List<Map<String, Object>> stationContexts,

        @JsonProperty("horizon_min")
        int horizonMin,

        @JsonProperty("top_n")
        int topN
) {
}
