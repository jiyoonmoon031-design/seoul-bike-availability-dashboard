package com.example.ddareungi.domain.snapshot;

import java.time.Instant;
import java.util.Objects;
import java.io.Serializable;

public class StationSnapshotId implements Serializable{

    private String stationId;
    private Instant collectedAt;
    public StationSnapshotId(){
    }
    public StationSnapshotId(String stationId, Instant collectedAt){
        this.stationId = stationId;
        this.collectedAt=collectedAt;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof StationSnapshotId that)) return false;
        return Objects.equals(stationId, that.stationId)
                && Objects.equals(collectedAt, that.collectedAt);
    }

    @Override
    public int hashCode(){
        return Objects.hash(stationId, collectedAt);
    }
}
