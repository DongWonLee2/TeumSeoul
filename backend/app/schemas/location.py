from datetime import datetime

from pydantic import Field

from app.schemas.common import APIModel


class LocationSummary(APIModel):
    id: int = Field(description="서비스 내부 장소 ID", examples=[101])
    source_content_id: str = Field(description="TourAPI 원본 콘텐츠 ID", examples=["128611"])
    content_type_id: int = Field(description="TourAPI 콘텐츠 유형 ID", examples=[12])
    content_type: str = Field(description="콘텐츠 유형 한국어명", examples=["관광지"])
    title: str = Field(description="장소명", examples=["서울숲"])
    address: str | None = Field(description="상세 주소", examples=["서울특별시 성동구 뚝섬로 273"])
    district: str | None = Field(description="서울 자치구", examples=["성동구"])
    latitude: float | None = Field(description="WGS84 위도", examples=[37.5430715815])
    longitude: float | None = Field(description="WGS84 경도", examples=[127.041798446])
    image_url: str | None = Field(description="저작권 코드가 확인된 대표 이미지 URL")
    source_modified_at: datetime = Field(description="원천 데이터 최종 수정 시각")
    warnings: list[str] = Field(
        default_factory=list,
        description="원천 데이터의 결측·제약에 대한 안내",
    )


class RelatedPostSummary(APIModel):
    id: int = Field(description="게시글 ID")
    title: str = Field(description="게시글 제목")
    category: str = Field(description="게시글 카테고리")
    status_tag: str | None = Field(description="현장 상태 태그")
    created_at: datetime = Field(description="게시글 작성 시각")


class NearbyLocationSummary(APIModel):
    id: int = Field(description="주변 장소 ID")
    title: str = Field(description="주변 장소명")
    content_type: str = Field(description="주변 장소 유형")
    distance_km: float = Field(ge=0, description="Haversine 근사 직선거리(km)")


class LocationDetail(LocationSummary):
    thumbnail_url: str | None = Field(description="저작권 코드가 확인된 썸네일 URL")
    telephone: str | None = Field(description="원천 데이터 제공 전화번호")
    copyright_code: str | None = Field(description="원천 이미지 저작권 구분 코드")
    class_codes: list[str] = Field(default_factory=list, description="원천 분류 코드 목록")
    related_post_count: int = Field(default=0, ge=0, description="연결된 게시글 수")
    related_posts: list[RelatedPostSummary] = Field(
        default_factory=list,
        description="작성일시 내림차순 최근 연결 게시글 최대 5건",
    )
    nearby_locations: list[NearbyLocationSummary] = Field(
        default_factory=list,
        description="반경 3km 내 가까운 장소 최대 5건",
    )
