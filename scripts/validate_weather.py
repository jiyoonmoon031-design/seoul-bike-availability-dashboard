import pandas as pd

# 1. AWS 원본 데이터 불러오기
file_path = "D:/ddareungi_data/raw/weather/OBS_AWS_TIM_20260902035520.csv"

df = pd.read_csv(file_path, encoding="cp949")
df["일시"] = pd.to_datetime(df["일시"])


# 2. 학습 대상 기간 필터링
target_df = df[
    (df["일시"] >= "2025-08-01 00:00") & (df["일시"] < "2026-08-01 00:00")
].copy()


# 3. 기본 정보 확인
print("=== 기본 정보 ===")
print("데이터 크기:", target_df.shape)
print("관측소 번호:", target_df["지점"].unique())
print("관측소 이름:", target_df["지점명"].unique())


# 4. 결측치 확인
print("\n=== 결측치 ===")
print(target_df.isnull().sum())


# 5. timestamp 중복 확인
print("\n=== 시간 중복 ===")
print("중복 timestamp:", target_df["일시"].duplicated().sum())


# 6. 시간 간격 및 누락 확인
time_diff = target_df["일시"].diff()

invalid_time_diff = target_df[time_diff.notna() & (time_diff != pd.Timedelta(hours=1))]

print("\n=== 시간 간격 ===")
print(time_diff.value_counts())

print("\n=== 비정상 시간 간격 ===")
print(invalid_time_diff)


# 7. 강수량 연속 결측 구간 확인
missing_rain = target_df[target_df["강수량(mm)"].isnull()].copy()

missing_rain["time_diff"] = missing_rain["일시"].diff()
missing_rain["new_group"] = missing_rain["time_diff"] != pd.Timedelta(hours=1)
missing_rain["group"] = missing_rain["new_group"].cumsum()

rain_missing_summary = missing_rain.groupby("group")["일시"].agg(
    start="min", end="max", count="size"
)

print("\n=== 강수량 연속 결측 구간 ===")
print(rain_missing_summary)
