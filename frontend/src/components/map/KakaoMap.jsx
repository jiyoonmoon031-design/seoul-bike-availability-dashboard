import { useEffect, useRef, useState } from "react";

const KAKAO_SCRIPT_ID = "kakao-map-sdk";

function loadKakaoMap() {
  if (window.kakao?.maps) {
    return Promise.resolve(window.kakao.maps);
  }

  return new Promise((resolve, reject) => {
    const existing = document.getElementById(KAKAO_SCRIPT_ID);
    const finish = () => window.kakao.maps.load(() => resolve(window.kakao.maps));

    if (existing) {
      existing.addEventListener("load", finish, { once: true });
      existing.addEventListener("error", reject, { once: true });
      return;
    }

    const key = import.meta.env.VITE_KAKAO_JAVASCRIPT_KEY;
    if (!key) {
      reject(new Error("Kakao Map JavaScript 키가 설정되지 않았습니다."));
      return;
    }

    const script = document.createElement("script");
    script.id = KAKAO_SCRIPT_ID;
    script.async = true;
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${key}&autoload=false`;
    script.addEventListener("load", finish, { once: true });
    script.addEventListener(
      "error",
      () => reject(new Error("Kakao Map을 불러오지 못했습니다.")),
      { once: true },
    );
    document.head.appendChild(script);
  });
}

function KakaoMap({ origin, destination, routes }) {
  const mapRef = useRef(null);
  const [mapError, setMapError] = useState("");

  useEffect(() => {
    let cancelled = false;

    loadKakaoMap()
      .then((maps) => {
        if (cancelled || !mapRef.current) {
          return;
        }

        mapRef.current.replaceChildren();
        const map = new maps.Map(mapRef.current, {
          center: new maps.LatLng(37.5506, 127.0743),
          level: 6,
        });
        const bounds = new maps.LatLngBounds();
        const points = [];

        if (origin) {
          points.push({ ...origin, markerLabel: "O", markerType: "origin" });
        }
        if (destination) {
          points.push({
            ...destination,
            markerLabel: "D",
            markerType: "destination",
          });
        }
        routes.forEach((route) => {
          points.push({
            latitude: route.origin_latitude,
            longitude: route.origin_longitude,
            name: `${route.rank}위 출발 · ${route.origin_station_name}`,
            markerLabel: `${route.rank}O`,
            markerType: "origin-station",
          });
          points.push({
            latitude: route.destination_latitude,
            longitude: route.destination_longitude,
            name: `${route.rank}위 도착 · ${route.destination_station_name}`,
            markerLabel: `${route.rank}D`,
            markerType: "destination-station",
          });
        });

        points.forEach((point) => {
          const position = new maps.LatLng(point.latitude, point.longitude);
          bounds.extend(position);

          const marker = document.createElement("button");
          marker.type = "button";
          marker.className = `map-marker ${point.markerType}`;
          marker.textContent = String(point.markerLabel);
          marker.title = point.name;
          marker.setAttribute("aria-label", point.name);

          new maps.CustomOverlay({
            map,
            position,
            content: marker,
            clickable: true,
            xAnchor: 0.5,
            yAnchor: 0.5,
          });
        });

        if (points.length > 0) {
          map.setBounds(bounds);
        }
        setMapError("");
      })
      .catch((error) => {
        if (!cancelled) {
          setMapError(
            error instanceof Error ? error.message : "지도를 불러오지 못했습니다.",
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [origin, destination, routes]);

  return (
    <div className="map-shell">
      <div ref={mapRef} className="map-canvas" />
      {mapError && (
        <div className="map-error" role="alert">
          {mapError}
        </div>
      )}
    </div>
  );
}

export default KakaoMap;
