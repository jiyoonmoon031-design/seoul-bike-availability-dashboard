package com.example.ddareungi.collector;

import java.util.List;

public class BikeApiResponse {

    private RentBikeStatus rentBikeStatus;

    public RentBikeStatus getRentBikeStatus(){
        return rentBikeStatus;
    }

    public static class RentBikeStatus{
        private int list_total_count;
        private Result RESULT;
        private List<BikeStation> row;

        public int getList_total_count(){
            return list_total_count;
        }

        public Result getRESULT(){
            return RESULT;
        }

        public List<BikeStation> getRow(){
            return row;
        }
    }
    public static class Result{
        private String CODE;
        private String MESSAGE;

        public String getCODE(){
            return CODE;
        }

        public String getMESSAGE(){
            return MESSAGE;
        }
    }
}
