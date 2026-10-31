package com.example.ddareungi.prediction;

import com.example.ddareungi.prediction.dto.PredictionRequest;
import com.example.ddareungi.prediction.dto.PredictionResponse;

import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

@RestController
public class PredictionController {

    private final PredictionProvider predictionProvider;

    public PredictionController(
            PredictionProvider predictionProvider
    ) {
        this.predictionProvider = predictionProvider;
    }

    @PostMapping("/api/v1/predict")
    public PredictionResponse predict(
            @RequestBody PredictionRequest request
    ) {
        return predictionProvider.predict(request);
    }
}
