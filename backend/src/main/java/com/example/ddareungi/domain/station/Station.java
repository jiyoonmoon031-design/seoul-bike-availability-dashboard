package com.example.ddareungi.domain.station;

import jakarta.persistence.*;

@Entity
@Table(name="station")
public class Station {
    @Id
    @Column(name = "station_id", length = 20, nullable = false)
    private String stationId;

    @Column(name = "station_name", nullable = false)
    private String stationName;

    @Column(name = "district", length=20, nullable = false)
    private String district;

    @Column(name = "latitude", nullable = false)
    private Double latitude;

    @Column(name = "longitude", nullable = false)
    private Double longitude;

    @Column(name = "address")
    private String address;

    @Column(name = "capacity")
    private Integer capacity;

    protected Station(){
    }

    public Station(
            String stationId,
            String stationName,
            String district,
            Double latitude,
            Double longitude,
            String address,
            Integer capacity
    ){
        this.stationId = stationId;
        this.stationName = stationName;
        this.district = district;
        this.latitude = latitude;
        this.longitude = longitude;
        this.address = address;
        this.capacity = capacity;
    }
    public String getStationId() {
        return stationId;
    }
    public Integer getCapacity(){
        return capacity;
    }
    public void setCapacity(Integer capacity){
        this.capacity = capacity;
    }
}
