package com.example.ddareungi.domain.snapshot;

import org.springframework.data.jpa.repository.JpaRepository;

public interface StationSnapshotRepository
        extends JpaRepository<StationSnapshot, StationSnapshotId>{
}