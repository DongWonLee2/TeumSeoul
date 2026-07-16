from pydantic import Field

from app.schemas.common import APIModel


class ContentTypeOption(APIModel):
    id: int = Field(description="TourAPI 콘텐츠 유형 ID", examples=[12])
    code: str = Field(description="프런트엔드용 영문 코드", examples=["tourist_attraction"])
    name: str = Field(description="콘텐츠 유형 한국어명", examples=["관광지"])


class RecommendationOptions(APIModel):
    available_minutes: list[int] = Field(description="선택 가능한 여유 시간(분)")
    companions: list[str] = Field(description="선택 가능한 동행 유형")
    moods: list[str] = Field(description="선택 가능한 분위기")


class Metadata(APIModel):
    content_types: list[ContentTypeOption] = Field(description="장소 콘텐츠 유형 7종")
    districts: list[str] = Field(description="현재 장소 데이터에 존재하는 서울 자치구")
    post_categories: list[str] = Field(description="게시글 작성 시 선택 가능한 카테고리")
    status_tags: list[str] = Field(description="게시글 현장 상태 태그")
    status_tags_by_category: dict[str, list[str]] = Field(
        description="게시글 카테고리별 선택 가능한 상태 태그"
    )
    recommendation_options: RecommendationOptions = Field(description="상황형 추천 입력 옵션")
