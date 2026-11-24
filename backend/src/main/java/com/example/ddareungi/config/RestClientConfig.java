package com.example.ddareungi.config;

import java.net.URI;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

@Configuration
public class RestClientConfig {

    @Bean
    public RestClient.Builder restClientBuilder() {

        SimpleClientHttpRequestFactory requestFactory =
                new SimpleClientHttpRequestFactory();

        requestFactory.setConnectTimeout(5000);
        requestFactory.setReadTimeout(10000);

        return RestClient.builder()
                .requestFactory(requestFactory);
    }

    @Bean
    @Primary
    public RestClient restClient(RestClient.Builder builder) {
        return builder.build();
    }

    @Bean
    public RestClient aiRestClient(
            @Value("${ai.server.url}") String baseUrl,
            @Value("${ai.server.basic-user:}") String username,
            @Value("${ai.server.basic-password:}") String password,
            @Value("${ai.server.read-timeout-ms:60000}") int readTimeoutMs
    ) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(5000);
        requestFactory.setReadTimeout(readTimeoutMs);
        RestClient.Builder builder = RestClient.builder()
                .baseUrl(baseUrl)
                .requestFactory(requestFactory);

        if (!username.isEmpty() || !password.isEmpty()) {
            if (username.isEmpty() || password.isEmpty()
                    || !"https".equalsIgnoreCase(URI.create(baseUrl).getScheme())) {
                throw new IllegalArgumentException("AI server Basic Auth needs both credentials and HTTPS");
            }
            builder.defaultHeaders(headers -> headers.setBasicAuth(username, password));
        }
        return builder.build();
    }
}
