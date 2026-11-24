package com.example.ddareungi.ai;

import com.example.ddareungi.ai.dto.AiRebalancingRequest;
import com.example.ddareungi.api.operator.dto.RebalancingResponse;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;
import org.springframework.web.server.ResponseStatusException;

import java.net.SocketTimeoutException;
import java.util.concurrent.TimeoutException;

@Component
public class AiRebalancingClient {

    private final RestClient restClient;
    private final String rebalancingPath;

    public AiRebalancingClient(
            @Qualifier("aiRestClient") RestClient aiRestClient,
            @Value("${ai.server.rebalancing-path}") String rebalancingPath
    ) {
        this.restClient = aiRestClient;

        this.rebalancingPath = rebalancingPath;
    }

    public RebalancingResponse rebalance(
            AiRebalancingRequest request
    ) {
        try {
            RebalancingResponse response = restClient.post()
                    .uri(rebalancingPath)
                    .body(request)
                    .retrieve()
                    .body(RebalancingResponse.class);

            if (response == null) {
                throw new ResponseStatusException(
                        HttpStatus.BAD_GATEWAY,
                        "AI rebalancing server returned an empty response"
                );
            }

            return response;

        } catch (RestClientResponseException e) {
            // AI 서버가 HTTP 4xx 또는 5xx를 반환한 경우
            throw new ResponseStatusException(
                    HttpStatus.BAD_GATEWAY,
                    "AI rebalancing server returned an error",
                    e
            );

        } catch (RestClientException e) {
            // 연결 실패와 타임아웃을 구분
            Throwable cause = e;
            while (cause != null) {
                if (cause instanceof SocketTimeoutException
                        || cause instanceof TimeoutException) {
                    throw new ResponseStatusException(
                            HttpStatus.GATEWAY_TIMEOUT,
                            "AI rebalancing server timed out",
                            e
                    );
                }
                cause = cause.getCause();
            }

            throw new ResponseStatusException(
                    HttpStatus.SERVICE_UNAVAILABLE,
                    "AI rebalancing server is unavailable",
                    e
            );
        }
    }
}
