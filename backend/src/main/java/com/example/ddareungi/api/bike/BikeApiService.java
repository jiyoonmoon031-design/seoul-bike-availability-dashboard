package com.example.ddareungi.api.bike;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.util.Set;
import java.util.HashSet;
import java.time.Instant;
import java.util.List;
import java.util.ArrayList;
import java.util.Map;
import java.util.HashMap;

import com.example.ddareungi.domain.snapshot.StationSnapshotRepository;
import com.example.ddareungi.domain.snapshot.StationSnapshot;

import com.example.ddareungi.domain.station.Station;
import com.example.ddareungi.domain.station.StationRepository;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;


@Service
public class BikeApiService {

    private final RestClient restClient;
    private final StationSnapshotRepository stationSnapshotRepository;
    private final StationRepository stationRepository;
    private final String apiKey;
    private static final Logger log =
            LoggerFactory.getLogger(BikeApiService.class);

    public BikeApiService(
            StationSnapshotRepository stationSnapshotRepository,
            StationRepository stationRepository,
            @Value("${seoul.api.key}") String apiKey,
            RestClient restClient
    ) {
        this.stationSnapshotRepository = stationSnapshotRepository;
        this.stationRepository = stationRepository;
        this.apiKey = apiKey;
        this.restClient = restClient;
    }


    public void getTargetBikeData() {

        Set<String> targetStationIds = getTargetStationIdsFromDb();

        if(targetStationIds.isEmpty()){
            throw new IllegalStateException("대상 대여소 정보가 없습니다");
        }

        Instant collectedAt = Instant.now();

        String url="http://openapi.seoul.go.kr:8088/"+ apiKey+ "/json/bikeList/";

        List<StationSnapshot> snapshotList = new ArrayList<>();

        int start=1;
        int pageSize=1000;

        while(true){
            int end=start+pageSize-1;
            String urlPage = url + start + "/" + end + "/";

            BikeApiResponse response = fetchBikePage(urlPage, start, end);

            var stations = response.getRentBikeStatus().getRow();
            log.info(
                    "따릉이 API 호출 성공. 조회 범위: {} ~ {}, 응답 건수: {}",
                    start,
                    end,
                    stations.size()
            );

            for (BikeStation station : stations){
                if(targetStationIds.contains(station.getStationId())){
                    StationSnapshot snapshot = new StationSnapshot(
                            station.getStationId(),
                            collectedAt,
                            Integer.parseInt(station.getParkingBikeTotCnt()),
                            Integer.parseInt(station.getRackTotCnt())
                    );

                    snapshotList.add(snapshot);
                }

            }
            if(stations.size()<pageSize){
                break;
            }
            start+=pageSize;
        }
        if (snapshotList.isEmpty()){
            throw new IllegalStateException("수집된 대여소 데이터가 없습니다");
        }
        stationSnapshotRepository.saveAll(snapshotList);
        log.info("스냅샷 저장 완료. 수집 시각: {}, 저장 건수: {}", collectedAt, snapshotList.size());
    }

    private BikeApiResponse fetchBikePage(String urlPage, int start, int end){
        for(int attempts = 1; attempts <=3; attempts++) {
            try {
                BikeApiResponse response = restClient.get()
                        .uri(urlPage)
                        .retrieve()
                        .body(BikeApiResponse.class);
                if(response == null
                        || response.getRentBikeStatus()==null
                        || response.getRentBikeStatus().getRow() == null
                ){
                    throw new IllegalStateException(
                            "따릉이 API 응답 데이터 없음. 조회 범위: "
                                    +start+"~"+end
                    );
                }
                return response;
            } catch (Exception e) {
                if(attempts==3){
                    throw new IllegalStateException(
                            "따릉이 API 호출 3회 모두 실패. 조회 범위: "
                            +start+"~"+end,
                            e
                    );
                }
                log.warn(
                        "따릉이 API 호출 실패. 2초 후 재시도합니다. 현재 시도: {}/3",
                        attempts,
                        e
                );
                try {
                    Thread.sleep(2000);
                } catch(InterruptedException ie){
                    Thread.currentThread().interrupt();
                    throw new IllegalStateException(
                            "재시도 대기 중 인터럽트 발생",
                            ie
                    );
                }
            }
        }
        throw new IllegalStateException("따릉이 API 재시도 실패");
    }

    private Set<String> getTargetStationIdsFromDb() {

        Set<String> targetStationIds = new HashSet<>();

        for (Station station : stationRepository.findAll()) {
            targetStationIds.add(station.getStationId());
        }

        return targetStationIds;
    }

    public void saveTargetStations() {
        Map<String, Integer> capacityMap = getStationCapacityMap();

        String url= "http://openapi.seoul.go.kr:8088/"+ apiKey+ "/json/tbCycleStationInfo/";

        String listTotalCountUrl=url+"1/1/";
        StationInfoResponse countResponse=restClient.get()
                .uri(listTotalCountUrl)
                .retrieve()
                .body(StationInfoResponse.class);

        if(countResponse==null
                || countResponse.getStationInfo()==null
                || countResponse.getStationInfo().getListTotalCount()==null
                || countResponse.getStationInfo().getListTotalCount().isBlank()){
          throw new IllegalStateException(
                "대여소 기본정보 API 응답 없음"
          );
        }

        int totalCount=Integer.parseInt(countResponse.getStationInfo().getListTotalCount());

        List<Station> stationList = new ArrayList<>();

        for (int start = 1; start <= totalCount; start += 1000) {

            int end = Math.min(start + 999, totalCount);

            String urlPage = url
                    + start
                    + "/"
                    + end
                    + "/";

            StationInfoResponse response = restClient.get()
                    .uri(urlPage)
                    .retrieve()
                    .body(StationInfoResponse.class);

            if (response == null
                    || response.getStationInfo() == null
                    || response.getStationInfo().getRow() == null) {
                throw new IllegalStateException("대여소 기본정보 API 응답 없음");
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
                            stationInfo.getSTA_ADD1(),
                            capacityMap.get(stationInfo.getRENT_ID())

                    );

                    stationList.add(station);
                }
            }
        }

        if(stationList.isEmpty()){
            throw new IllegalStateException("수집된 대상 대여소 정보가 없습니다");
        }
        stationRepository.saveAll(stationList);
        System.out.println("광진·성동 대여소 기본정보 저장 완료");
    }

    private Map<String, Integer> getStationCapacityMap(){
        Map<String, Integer> capacityMap = new HashMap<>();

        String url="http://openapi.seoul.go.kr:8088/"+ apiKey+ "/json/bikeList/";

        int start = 1;
        int pageSize = 1000;

        while (true){
            int end = start + pageSize -1;
            String urlPage = url + start + "/" + end + "/";

            BikeApiResponse response = restClient.get()
                    .uri(urlPage)
                    .retrieve()
                    .body(BikeApiResponse.class);

            if(response==null
                    ||response.getRentBikeStatus()==null
                    ||response.getRentBikeStatus().getRow()==null
            ){ throw new IllegalStateException(
                    "따릉이 API 응답 데이터 없음. 조회 범위: "
                            + start + "~" +end
                );
            }
            var stations = response.getRentBikeStatus().getRow();
            for(BikeStation station:stations){
                capacityMap.put(station.getStationId(), Integer.parseInt(station.getRackTotCnt()));

            }
            if(stations.size()<pageSize){
                break;
            }
            start+=pageSize;
        }


        return capacityMap;
    }
}
