package com.example.ddareungi.api.operator;

import com.example.ddareungi.ai.AiRebalancingClient;
import com.example.ddareungi.ai.dto.AiRebalancingRequest;
import com.example.ddareungi.api.operator.dto.OperatorRiskResponse;
import com.example.ddareungi.api.operator.dto.RebalancingResponse;
import com.example.ddareungi.domain.station.Station;
import com.example.ddareungi.domain.station.StationRepository;
import com.example.ddareungi.prediction.PredictionProvider;
import com.example.ddareungi.prediction.dto.PredictionRequest;
import com.example.ddareungi.prediction.dto.PredictionResponse;
import com.example.ddareungi.ai.AiLlmClient;
import com.example.ddareungi.api.operator.dto.MoveMatch;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
public class OperatorService {

    private final PredictionProvider predictionProvider;
    private final StationRepository stationRepository;
    private final AiRebalancingClient aiRebalancingClient;
    private final AiLlmClient aiLlmClient;

    public OperatorService(
            PredictionProvider predictionProvider,
            StationRepository stationRepository,
            AiRebalancingClient aiRebalancingClient,
            AiLlmClient aiLlmClient
    ) {
        this.predictionProvider = predictionProvider;
        this.stationRepository = stationRepository;
        this.aiRebalancingClient = aiRebalancingClient;
        this.aiLlmClient = aiLlmClient;
    }

    public OperatorRiskResponse getRisk(
            OffsetDateTime baseTime,
            int horizon,
            int topn
    ) {
        RebalancingResponse result =
                getRebalancing(baseTime, horizon, topn);

        return new OperatorRiskResponse(
                result.baseTime(),
                result.horizonMin(),
                result.shortageTop(),
                result.surplusTop()
        );
    }

    public RebalancingResponse getRebalancing(
            OffsetDateTime baseTime,
            int horizon,
            int topn
    ) {
        validateRequest(horizon, topn);

        List<Station> stations =
                stationRepository.findByDistrictIn(
                        List.of("광진구", "성동구")
                );

        List<String> stationIds = stations.stream()
                .map(Station::getStationId)
                .toList();

        PredictionRequest predictionRequest =
                new PredictionRequest(
                        UUID.randomUUID().toString(),
                        baseTime,
                        stationIds,
                        List.of(horizon)
                );

        PredictionResponse prediction =
                predictionProvider.predict(predictionRequest);

        List<Map<String, Object>> stationContexts =
                stations.stream()
                        .map(station -> Map.<String, Object>of(
                                "station_id", station.getStationId(),
                                "station_name", station.getStationName(),
                                "district", station.getDistrict(),
                                "latitude", station.getLatitude(),
                                "longitude", station.getLongitude()
                        ))
                        .toList();

        AiRebalancingRequest rebalancingRequest =
                new AiRebalancingRequest(
                        prediction,
                        stationContexts,
                        horizon,
                        topn
                );

        return aiRebalancingClient.rebalance(rebalancingRequest);
    }

    private void validateRequest(int horizon, int topn) {
        if (horizon != 15 && horizon != 30 && horizon != 60) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "horizon must be 15, 30, or 60"
            );
        }

        if (topn < 1 || topn > 100) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "topn must be between 1 and 100"
            );
        }
    }
    public String getOperatorBriefing(
            OffsetDateTime baseTime,
            int horizon,
            int topn
    ) {
        // 기존 AI 재배치 결과 가져오기
        RebalancingResponse result =
                getRebalancing(baseTime, horizon, topn);

        // 대여소 ID를 이름으로 변환하기 위한 조회
        Map<String, String> stationNames =
                stationRepository.findByDistrictIn(
                        List.of("광진구", "성동구")
                ).stream().collect(Collectors.toMap(
                        Station::getStationId,
                        Station::getStationName,
                        (first, second) -> first
                ));

        // 부족 대여소: LLM이 요구하는 필드만 전달
        List<Map<String, Object>> shortageTop =
                result.shortageTop().stream()
                        .map(station -> Map.<String, Object>of(
                                "station_name", station.stationName(),
                                "bikes_expected", station.bikesExpected(),
                                "s_min", station.sMin(),
                                "risk_time", station.riskTime().toString()
                        ))
                        .toList();

        // 이동 추천: 대여소 ID를 이름으로 변환
        List<Map<String, Object>> moveMatches =
                result.moveMatches().stream()
                        .map(move -> Map.<String, Object>of(
                                "from_station_name",
                                stationNames.getOrDefault(
                                        move.fromStationId(),
                                        move.fromStationId()
                                ),
                                "to_station_name",
                                stationNames.getOrDefault(
                                        move.toStationId(),
                                        move.toStationId()
                                ),
                                "move_qty", move.moveQty()
                        ))
                        .toList();

        Map<String, Object> request = Map.of(
                "base_time", result.baseTime().toString(),
                "horizon_min", result.horizonMin(),
                "shortage_top", shortageTop,
                "move_matches", moveMatches
        );

        return aiLlmClient.getOperatorBriefing(request);
    }
}
