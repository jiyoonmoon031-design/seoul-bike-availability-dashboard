package com.example.ddareungi.scheduler;
import com.example.ddareungi.collector.BikeApiService;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class StationScheduler {
    private final BikeApiService bikeApiService;
    public StationScheduler(BikeApiService bikeApiService){
        this.bikeApiService=bikeApiService;
    }

    @Scheduled(
            cron="${station.cron}",
            zone="Asia/Seoul"
    )
    public void updateStation(){
        bikeApiService.saveTargetStations();
    }
}
