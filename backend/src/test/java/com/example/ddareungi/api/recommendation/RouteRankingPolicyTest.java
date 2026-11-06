package com.example.ddareungi.api.recommendation;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class RouteRankingPolicyTest {

    private RouteRankingPolicy policy() {
        return new RouteRankingPolicy(
                0.35,
                0.35,
                0.15,
                0.15,
                90,
                20
        );
    }

    @Test
    void balancedAvailableRouteGetsMaximumScore() {
        RouteRankingPolicy.RouteScore score = policy().calculate(
                1.0,
                1.0,
                0,
                0,
                0
        );

        assertEquals(1.0, score.total(), 0.000001);
        assertEquals(0.35, score.originStation(), 0.000001);
        assertEquals(0.35, score.destinationStation(), 0.000001);
        assertEquals(0.15, score.eta(), 0.000001);
        assertEquals(0.15, score.walking(), 0.000001);
    }

    @Test
    void shorterAndLessWalkingRouteRanksHigherWhenAvailabilityMatches() {
        RouteRankingPolicy.RouteScore shortRoute = policy().calculate(
                0.8,
                0.8,
                30,
                3,
                3
        );
        RouteRankingPolicy.RouteScore longRoute = policy().calculate(
                0.8,
                0.8,
                80,
                9,
                9
        );

        assertTrue(shortRoute.total() > longRoute.total());
    }

    @Test
    void oneSidedAvailabilityCannotMatchBalancedRoute() {
        RouteRankingPolicy.RouteScore balanced = policy().calculate(
                0.8,
                0.8,
                45,
                5,
                5
        );
        RouteRankingPolicy.RouteScore destinationFailure = policy().calculate(
                1.0,
                0.0,
                45,
                5,
                5
        );

        assertTrue(balanced.total() > destinationFailure.total());
    }

    @Test
    void invalidWeightsAreRejected() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new RouteRankingPolicy(-1, 1, 0, 0, 90, 20)
        );
    }
}
