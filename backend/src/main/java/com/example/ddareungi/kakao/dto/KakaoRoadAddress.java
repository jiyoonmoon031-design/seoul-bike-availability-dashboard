package com.example.ddareungi.kakao.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public class KakaoRoadAddress {

    @JsonProperty("address_name")
    private String addressName;

    public String getAddressName() {
        return addressName;
    }
}
