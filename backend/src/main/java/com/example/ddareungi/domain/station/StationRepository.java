package com.example.ddareungi.domain.station;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Collection;
import java.util.List;

public interface StationRepository
        extends JpaRepository<Station, String> {

    List<Station> findByDistrictIn(Collection<String> districts);

}
