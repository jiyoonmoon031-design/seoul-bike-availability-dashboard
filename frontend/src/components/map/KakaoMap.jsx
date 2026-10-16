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
