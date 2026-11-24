
package com.example.ddareungi.api.recommendation.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Map;
import java.time.Instant;
import java.time.OffsetDateTime;
import com.example.ddareungi.prediction.dto.PredictionWarning;

public record RouteRecommendationResponse(
        @JsonProperty("routes")
        List<Route> routes,

        @JsonProperty("model_version")
        String modelVersion,

        @JsonProperty("prediction_base_time")
        OffsetDateTime predictionBaseTime,

        @JsonProperty("prediction_warnings")
        List<PredictionWarning> predictionWarnings
) {
        public RouteRecommendationResponse(List<Route> routes) {
                this(routes, null, null, List.of());
        }

        public record Route(
                @JsonProperty("rank")
                Integer rank,

                @JsonProperty("origin_station_id")
                String originStationId,

                @JsonProperty("origin_station_name")
                String originStationName,

                @JsonProperty("destination_station_id")
                String destinationStationId,

                @JsonProperty("destination_station_name")
                String destinationStationName,

                @JsonProperty("walk_to_origin_min")
                Integer walkToOriginMin,

                @JsonProperty("bike_min")
                Integer bikeMin,

                @JsonProperty("walk_to_destination_min")
                Integer walkToDestinationMin,

                @JsonProperty("total_eta_min")
                Integer totalEtaMin,

                @JsonProperty("score")
                Double score,

                @JsonProperty("score_breakdown")
                Map<String, Double> scoreBreakdown,

                @JsonProperty("reason")
                String reason,

                @JsonProperty("origin_latitude")
                Double originLatitude,

                @JsonProperty("origin_longitude")
                Double originLongitude,

                @JsonProperty("destination_latitude")
                Double destinationLatitude,

                @JsonProperty("destination_longitude")
                Double destinationLongitude,

                @JsonProperty("origin_bikes_now")
                Integer originBikesNow,

                @JsonProperty("origin_bikes_expected")
                Double originBikesExpected,

                @JsonProperty("destination_docks_now")
                Integer destinationDocksNow,

                @JsonProperty("destination_docks_expected")
                Double destinationDocksExpected,

                @JsonProperty("walk_to_origin_m")
                Double walkToOriginM,

                @JsonProperty("walk_to_destination_m")
                Double walkToDestinationM,

                @JsonProperty("origin_eta_min")
                Integer originEtaMin,

                @JsonProperty("destination_eta_min")
                Integer destinationEtaMin,

                @JsonProperty("origin_prediction_source")
                String originPredictionSource,

                @JsonProperty("destination_prediction_source")
                String destinationPredictionSource,

                @JsonProperty("origin_inventory_collected_at")
                Instant originInventoryCollectedAt,

                @JsonProperty("destination_inventory_collected_at")
                Instant destinationInventoryCollectedAt,

                @JsonProperty("origin_overflow_bikes")
                Integer originOverflowBikes,

                @JsonProperty("destination_overflow_bikes")
                Integer destinationOverflowBikes
        ) {}
}
