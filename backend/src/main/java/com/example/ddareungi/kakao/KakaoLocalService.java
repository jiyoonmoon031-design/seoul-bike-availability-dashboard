package com.example.ddareungi.kakao;

import com.example.ddareungi.kakao.dto.KakaoPlace;
import com.example.ddareungi.kakao.dto.KakaoPlaceSearchResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import com.example.ddareungi.kakao.dto.KakaoAddress;
import com.example.ddareungi.kakao.dto.KakaoAddressSearchResponse;

import java.util.List;

@Service
public class KakaoLocalService {

    private final RestClient restClient;

    public KakaoLocalService(
            @Value("${kakao.api.key}") String apiKey
    ) {
        this.restClient = RestClient.builder()
                .baseUrl("https://dapi.kakao.com")
                .defaultHeader("Authorization", "KakaoAK " + apiKey)
                .build();
    }

    public List<KakaoPlace> searchPlaces(String query) {

        KakaoPlaceSearchResponse response = restClient.get()
                .uri(uriBuilder -> uriBuilder
                        .path("/v2/local/search/keyword.json")
                        .queryParam("query", query)
                        .build())
                .retrieve()
                .body(KakaoPlaceSearchResponse.class);

        if (response == null || response.getDocuments() == null) {
            return List.of();
        }

        return response.getDocuments();
    }

    public List<KakaoAddress> searchAddresses(String query) {

        KakaoAddressSearchResponse response = restClient.get()
                .uri(uriBuilder -> uriBuilder
                        .path("/v2/local/search/address.json")
                        .queryParam("query", query)
                        .build())
                .retrieve()
                .body(KakaoAddressSearchResponse.class);

        if (response == null || response.getDocuments() == null) {
            return List.of();
        }

        return response.getDocuments();
    }

}