package com.example.ddareungi.initializer;

import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.ApplicationArguments;

import com.example.ddareungi.domain.station.StationRepository;
import com.example.ddareungi.collector.BikeApiService;
import org.springframework.web.client.RestClientException;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Component
@Profile("!test")
public class StationInitializer implements ApplicationRunner{
    private final StationRepository stationRepository;
    private final BikeApiService bikeApiService;

    private static final Logger log = LoggerFactory.getLogger(StationInitializer.class);

    public StationInitializer(
            StationRepository stationRepository,
            BikeApiService bikeApiService){
        this.stationRepository=stationRepository;
        this.bikeApiService=bikeApiService;
    }

    @Override
    public void run(ApplicationArguments args){
        log.info("Initializer 실행");
        if(stationRepository.count()==0){
            log.info("station이 0개라서 초기화 시작");

            try {
                bikeApiService.saveTargetStations();
            } catch(RestClientException | IllegalStateException e){
                log.error("대여소 초기화 중 문제 발생",e);
            }
        }
    }

}
