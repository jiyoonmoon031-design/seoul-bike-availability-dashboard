package com.example.ddareungi.prediction.dto;
import java.time.OffsetDateTime;
import java.util.List;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonFormat;

public class PredictionResponse {
    @JsonProperty("request_id")
    private String requestId;
    @JsonProperty("base_time")
    @JsonFormat(
            shape = JsonFormat.Shape.STRING,
            pattern = "yyyy-MM-dd'T'HH:mm:ssXXX",
            timezone = "Asia/Seoul"
    )
    private OffsetDateTime baseTime;
    @JsonProperty("model_version")
    private String modelVersion;
    private List<StationPrediction> predictions;
    private List<PredictionWarning> warnings;

    public PredictionResponse(
            String requestId,
            OffsetDateTime baseTime,
            String modelVersion,
            List<StationPrediction> predictions,
            List<PredictionWarning> warnings
    ){
        this.requestId = requestId;
        this.baseTime = baseTime;
        this.modelVersion = modelVersion;
        this.predictions = predictions;
        this.warnings = warnings;
    }

    public String getRequestId(){
        return requestId;
    }
    public OffsetDateTime getBaseTime(){
        return baseTime;
    }

    public String getModelVersion(){
        return modelVersion;
    }

    public List<StationPrediction> getPredictions(){
        return predictions;
    }

    public List<PredictionWarning> getWarnings(){
        return warnings;
    }

}
