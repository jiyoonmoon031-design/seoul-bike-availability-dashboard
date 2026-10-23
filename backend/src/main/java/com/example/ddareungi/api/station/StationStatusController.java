package com.example.ddareungi.api.station;
import org.springframework.web.bind.annotation.CrossOrigin;
import com.example.ddareungi.api.station.dto.StationStatus;
import com.example.ddareungi.api.station.dto.StationStatusResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/stations")
@CrossOrigin(origins = "http://localhost:5173")
public class StationStatusController {
    private final StationStatusService stationStatusService;

    public StationStatusController(StationStatusService stationStatusService){
        this.stationStatusService = stationStatusService;
    }

    @GetMapping("/status")
    public StationStatusResponse getStationStatuses(){
        List<StationStatus> status = stationStatusService.getStationStatuses();

        return new StationStatusResponse(status);
    }
}
