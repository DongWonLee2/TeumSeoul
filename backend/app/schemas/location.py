from datetime import datetime

from pydantic import Field

from app.schemas.common import APIModel


class LocationSummary(APIModel):
    id: int
    source_content_id: str
    content_type_id: int
    content_type: str
    title: str
    address: str | None
    district: str | None
    latitude: float | None
    longitude: float | None
    image_url: str | None
    source_modified_at: datetime
    warnings: list[str] = Field(default_factory=list)


class RelatedPostSummary(APIModel):
    id: int
    title: str
    category: str
    status_tag: str | None
    created_at: datetime


class NearbyLocationSummary(APIModel):
    id: int
    title: str
    content_type: str
    distance_km: float = Field(ge=0)


class LocationDetail(LocationSummary):
    thumbnail_url: str | None
    telephone: str | None
    copyright_code: str | None
    class_codes: list[str] = Field(default_factory=list)
    related_post_count: int = Field(default=0, ge=0)
    related_posts: list[RelatedPostSummary] = Field(default_factory=list)
    nearby_locations: list[NearbyLocationSummary] = Field(default_factory=list)
