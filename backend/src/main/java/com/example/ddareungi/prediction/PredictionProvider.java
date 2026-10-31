package com.example.ddareungi.prediction;

import com.example.ddareungi.prediction.dto.PredictionRequest;
import com.example.ddareungi.prediction.dto.PredictionResponse;

public interface PredictionProvider {

    PredictionResponse predict(PredictionRequest request);

}
