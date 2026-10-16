package com.example.ddareungi.api.search.dto;

public class PlaceSearchResult {

    private String placeName;
    private String address;
    private String roadAddress;
    private Double latitude;
    private Double longitude;

    public PlaceSearchResult(
            String placeName,
            String address,
            String roadAddress,
            Double latitude,
            Double longitude
    ) {
        this.placeName = placeName;
        this.address = address;
        this.roadAddress = roadAddress;
        this.latitude = latitude;
        this.longitude = longitude;
    }

    public String getPlaceName() {
        return placeName;
    }

    public String getAddress() {
        return address;
    }

    public String getRoadAddress() {
        return roadAddress;
    }

    public Double getLatitude() {
        return latitude;
    }

    public Double getLongitude() {
        return longitude;
    }
}
