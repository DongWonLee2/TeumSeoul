from typing import Literal

from pydantic import ConfigDict, Field

from app.schemas.common import APIModel

AvailableMinutes = Literal[30, 60, 120, 240]
Companion = Literal["solo", "couple", "friends", "family"]
Mood = Literal["healing", "culture", "activity", "night_view", "shopping"]
SeoulDistrict = Literal[
    "강남구",
    "강동구",
    "강북구",
    "강서구",
    "관악구",
    "광진구",
    "구로구",
    "금천구",
    "노원구",
    "도봉구",
    "동대문구",
    "동작구",
    "마포구",
    "서대문구",
    "서초구",
    "성동구",
    "성북구",
    "송파구",
    "양천구",
    "영등포구",
    "용산구",
    "은평구",
    "종로구",
    "중구",
    "중랑구",
]


class CurrentLocation(APIModel):
    latitude: float = Field(ge=-90, le=90, description="현재 위치 위도", examples=[37.575])
    longitude: float = Field(ge=-180, le=180, description="현재 위치 경도", examples=[126.98])


class SituationalRecommendationRequest(APIModel):
    available_minutes: AvailableMinutes = Field(description="사용 가능한 시간(분)", examples=[120])
    companion: Companion = Field(description="동행 유형", examples=["friends"])
    mood: Mood = Field(description="원하는 분위기", examples=["culture"])
    district: SeoulDistrict | None = Field(
        default=None,
        description="희망 서울 자치구; 생략하면 서울 전체",
        examples=["종로구"],
    )
    current_location: CurrentLocation | None = Field(
        default=None,
        description="현재 위치; 생략하면 거리 점수를 적용하지 않음",
    )


class RepresentativeLocation(APIModel):
    latitude: float
    longitude: float


class RecommendedLocation(APIModel):
    id: int
    title: str
    content_type: str
    address: str | None
    image_url: str | None
    match_reasons: list[str]


class SituationalCourse(APIModel):
    id: str
    title: str
    reason: str
    representative_location: RepresentativeLocation
    estimated_place_count: int = Field(ge=1, le=4)
    locations: list[RecommendedLocation] = Field(min_length=1, max_length=4)
    warnings: list[str]


class AppliedConditions(APIModel):
    available_minutes: AvailableMinutes
    companion: Companion
    mood: Mood
    district: SeoulDistrict | None = None


class SituationalRecommendationData(APIModel):
    recommendations: list[SituationalCourse]
    applied_conditions: AppliedConditions


class SituationalRecommendationMeta(APIModel):
    count: int = Field(ge=0, le=3)
    fallback: bool
    warnings: list[str] = Field(default_factory=list)
    model: str


class SituationalRecommendationResponse(APIModel):
    data: SituationalRecommendationData
    meta: SituationalRecommendationMeta


class AICourse(APIModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=1, max_length=300)
    location_ids: list[int] = Field(min_length=1, max_length=4)


class AICourseSelection(APIModel):
    model_config = ConfigDict(extra="forbid")

    recommendations: list[AICourse] = Field(min_length=3, max_length=3)
