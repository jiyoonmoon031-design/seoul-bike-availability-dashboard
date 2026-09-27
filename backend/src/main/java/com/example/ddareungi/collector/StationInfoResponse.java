package com.example.ddareungi.collector;

import com.fasterxml.jackson.annotation.JsonProperty;
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
        @JsonProperty("list_total_count")
        private String listTotalCount;

        private List<StationInfo> row;

        public String getListTotalCount(){
            return listTotalCount;
        }

        public void setListTotalCount(String listTotalCount) {
            this.listTotalCount = listTotalCount;
        }

        public List<StationInfo> getRow(){
            return row;
        }
    }
}
