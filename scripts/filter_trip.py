import zipfile

import pandas as pd

# 광진구·성동구 대상 대여소 목록
target_stations = pd.read_csv("D:/ddareungi_data/reference/target_stations.csv")

target_ids = set(target_stations["station_id"])

print("대상 대여소 수:", len(target_ids))


# 수집 대상 기간
date_list = [
    "202508",
    "202509",
    "202510",
    "202511",
    "202512",
    "202601",
    "202602",
    "202603",
    "202604",
    "202605",
    "202606",
    "202607",
]


for date in date_list:
    rent_list = []
    return_list = []

    zip_path = "D:/ddareungi_data/raw/trip/" + "tpss_bcycl_od_statnhm_" + date + ".zip"

    with zipfile.ZipFile(zip_path, "r") as zip_file:

        for file_name in sorted(zip_file.namelist()):

            # 원본 CSV 인코딩 확인
            try:
                with zip_file.open(file_name) as csv_file:
                    df = pd.read_csv(csv_file, encoding="cp949")

            except UnicodeDecodeError:
                with zip_file.open(file_name) as csv_file:
                    df = pd.read_csv(csv_file, encoding="utf-8")

            print(date, file_name)

            # 원천 데이터가 비어 있는 날짜 확인
            if len(df) == 0:
                print("빈 원천 데이터:", date, file_name)

            # 대여 데이터 필터링
            rent_mask = (df["집계_기준"] == "출발시간") & (
                df["시작_대여소_ID"].isin(target_ids)
            )

            rent_rows = df[rent_mask]

            # 반납 데이터 필터링
            return_mask = (df["집계_기준"] == "도착시간") & (
                df["종료_대여소_ID"].isin(target_ids)
            )

            return_rows = df[return_mask]

            rent_list.append(rent_rows)
            return_list.append(return_rows)

    # 월 단위로 합치기
    rent_month = pd.concat(rent_list, ignore_index=True)

    return_month = pd.concat(return_list, ignore_index=True)

    # 필터링 결과 저장
    #
    # rent_month.to_csv(
    #     "D:/ddareungi_data/interim/trip/rent_" + date + ".csv",
    #     index=False,
    #     encoding="utf-8-sig",
    # )
    #
    # return_month.to_csv(
    #     "D:/ddareungi_data/interim/trip/return_" + date + ".csv",
    #     index=False,
    #     encoding="utf-8-sig",
    # )


# 원천 데이터 미관측 구간
#
# 2026-05-16
# 2026-06-29
# 2026-06-30
# 2026-07-01
#
# 해당 날짜는 대여·반납 건수가 0인 것이 아니라
# 원천 데이터 자체가 존재하지 않는 미관측 구간으로 처리한다.
