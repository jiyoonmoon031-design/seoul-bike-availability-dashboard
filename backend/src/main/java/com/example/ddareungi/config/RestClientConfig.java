package com.example.ddareungi.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;

import java.time.Duration;

import org.springframework.http.client.SimpleClientHttpRequestFactory;

@Configuration
public class RestClientConfig {
    @Bean
    public RestClient restClient(){
        SimpleClientHttpRequestFactory requestFactory =
                new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(5000);
        requestFactory.setReadTimeout(10000);

        return RestClient.builder()
                .requestFactory(requestFactory)
                .build();
    }
}
