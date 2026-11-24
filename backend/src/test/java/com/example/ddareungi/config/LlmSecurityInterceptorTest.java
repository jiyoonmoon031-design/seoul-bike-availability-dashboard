package com.example.ddareungi.config;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import static org.assertj.core.api.Assertions.assertThat;

class LlmSecurityInterceptorTest {

    private static final Clock CLOCK = Clock.fixed(
            Instant.parse("2026-11-25T00:00:00Z"),
            ZoneOffset.UTC
    );

    @Test
    void rejectsMissingTokenWhenAuthenticationIsRequired() throws Exception {
        LlmSecurityInterceptor interceptor =
                new LlmSecurityInterceptor(true, "secret", 20, 1024, CLOCK);
        MockHttpServletResponse response = new MockHttpServletResponse();

        boolean allowed = interceptor.preHandle(
                new MockHttpServletRequest(), response, new Object()
        );

        assertThat(allowed).isFalse();
        assertThat(response.getStatus()).isEqualTo(401);
        assertThat(response.getContentAsString()).doesNotContain("secret");
    }

    @Test
    void acceptsValidToken() throws Exception {
        LlmSecurityInterceptor interceptor =
                new LlmSecurityInterceptor(true, "secret", 20, 1024, CLOCK);
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("X-LLM-Token", "secret");

        assertThat(interceptor.preHandle(
                request, new MockHttpServletResponse(), new Object()
        )).isTrue();
    }

    @Test
    void rejectsOversizedRequestBeforeAuthentication() throws Exception {
        LlmSecurityInterceptor interceptor =
                new LlmSecurityInterceptor(false, "", 20, 10, CLOCK);
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setContent(new byte[11]);
        MockHttpServletResponse response = new MockHttpServletResponse();

        assertThat(interceptor.preHandle(request, response, new Object())).isFalse();
        assertThat(response.getStatus()).isEqualTo(413);
    }

    @Test
    void rateLimitsRepeatedRequestsPerClient() throws Exception {
        LlmSecurityInterceptor interceptor =
                new LlmSecurityInterceptor(false, "", 2, 1024, CLOCK);
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRemoteAddr("203.0.113.10");

        assertThat(interceptor.preHandle(
                request, new MockHttpServletResponse(), new Object()
        )).isTrue();
        assertThat(interceptor.preHandle(
                request, new MockHttpServletResponse(), new Object()
        )).isTrue();

        MockHttpServletResponse response = new MockHttpServletResponse();
        assertThat(interceptor.preHandle(request, response, new Object())).isFalse();
        assertThat(response.getStatus()).isEqualTo(429);
        assertThat(response.getHeader("Retry-After")).isEqualTo("60");
    }
}
