package com.example.ddareungi.kakao.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public class KakaoAddress {

    @JsonProperty("address_name")
    private String addressName;

    @JsonProperty("road_address")
    private KakaoRoadAddress roadAddress;

    private String x;
    private String y;

    public String getAddressName() {
        return addressName;
    }

    public KakaoRoadAddress getRoadAddress() {
        return roadAddress;
    }

    public String getX() {
        return x;
    }

    public String getY() {
        return y;
    }
}