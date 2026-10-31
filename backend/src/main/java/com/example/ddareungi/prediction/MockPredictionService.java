package com.example.ddareungi.prediction;

import com.example.ddareungi.prediction.dto.*;
import org.springframework.stereotype.Service;

import java.util.List;
import org.springframework.context.annotation.Profile;

@Service
@Profile("mock")
public class MockPredictionService implements PredictionProvider {
    @Override
    public PredictionResponse predict(PredictionRequest request){
        HorizonResult result15 = new HorizonResult(
                15,
                3.2,
                11.8,
                18.2,
                "model"
        );

        HorizonResult result30 = new HorizonResult(
                30,
                6.5,
                8.5,
                21.5,
                "model"
        );
        List<HorizonResult> horizonResults = List.of(result15, result30);

        StationPrediction stationPrediction = new StationPrediction(
                "ST0002",
                30,
                15,
                "cache",
                horizonResults
        );
        List<StationPrediction> predictions = List.of(stationPrediction);

        PredictionWarning warning1 = new PredictionWarning(
                "ST0002",
                null,
                "STALE_INVENTORY",
                "Latest station snapshot is older than 5 minutes."
        );
        PredictionWarning warning2 = new PredictionWarning(
                "ST0002",
                60,
                "PREDICTION_UNAVAILABLE",
                "Prediction failed for the requested horizon."
        );
        List<PredictionWarning> warningsResult = List.of(warning1, warning2) ;

        PredictionResponse response = new PredictionResponse(
                request.getRequestId(),
                request.getBaseTime(),
                "mock-v1.0.0",
                predictions,
                warningsResult
        );

        return response;
    }
}
