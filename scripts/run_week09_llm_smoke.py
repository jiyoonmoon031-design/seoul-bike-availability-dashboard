from src.llm.client import (
    generate_operator_briefing,
    generate_user_reasons,
)

operator = {
    "base_time": "2026-10-28T08:00:00+09:00",
    "horizon_min": 30,
    "shortage_top": [
        {
            "station_name": "건대입구역 2번출구",
            "bikes_expected": 2.0,
            "s_min": 4.0,
            "risk_time": "2026-10-28T08:30:00+09:00",
        }
    ],
    "move_matches": [
        {
            "from_station_name": "성수역 3번출구",
            "to_station_name": "건대입구역 2번출구",
            "move_qty": 2,
        }
    ],
}


user = {
    "leg": "origin",
    "eta_min": 8,
    "candidates": [
        {
            "rank": 1,
            "station_name": "세종대학교 정문",
            "distance_m": 420,
            "bikes_expected": 7.4,
            "docks_expected": 12.6,
        }
    ],
}


print("===== OPERATOR =====")

print(generate_operator_briefing(operator))

print()

print("===== USER =====")

print(generate_user_reasons(user))
