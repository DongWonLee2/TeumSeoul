from typing import Literal, Self

from pydantic import ConfigDict, Field, model_validator

from app.schemas.common import APIModel

AvailableMinutes = Literal[30, 60, 120, 240]
RecommendationMode = Literal["nearby", "district"]
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
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "recommendation_mode": "nearby",
                    "available_minutes": 120,
                    "companion": "friends",
                    "mood": "culture",
                    "current_location": {"latitude": 37.575, "longitude": 126.98},
                },
                {
                    "recommendation_mode": "district",
                    "available_minutes": 240,
                    "companion": "friends",
                    "mood": "culture",
                    "district": "강남구",
                },
            ]
        },
    )

    recommendation_mode: RecommendationMode = Field(
        description="추천 범위 선택: 현재 위치 주변 또는 지정 자치구",
        examples=["nearby"],
    )
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
        description="nearby 모드에서 필수인 현재 위치",
    )

    @model_validator(mode="after")
    def validate_recommendation_mode_fields(self) -> Self:
        if self.recommendation_mode == "nearby":
            if self.current_location is None:
                raise ValueError("현재 위치 추천에는 current_location이 필요합니다.")
            if self.district is not None:
                raise ValueError("현재 위치 추천에는 district를 함께 입력할 수 없습니다.")
        elif self.district is None:
            raise ValueError("지역 지정 추천에는 district가 필요합니다.")
        elif self.current_location is not None:
            raise ValueError("지역 지정 추천에는 current_location을 함께 입력할 수 없습니다.")
        return self


class RepresentativeLocation(APIModel):
    latitude: float
    longitude: float


class RecommendedLocation(APIModel):
    id: int
    title: str
    content_type: str
    address: str | None
    image_url: str | None
    experience_type: str = Field(description="박물관·미술관, 산책·야외 등 내부 경험 유형")
    estimated_visit_minutes: int = Field(
        ge=15,
        le=120,
        description="경험 유형을 바탕으로 계산한 예상 체류시간(분)",
    )
    match_reasons: list[str]


class SituationalCourse(APIModel):
    id: str
    title: str
    reason: str
    representative_location: RepresentativeLocation
    estimated_place_count: int = Field(ge=1, le=4)
    estimated_duration_minutes: int = Field(
        ge=15,
        le=240,
        description="예상 체류시간과 이동시간을 합한 코스 총시간(분)",
    )
    estimated_travel_minutes: int = Field(
        ge=0,
        description="직선거리와 도보 속도로 계산한 예상 이동시간(분)",
    )
    estimated_distance_km: float = Field(
        ge=0,
        description="현재 위치와 장소 간 직선거리 합계(km)",
    )
    locations: list[RecommendedLocation] = Field(min_length=1, max_length=4)
    warnings: list[str]


class AppliedConditions(APIModel):
    recommendation_mode: RecommendationMode
    available_minutes: AvailableMinutes
    companion: Companion
    mood: Mood
    district: SeoulDistrict | None = None
    current_location: CurrentLocation | None = None


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
    candidate_course_id: str = Field(min_length=1, max_length=40)


class AICourseSelection(APIModel):
    model_config = ConfigDict(extra="forbid")

    recommendations: list[AICourse] = Field(min_length=3, max_length=3)
