package com.example.ddareungi.api.search;

import com.example.ddareungi.api.search.dto.PlaceSearchResult;
import com.example.ddareungi.kakao.KakaoLocalService;
import com.example.ddareungi.kakao.dto.KakaoPlace;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import com.example.ddareungi.api.search.dto.AddressSearchResult;
import com.example.ddareungi.kakao.dto.KakaoAddress;

import java.util.List;

@RestController
@RequestMapping("/api/v1/search")
public class PlaceSearchController {

    private final KakaoLocalService kakaoLocalService;

    public PlaceSearchController(KakaoLocalService kakaoLocalService) {
        this.kakaoLocalService = kakaoLocalService;
    }

    @GetMapping("/places")
    public List<PlaceSearchResult> searchPlaces(
            @RequestParam String query
    ) {
        List<KakaoPlace> places = kakaoLocalService.searchPlaces(query);

        return places.stream()
                .map(place -> new PlaceSearchResult(
                        place.getPlaceName(),
                        place.getAddressName(),
                        place.getRoadAddressName(),
                        Double.parseDouble(place.getY()), // latitude
                        Double.parseDouble(place.getX())  // longitude
                ))
                .toList();
    }

    @GetMapping("/addresses")
    public List<AddressSearchResult> searchAddresses(
            @RequestParam String query
    ) {
        List<KakaoAddress> addresses =
                kakaoLocalService.searchAddresses(query);

        return addresses.stream()
                .map(address -> new AddressSearchResult(
                        address.getAddressName(),
                        address.getRoadAddress() != null
                                ? address.getRoadAddress().getAddressName()
                                : null,
                        Double.parseDouble(address.getY()),
                        Double.parseDouble(address.getX())
                ))
                .toList();
    }
}
