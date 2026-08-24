package com.example.ddareungi.api.bike;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.util.Set;
import java.util.HashSet;
import java.time.Instant;

import com.example.ddareungi.domain.snapshot.StationSnapshotRepository;
import com.example.ddareungi.domain.snapshot.StationSnapshot;

import com.example.ddareungi.domain.station.Station;
import com.example.ddareungi.domain.station.StationRepository;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Service
public class BikeApiService {

    private final RestClient restClient = RestClient.create();
    private final StationSnapshotRepository stationSnapshotRepository;
    private final StationRepository stationRepository;
    private final String apiKey;
    private static final Logger log =
            LoggerFactory.getLogger(BikeApiService.class);

    public BikeApiService(
            StationSnapshotRepository stationSnapshotRepository,
            StationRepository stationRepository,
            @Value("${seoul.api.key}") String apiKey
    ) {
        this.stationSnapshotRepository = stationSnapshotRepository;
        this.stationRepository = stationRepository;
        this.apiKey = apiKey;
    }


    public void getTargetBikeData() {


        Set<String> targetStationIds = getTargetStationIdsFromDb();

        Instant collectedAt = Instant.now();

        int start = 1;
        int pageSize = 1000;
        int savedCount = 0;

        while (true) {

            int end = start + pageSize - 1;

            String url = "http://openapi.seoul.go.kr:8088/"
                    + apiKey
                    + "/json/bikeList/"
                    + start
                    + "/"
                    + end
                    + "/";
            try {
                BikeApiResponse response = restClient.get()
                        .uri(url)
                        .retrieve()
                        .body(BikeApiResponse.class);

                if (response == null
                        || response.getRentBikeStatus() == null
                        || response.getRentBikeStatus().getRow() == null) {

                    throw new IllegalStateException(
                            "따릉이 API 응답 데이터 없음. 조회 범위: "
                            +start+"~"+end
                    );
                }

                var stations = response.getRentBikeStatus().getRow();

                for (BikeStation station : stations) {

                    if (targetStationIds.contains(station.getStationId())) {

                        StationSnapshot snapshot = new StationSnapshot(
                                station.getStationId(),
                                collectedAt,
                                Integer.parseInt(station.getParkingBikeTotCnt()),
                                Integer.parseInt(station.getRackTotCnt())
                        );
                        stationSnapshotRepository.save(snapshot);
                        savedCount++;
                    }
                }

                log.info(
                        "따릉이 API 호출 성공. 조회 범위: {} ~ {}, 응답 건수: {}",
                        start,
                        end,
                        stations.size()
                );

                // 1000개보다 적게 왔다면 마지막 페이지
                if (stations.size() < pageSize) {
                    break;
                }

                start += pageSize;
            } catch (Exception e) {

                log.error(
                        "따릉이 API 호출 실패. 조회 범위: {} ~ {}",
                        start,
                        end,
                        e
                );
                throw e;
            }
        }
        log.info("스냅샷 저장 완료. 수집 시각: {}, 저장 건수: {}", collectedAt,savedCount);
    }

    private Set<String> getTargetStationIdsFromDb() {

        Set<String> targetStationIds = new HashSet<>();

        for (Station station : stationRepository.findAll()) {
            targetStationIds.add(station.getStationId());
        }

        return targetStationIds;
    }

    public void saveTargetStations() {

        int totalCount = 3241;

        for (int start = 1; start <= totalCount; start += 1000) {

            int end = Math.min(start + 999, totalCount);

            String url = "http://openapi.seoul.go.kr:8088/"
                    + apiKey
                    + "/json/tbCycleStationInfo/"
                    + start
                    + "/"
                    + end
                    + "/";

            StationInfoResponse response = restClient.get()
                    .uri(url)
                    .retrieve()
                    .body(StationInfoResponse.class);

            if (response == null
                    || response.getStationInfo() == null
                    || response.getStationInfo().getRow() == null) {
                continue;
            }

            for (StationInfo stationInfo : response.getStationInfo().getRow()) {

                if ("광진구".equals(stationInfo.getSTA_LOC())
                        || "성동구".equals(stationInfo.getSTA_LOC())) {

                    Station station = new Station(
                            stationInfo.getRENT_ID(),
                            stationInfo.getRENT_NM(),
                            stationInfo.getSTA_LOC(),
                            Double.parseDouble(stationInfo.getSTA_LAT()),
                            Double.parseDouble(stationInfo.getSTA_LONG()),
                            stationInfo.getSTA_ADD1()
                    );

                    stationRepository.save(station);
                }
            }
        }

        System.out.println("광진·성동 대여소 기본정보 저장 완료");
    }
}
