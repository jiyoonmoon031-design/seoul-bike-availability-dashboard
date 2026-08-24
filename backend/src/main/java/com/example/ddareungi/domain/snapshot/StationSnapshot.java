package com.example.ddareungi.domain.snapshot;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(
        name = "station_snapshot",
        indexes = {
                @Index(
                        name = "idx_snapshot_time",
                        columnList = "collected_at"
                )
        }
)
@IdClass(StationSnapshotId.class)
public class StationSnapshot {

    @Id
    @Column(name = "station_id", length = 20, nullable = false)
    private String stationId;

    @Id
    @Column(name = "collected_at", nullable = false)
    private Instant collectedAt;

    @Column(name = "bikes_available", nullable = false)
    private Integer bikesAvailable;

    @Column(name = "capacity")
    private Integer capacity;

    protected StationSnapshot() {
    }

    public StationSnapshot(
            String stationId,
            Instant collectedAt,
            Integer bikesAvailable,
            Integer capacity
    ) {
        this.stationId = stationId;
        this.collectedAt = collectedAt;
        this.bikesAvailable = bikesAvailable;
        this.capacity = capacity;
    }
}