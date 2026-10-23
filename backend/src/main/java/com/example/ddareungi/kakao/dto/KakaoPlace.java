package com.example.ddareungi.kakao.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public class KakaoPlace {

    @JsonProperty("place_name")
    private String placeName;

    @JsonProperty("address_name")
    private String addressName;

    @JsonProperty("road_address_name")
    private String roadAddressName;

    // Kakao API: x = longitude(경도)
    private String x;

    // Kakao API: y = latitude(위도)
    private String y;

    public String getPlaceName() {
        return placeName;
    }

    public String getAddressName() {
        return addressName;
    }

    public String getRoadAddressName() {
        return roadAddressName;
    }

    public String getX() {
        return x;
    }

    public String getY() {
        return y;
    }
}
