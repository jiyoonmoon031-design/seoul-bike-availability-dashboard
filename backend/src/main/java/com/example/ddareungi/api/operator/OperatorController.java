package com.example.ddareungi.api.operator;

import com.example.ddareungi.api.operator.dto.OperatorRiskResponse;
import com.example.ddareungi.api.operator.dto.RebalancingResponse;

import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.OffsetDateTime;

@RestController
@RequestMapping("/api/v1/operator")
public class OperatorController {

    private final OperatorService operatorService;

    public OperatorController(OperatorService operatorService) {
        this.operatorService = operatorService;
    }

    @GetMapping("/risk")
    public OperatorRiskResponse getRisk(
            @RequestParam("basetime")
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME)
            OffsetDateTime baseTime,

            @RequestParam("horizon")
            int horizon,

            @RequestParam(value = "topn", defaultValue = "10")
            int topn
    ) {
        return operatorService.getRisk(baseTime, horizon, topn);
    }

    @GetMapping("/rebalancing")
    public RebalancingResponse getRebalancing(
            @RequestParam("basetime")
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME)
            OffsetDateTime baseTime,

            @RequestParam("horizon")
            int horizon,

            @RequestParam(value = "topn", defaultValue = "10")
            int topn
    ) {
        return operatorService.getRebalancing(
                baseTime, horizon, topn
        );
    }

    @GetMapping("/briefing")
    public String getBriefing(
            @RequestParam("basetime")
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME)
            OffsetDateTime baseTime,

            @RequestParam("horizon")
            int horizon,

            @RequestParam(value = "topn", defaultValue = "10")
            int topn
    ) {
        return operatorService.getOperatorBriefing(
                baseTime, horizon, topn
        );
    }

}
