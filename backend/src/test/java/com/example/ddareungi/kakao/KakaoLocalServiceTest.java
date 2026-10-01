package com.example.ddareungi.kakao;

import com.example.ddareungi.kakao.dto.KakaoPlace;
import org.junit.jupiter.api.Disabled;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertFalse;

@SpringBootTest
@Disabled("Requires real Kakao Local API key and external API access")
class KakaoLocalServiceTest {

    @Autowired
    private KakaoLocalService kakaoLocalService;

    @Test
    void searchPlaces() {

        List<KakaoPlace> places =
                kakaoLocalService.searchPlaces("세종대학교");

        assertFalse(places.isEmpty());

        for (KakaoPlace place : places) {
            System.out.println(
                    place.getPlaceName()
                            + " / "
                            + place.getAddressName()
                            + " / "
                            + place.getX()
                            + " / "
                            + place.getY()
            );
        }
    }
}