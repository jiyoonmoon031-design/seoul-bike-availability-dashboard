import xml.etree.ElementTree as ET

import pandas as pd
import requests

# 한국천문연구원 특일 정보 API
# API Key는 코드에 직접 작성하지 않고 환경변수 등을 통해 관리한다.
api_key = ""

url = (
    "https://apis.data.go.kr/B090041/openapi/service/"
    "SpcdeInfoService/getRestDeInfo?serviceKey=" + api_key
)


# 공휴일 목록 수집
holidays = []

for year in ["2025", "2026"]:

    if year == "2025":
        months = ["08", "09", "10", "11", "12"]
    else:
        months = ["01", "02", "03", "04", "05", "06", "07"]

    for month in months:
        date_url = url + "&solYear=" + year + "&solMonth=" + month

        response = requests.get(date_url)
        root = ET.fromstring(response.text)

        items = root.findall(".//item")

        for item in items:
            holiday_date = item.find("locdate").text
            holiday_name = item.find("dateName").text

            holidays.append(holiday_date)


# 분석 기간의 전체 날짜 생성
dates = pd.date_range(
    start="2025-08-01",
    end="2026-07-31",
    freq="D",
)

calendar_df = pd.DataFrame({"date": dates})


# 요일 정보 생성
calendar_df["weekday"] = calendar_df["date"].dt.day_name()


# 주말 여부 생성
calendar_df["is_weekend"] = calendar_df["date"].dt.weekday >= 5


# 공휴일 여부 생성
calendar_df["is_holiday"] = calendar_df["date"].dt.strftime("%Y%m%d").isin(holidays)


# Calendar 데이터 저장
calendar_df.to_csv(
    "D:/ddareungi_data/processed/calendar/calendar_dim.csv",
    index=False,
    encoding="utf-8-sig",
)
