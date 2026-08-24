package com.example.ddareungi.scheduler;

import com.example.ddareungi.api.bike.BikeApiService;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Component
public class BikeSnapshotScheduler {

    private static final Logger log =
            LoggerFactory.getLogger(BikeSnapshotScheduler.class);

    private final BikeApiService bikeApiService;

    public BikeSnapshotScheduler(BikeApiService bikeApiService){
        this.bikeApiService = bikeApiService;
    }

    @Scheduled(
            cron = "${snapshot.cron}",
            zone = "Asia/Seoul"
    )

    public void collectBikeSnapshot(){

        log.info("따릉이 스냅샷 수집 시작");
        try{
            bikeApiService.getTargetBikeData();
            log.info("따릉이 스냅샷 수집 종료");
        } catch(Exception e){
            log.error("따릉이 스냅샷 수집 작업 실패",e);

        }
    }
}
