from datetime import date, datetime
from html import escape
from typing import Annotated, Literal

from pydantic import AfterValidator, Field, field_validator

from app.core.constants import POST_CATEGORIES, POST_STATUS_TAGS
from app.schemas.common import APIModel

PostCategory = Literal["현장 제보", "방문 후기", "질문", "추천"]
PostStatusTag = Literal[
    "혼잡",
    "여유",
    "공사",
    "이용 주의",
    "사진 추천",
    "가족 추천",
    "혼자 추천",
]


def _normalize_and_escape(value: str) -> str:
    return escape(value.strip(), quote=True)


SafeTitle = Annotated[
    str, AfterValidator(_normalize_and_escape), Field(min_length=2, max_length=100)
]
SafeContent = Annotated[
    str, AfterValidator(_normalize_and_escape), Field(min_length=2, max_length=5000)
]
PostPassword = Annotated[str, Field(min_length=4, max_length=30)]


class PostWriteFields(APIModel):
    location_id: int | None = Field(default=None, ge=1)
    category: PostCategory
    status_tag: PostStatusTag | None = None
    title: SafeTitle
    content: SafeContent
    visited_at: date | None = None

    @field_validator("category")
    @classmethod
    def validate_category_contract(cls, value: str) -> str:
        if value not in POST_CATEGORIES:
            raise ValueError("허용되지 않은 게시글 카테고리입니다.")
        return value

    @field_validator("status_tag")
    @classmethod
    def validate_status_tag_contract(cls, value: str | None) -> str | None:
        if value is not None and value not in POST_STATUS_TAGS:
            raise ValueError("허용되지 않은 상태 태그입니다.")
        return value


class PostCreate(PostWriteFields):
    password: PostPassword


class PostUpdate(PostWriteFields):
    password: PostPassword


class PostDelete(APIModel):
    password: PostPassword


class PostLocationSummary(APIModel):
    id: int
    title: str


class PostLocationDetail(PostLocationSummary):
    address: str | None
    latitude: float | None
    longitude: float | None


class PostSummary(APIModel):
    id: int
    location: PostLocationSummary | None
    category: str
    status_tag: str | None
    title: str
    content_preview: str
    visited_at: date | None
    view_count: int
    created_at: datetime
    updated_at: datetime


class PostDetail(APIModel):
    id: int
    location: PostLocationDetail | None
    category: str
    status_tag: str | None
    title: str
    content: str
    visited_at: date | None
    view_count: int
    created_at: datetime
    updated_at: datetime


class PostMutation(APIModel):
    id: int
    location: PostLocationSummary | None
    category: str
    status_tag: str | None
    title: str
    content: str
    visited_at: date | None
    view_count: int
    created_at: datetime
    updated_at: datetime
