import { useEffect, useRef } from "react";
import { getStationStatuses } from "../../api/stationApi";

function KakaoMap() {
  const mapRef = useRef(null);

  useEffect(() => {
    const script = document.createElement("script");

    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${import.meta.env.VITE_KAKAO_JAVASCRIPT_KEY}&autoload=false`;

    script.async = true;

    script.onload = () => {
      window.kakao.maps.load(async () => {
        const container = mapRef.current;

        const options = {
          center: new window.kakao.maps.LatLng(
            37.550638892935346,
            127.0742595815513,
          ),
          level: 5,
        };

        const map = new window.kakao.maps.Map(container, options);
        // 임시 경로 표시 테스트
        const testPath = [
          new window.kakao.maps.LatLng(37.53942623086569, 127.07479079682322),
          new window.kakao.maps.LatLng(37.53951232447078, 127.0743741656421),
          new window.kakao.maps.LatLng(37.539562316560996, 127.0742575081765),
          new window.kakao.maps.LatLng(37.53897627320167, 127.07423808214025),
          new window.kakao.maps.LatLng(37.53918456737776, 127.07340759627812),
          new window.kakao.maps.LatLng(37.539367867708975, 127.0727576502454),
          new window.kakao.maps.LatLng(37.53945951862464, 127.07247434010286),
          new window.kakao.maps.LatLng(37.539534505860196, 127.07224935845652),
          new window.kakao.maps.LatLng(37.53967892617131, 127.0718410581953),
          new window.kakao.maps.LatLng(37.53989555656308, 127.07122444151656),
          new window.kakao.maps.LatLng(37.53993999354347, 127.0710966741095),
          new window.kakao.maps.LatLng(37.53998165301884, 127.07096612925638),
          new window.kakao.maps.LatLng(37.54001220487401, 127.07095779581437),
          new window.kakao.maps.LatLng(37.54006775362431, 127.07093835156314),
          new window.kakao.maps.LatLng(37.5401038603395, 127.07092724043854),
          new window.kakao.maps.LatLng(37.54032883604545, 127.07103000247335),
          new window.kakao.maps.LatLng(37.54087044437256, 127.07128551938875),
          new window.kakao.maps.LatLng(37.540928771427765, 127.07131329298188),
          new window.kakao.maps.LatLng(37.5417897897306, 127.07171600964787),
          new window.kakao.maps.LatLng(37.54189254926592, 127.07136603859321),
          new window.kakao.maps.LatLng(37.542284173771854, 127.07155212164264),
          new window.kakao.maps.LatLng(37.5425702465374, 127.07126880598115),
          new window.kakao.maps.LatLng(37.54260635285246, 127.07123547465727),
          new window.kakao.maps.LatLng(37.542828545202795, 127.07101048883237),
          new window.kakao.maps.LatLng(37.54302851831304, 127.07080772383755),
          new window.kakao.maps.LatLng(37.543395135673336, 127.07043552509305),
          new window.kakao.maps.LatLng(37.54348123522838, 127.0703494193769),
          new window.kakao.maps.LatLng(37.54393395219344, 127.0698938924415),
        ];

        const testPolyline = new window.kakao.maps.Polyline({
          path: testPath,
          strokeWeight: 5,
          strokeOpacity: 0.8,
          strokeStyle: "solid",
        });

        testPolyline.setMap(map);

        try {
          const stations = await getStationStatuses();

          stations.forEach((station) => {
            if (station.latitude == null || station.longitude == null) {
              return;
            }

            const markerPosition = new window.kakao.maps.LatLng(
              station.latitude,
              station.longitude,
            );

            const marker = new window.kakao.maps.Marker({
              map: map,
              position: markerPosition,
            });

            const infoWindow = new window.kakao.maps.InfoWindow({
              content: `
                <div style="
                  padding: 10px;
                  min-width: 200px;
                  font-size: 13px;
                  line-height: 1.6;
                ">
                  <strong>${station.station_name}</strong><br />
                  ${station.district}<br />
                  대여 가능: ${station.bikes_now}대<br />
                  반납 가능: ${station.docks_now}대
                </div>
              `,
            });

            window.kakao.maps.event.addListener(marker, "click", () => {
              infoWindow.open(map, marker);
            });
          });
        } catch (error) {
          console.error("대여소 조회 오류:", error);
        }
      });
    };

    document.head.appendChild(script);

    return () => {
      document.head.removeChild(script);
    };
  }, []);

  return (
    <div
      ref={mapRef}
      style={{
        width: "100%",
        height: "500px",
      }}
    />
  );
}

export default KakaoMap;
