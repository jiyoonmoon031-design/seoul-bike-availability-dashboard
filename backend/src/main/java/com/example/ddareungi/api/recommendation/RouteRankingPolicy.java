package com.example.ddareungi.api.recommendation;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class RouteRankingPolicy {

    private final double originWeight;
    private final double destinationWeight;
    private final double etaWeight;
    private final double walkingWeight;
    private final double maxEtaMin;
    private final double maxWalkingMin;

    public RouteRankingPolicy(
            @Value("${recommendation.route.weight.origin:0.35}")
            double originWeight,
            @Value("${recommendation.route.weight.destination:0.35}")
            double destinationWeight,
            @Value("${recommendation.route.weight.eta:0.15}")
            double etaWeight,
            @Value("${recommendation.route.weight.walking:0.15}")
            double walkingWeight,
            @Value("${recommendation.route.max-eta-min:90}")
            double maxEtaMin,
            @Value("${recommendation.route.max-walking-min:20}")
            double maxWalkingMin
    ) {
        double totalWeight = originWeight
                + destinationWeight
                + etaWeight
                + walkingWeight;

        if (originWeight < 0
                || destinationWeight < 0
                || etaWeight < 0
                || walkingWeight < 0
                || totalWeight <= 0) {
            throw new IllegalArgumentException(
                    "route recommendation weights must be non-negative and sum to > 0"
            );
        }
        if (maxEtaMin <= 0 || maxWalkingMin <= 0) {
            throw new IllegalArgumentException(
                    "route recommendation limits must be > 0"
            );
        }

        this.originWeight = originWeight / totalWeight;
        this.destinationWeight = destinationWeight / totalWeight;
        this.etaWeight = etaWeight / totalWeight;
        this.walkingWeight = walkingWeight / totalWeight;
        this.maxEtaMin = maxEtaMin;
        this.maxWalkingMin = maxWalkingMin;
    }

    public RouteScore calculate(
            double originStationScore,
            double destinationStationScore,
            int totalEtaMin,
            int walkToOriginMin,
            int walkToDestinationMin
    ) {
        double originComponent = originWeight * clamp01(originStationScore);
        double destinationComponent =
                destinationWeight * clamp01(destinationStationScore);
        double etaComponent = etaWeight * inverseScore(totalEtaMin, maxEtaMin);
        double walkingComponent = walkingWeight * inverseScore(
                walkToOriginMin + walkToDestinationMin,
                maxWalkingMin
        );
        double total = originComponent
                + destinationComponent
                + etaComponent
                + walkingComponent;

        return new RouteScore(
                round(total),
                round(originComponent),
                round(destinationComponent),
                round(etaComponent),
                round(walkingComponent)
        );
    }

    public String reason(RouteScore score, int totalEtaMin) {
        return "출발 자전거와 도착 빈 거치대의 미래 가용성, 양쪽 도보시간, "
                + "총 " + totalEtaMin + "분 이동을 함께 고려한 경로입니다.";
    }

    private double inverseScore(double value, double maximum) {
        return 1.0 - Math.min(Math.max(value, 0.0) / maximum, 1.0);
    }

    private double clamp01(double value) {
        return Math.min(Math.max(value, 0.0), 1.0);
    }

    private double round(double value) {
        return Math.round(value * 1_000_000.0) / 1_000_000.0;
    }

    public record RouteScore(
            double total,
            double originStation,
            double destinationStation,
            double eta,
            double walking
    ) {}
}
