package com.example.ddareungi.config;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Clock;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

@Component
public class LlmSecurityInterceptor implements HandlerInterceptor {

    private static final String TOKEN_HEADER = "X-LLM-Token";

    private final boolean authRequired;
    private final byte[] expectedToken;
    private final int requestsPerMinute;
    private final long maxRequestBytes;
    private final Clock clock;
    private final ConcurrentHashMap<String, Window> windows =
            new ConcurrentHashMap<>();

    @Autowired
    public LlmSecurityInterceptor(
            @Value("${llm.auth.required:false}") boolean authRequired,
            @Value("${llm.api.token:}") String apiToken,
            @Value("${llm.rate-limit.requests-per-minute:20}")
            int requestsPerMinute,
            @Value("${llm.max-request-bytes:65536}") long maxRequestBytes
    ) {
        this(
                authRequired,
                apiToken,
                requestsPerMinute,
                maxRequestBytes,
                Clock.systemUTC()
        );
    }

    LlmSecurityInterceptor(
            boolean authRequired,
            String apiToken,
            int requestsPerMinute,
            long maxRequestBytes,
            Clock clock
    ) {
        this.authRequired = authRequired;
        this.expectedToken = apiToken.getBytes(StandardCharsets.UTF_8);
        this.requestsPerMinute = Math.max(1, requestsPerMinute);
        this.maxRequestBytes = Math.max(1, maxRequestBytes);
        this.clock = clock;
    }

    @Override
    public boolean preHandle(
            HttpServletRequest request,
            HttpServletResponse response,
            Object handler
    ) throws Exception {
        long contentLength = request.getContentLengthLong();
        if (contentLength > maxRequestBytes) {
            reject(response, 413, "LLM request is too large");
            return false;
        }

        if (authRequired) {
            if (expectedToken.length == 0) {
                reject(response, 503, "LLM authentication is not configured");
                return false;
            }
            String supplied = request.getHeader(TOKEN_HEADER);
            byte[] suppliedBytes = supplied == null
                    ? new byte[0]
                    : supplied.getBytes(StandardCharsets.UTF_8);
            if (!MessageDigest.isEqual(expectedToken, suppliedBytes)) {
                reject(response, 401, "Unauthorized LLM request");
                return false;
            }
        }

        long minute = clock.instant().getEpochSecond() / 60;
        String client = request.getRemoteAddr();
        Window window = windows.compute(
                client == null ? "unknown" : client,
                (key, current) -> current == null || current.minute != minute
                        ? new Window(minute)
                        : current
        );
        if (window.count.incrementAndGet() > requestsPerMinute) {
            response.setHeader("Retry-After", "60");
            reject(response, 429, "LLM rate limit exceeded");
            return false;
        }
        return true;
    }

    private static void reject(
            HttpServletResponse response,
            int status,
            String message
    ) throws Exception {
        response.setStatus(status);
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.getWriter().write(
                "{\"error\":\"" + message + "\"}"
        );
    }

    private static final class Window {
        private final long minute;
        private final AtomicInteger count = new AtomicInteger();

        private Window(long minute) {
            this.minute = minute;
        }
    }
}
