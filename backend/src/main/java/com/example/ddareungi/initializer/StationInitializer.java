package com.example.ddareungi.initializer;

import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.ApplicationArguments;
import org.springframework.context.annotation.Profile;

import com.example.ddareungi.domain.station.StationRepository;
import com.example.ddareungi.api.bike.BikeApiService;

@Component
@Profile("!test")
public class StationInitializer implements ApplicationRunner{
    private final StationRepository stationRepository;
    private final BikeApiService bikeApiService;

    public StationInitializer(
            StationRepository stationRepository,
            BikeApiService bikeApiService){
        this.stationRepository=stationRepository;
        this.bikeApiService=bikeApiService;
    }

    @Override
    public void run(ApplicationArguments args){
        if(stationRepository.count()==0){
            bikeApiService.saveTargetStations();
        }
    }

}


