CONTENT_TYPES: dict[int, dict[str, str]] = {
    12: {"code": "tourist_attraction", "name": "관광지"},
    14: {"code": "cultural_facility", "name": "문화시설"},
    15: {"code": "festival_event", "name": "축제공연행사"},
    25: {"code": "travel_course", "name": "여행코스"},
    28: {"code": "leports", "name": "레포츠"},
    32: {"code": "accommodation", "name": "숙박"},
    38: {"code": "shopping", "name": "쇼핑"},
}

POST_CATEGORIES = ("현장 제보", "방문 후기", "질문", "추천")
POST_STATUS_TAGS = (
    "혼잡",
    "여유",
    "공사",
    "이용 주의",
    "사진 추천",
    "가족 추천",
    "혼자 추천",
)

AVAILABLE_MINUTES = (30, 60, 120, 240)
COMPANIONS = ("solo", "couple", "friends", "family")
MOODS = ("healing", "culture", "activity", "night_view", "shopping")

