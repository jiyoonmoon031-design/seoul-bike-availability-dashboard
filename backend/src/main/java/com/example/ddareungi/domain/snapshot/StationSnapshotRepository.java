package com.example.ddareungi.domain.snapshot;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;
import java.util.stream.Stream;

public interface StationSnapshotRepository
        extends JpaRepository<StationSnapshot, StationSnapshotId>{

    @Query("""
            SELECT s
            FROM StationSnapshot s
            ORDER BY s.collectedAt ASC, s.stationId ASC
            """)
    Stream<StationSnapshot> streamAll();

    @Query("""
            SELECT s
            FROM StationSnapshot s
            WHERE s.collectedAt = (
                SELECT MAX(s2.collectedAt)
                FROM StationSnapshot s2
                WHERE s2.stationId = s.stationId
            )
            ORDER BY s.stationId ASC
            """)
    List<StationSnapshot> findLatestSnapshots();
}
