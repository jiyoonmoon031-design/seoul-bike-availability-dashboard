package com.example.ddareungi.api.station;

import com.example.ddareungi.domain.snapshot.StationSnapshotRepository;
import com.example.ddareungi.domain.station.StationRepository;
import org.springframework.stereotype.Service;

import com.example.ddareungi.domain.station.Station;
import com.example.ddareungi.domain.snapshot.StationSnapshot;
import com.example.ddareungi.api.station.dto.StationStatus;

import java.util.List;
import java.util.Map;
import java.util.HashMap;
import java.util.ArrayList;

@Service
public class StationStatusService {
    private final StationRepository stationRepository;
    private final StationSnapshotRepository stationSnapshotRepository;

    public StationStatusService(
            StationRepository stationRepository,
            StationSnapshotRepository stationSnapshotRepository
    ){
        this.stationRepository = stationRepository;
        this.stationSnapshotRepository = stationSnapshotRepository;
    }

    public List<StationStatus> getStationStatuses(){
        List<Station> stations = stationRepository.findAll();

        List<StationSnapshot> snapshots = stationSnapshotRepository.findLatestSnapshots();

        Map<String, StationSnapshot> snapshotMap = new HashMap<>();
        for(StationSnapshot snapshot : snapshots){
            snapshotMap.put(snapshot.getStationId(), snapshot);
        }

        List<StationStatus> stationStatuses = new ArrayList<>();

        for (Station station : stations){
            StationSnapshot snapshot = snapshotMap.get(station.getStationId());
            if(snapshot == null){
                continue;
            }
            Integer docksNow = null;
            Integer bikesNow = snapshot.getBikesAvailable();
            Integer capacity = snapshot.getCapacity();

            if (capacity != null && bikesNow != null) {
                docksNow = Math.max(capacity - bikesNow, 0);
            }

            StationStatus status = new StationStatus(
                    station.getStationId(),
                    station.getStationName(),
                    station.getDistrict(),
                    station.getLatitude(),
                    station.getLongitude(),
                    capacity,
                    bikesNow,
                    docksNow,
                    snapshot.getCollectedAt()
            );
            stationStatuses.add(status);
        }
        return stationStatuses;
    }

}
