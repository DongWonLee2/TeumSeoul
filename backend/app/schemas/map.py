from pydantic import Field

from app.schemas.common import APIModel


class MapLocationSummary(APIModel):
    id: int = Field(description="서비스 내부 장소 ID", examples=[101])
    title: str = Field(description="장소명", examples=["서울숲"])
    content_type_id: int = Field(description="TourAPI 콘텐츠 유형 ID", examples=[12])
    content_type: str = Field(description="콘텐츠 유형 한국어명", examples=["관광지"])
    district: str | None = Field(description="서울 자치구", examples=["성동구"])
    latitude: float = Field(description="WGS84 위도", examples=[37.5430715815])
    longitude: float = Field(description="WGS84 경도", examples=[127.041798446])
    thumbnail_url: str | None = Field(description="저작권 코드가 확인된 썸네일 URL")


class MapResponseMeta(APIModel):
    count: int = Field(ge=0, description="이번 응답의 장소 수")
    limit: int = Field(ge=1, le=300, description="요청에 적용된 최대 반환 수")
    truncated: bool = Field(description="조회 결과가 limit을 초과해 잘렸는지 여부")


class MapLocationsResponse(APIModel):
    data: list[MapLocationSummary]
    meta: MapResponseMeta
