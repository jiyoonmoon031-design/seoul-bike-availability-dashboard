package com.example.ddareungi.api.bike;

import java.util.List;

public class StationInfoResponse {


    private StationInfoData stationInfo;

    public StationInfoData getStationInfo(){
        return stationInfo;
    }

    public void setStationInfo(StationInfoData stationInfo){
        this.stationInfo = stationInfo;
    }

    public static class StationInfoData{
        private String list_total_count;
        private List<StationInfo> row;

        public String getList_total_count(){
            return list_total_count;
        }

        public List<StationInfo> getRow(){
            return row;
        }
    }
}
