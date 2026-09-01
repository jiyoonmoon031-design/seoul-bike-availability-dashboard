package com.example.ddareungi.scheduler;

import com.example.ddareungi.api.bike.BikeApiService;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import com.example.ddareungi.domain.station.StationRepository;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Component
public class BikeSnapshotScheduler {

    private static final Logger log =
            LoggerFactory.getLogger(BikeSnapshotScheduler.class);

    private final BikeApiService bikeApiService;
    private final StationRepository stationRepository;

    public BikeSnapshotScheduler(
            BikeApiService bikeApiService,
            StationRepository stationRepository
            ){
        this.bikeApiService = bikeApiService;
        this.stationRepository = stationRepository;
    }

    @Scheduled(
            cron = "${snapshot.cron}",
            zone = "Asia/Seoul"
    )
    public void collectBikeSnapshot(){

        if(stationRepository.count()==0){
            try{
                bikeApiService.saveTargetStations();
            } catch(Exception e){
                log.error("대여소 초기화중 문제 발생",e);
                return;
            }
        }

        log.info("따릉이 스냅샷 수집 시작");
        try{
            bikeApiService.getTargetBikeData();
            log.info("따릉이 스냅샷 수집 종료");
        } catch(Exception e){
            log.error("따릉이 스냅샷 수집 작업 실패",e);

        }
    }

}
