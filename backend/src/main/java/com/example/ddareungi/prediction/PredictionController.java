package com.example.ddareungi.prediction;

import org.springframework.web.bind.annotation.RestController;
import com.example.ddareungi.prediction.dto.PredictionRequest;
import com.example.ddareungi.prediction.dto.PredictionResponse;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

@RestController
public class PredictionController {
    private final MockPredictionService mockPredictionService;
    public PredictionController(
            MockPredictionService mockPredictionService
    ){
        this.mockPredictionService = mockPredictionService;
    }

    @PostMapping("/api/v1/predict")
    public PredictionResponse predict(@RequestBody PredictionRequest request){
        PredictionResponse response = mockPredictionService.predict(request);
        return response;
    }
}
