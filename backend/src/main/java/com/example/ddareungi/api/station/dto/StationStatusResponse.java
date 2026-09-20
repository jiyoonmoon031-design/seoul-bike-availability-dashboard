package com.example.ddareungi.api.station.dto;
import java.util.List;

public class StationStatusResponse {
    private List<StationStatus> stations;

    public StationStatusResponse(List<StationStatus> stations){
        this.stations = stations;
    }

    public List<StationStatus> getStations(){
        return stations;
    }
}
