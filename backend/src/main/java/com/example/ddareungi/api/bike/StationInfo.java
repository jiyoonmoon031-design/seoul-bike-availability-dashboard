package com.example.ddareungi.api.bike;

public class StationInfo {
    private String STA_LOC;
    private String RENT_ID;
    private String RENT_NO;
    private String RENT_NM;
    private String STA_LAT;
    private String STA_LONG;
    private String STA_ADD1;

    public String getSTA_LOC(){
        return STA_LOC;
    }
    public void setSTA_LOC(String STA_LOC){
        this.STA_LOC=STA_LOC;
    }

    public String getRENT_ID(){
        return RENT_ID;
    }
    public void setRENT_ID(String RENT_ID){
        this.RENT_ID=RENT_ID;
    }

    public String getRENT_NO(){
        return RENT_NO;
    }
    public void setRENT_NO(String RENT_NO){
        this.RENT_NO=RENT_NO;
    }

    public String getRENT_NM(){
        return RENT_NM;
    }
    public void setRENT_NM(String RENT_NM){
        this.RENT_NM=RENT_NM;
    }

    public String getSTA_LAT(){
        return STA_LAT;
    }
    public void setSTA_LAT(String STA_LAT){
        this.STA_LAT=STA_LAT;
    }

    public String getSTA_LONG(){
        return STA_LONG;
    }
    public void setSTA_LONG(String STA_LONG){
        this.STA_LONG=STA_LONG;
    }

    public String getSTA_ADD1(){
        return STA_ADD1;
    }
    public void setSTA_ADD1(String STA_ADD1){
        this.STA_ADD1=STA_ADD1;
    }
}
