CONTENT_TYPES: dict[int, dict[str, str]] = {
    12: {"code": "tourist_attraction", "name": "관광지"},
    14: {"code": "cultural_facility", "name": "문화시설"},
    15: {"code": "festival_event", "name": "축제공연행사"},
    25: {"code": "travel_course", "name": "여행코스"},
    28: {"code": "leports", "name": "레포츠"},
    32: {"code": "accommodation", "name": "숙박"},
    38: {"code": "shopping", "name": "쇼핑"},
}

POST_STATUS_TAGS_BY_CATEGORY = {
    "현장 제보": ("혼잡", "여유", "공사"),
    "방문 후기": ("이용 주의", "사진 추천", "가족 추천", "혼자 추천"),
}
POST_CATEGORIES = tuple(POST_STATUS_TAGS_BY_CATEGORY)
POST_STATUS_TAGS = tuple(
    status_tag
    for status_tags in POST_STATUS_TAGS_BY_CATEGORY.values()
    for status_tag in status_tags
)


def is_valid_post_category_status(category: str, status_tag: str | None) -> bool:
    return status_tag is None or status_tag in POST_STATUS_TAGS_BY_CATEGORY.get(category, ())

AVAILABLE_MINUTES = (30, 60, 120, 240)
COMPANIONS = ("solo", "couple", "friends", "family")
MOODS = ("healing", "culture", "activity", "night_view", "shopping")

