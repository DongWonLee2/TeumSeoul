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
    str,
    AfterValidator(_normalize_and_escape),
    Field(
        min_length=2,
        max_length=100,
        description="게시글 제목(2~100자)",
        examples=["주말 오후에는 사람이 많았어요"],
    ),
]
SafeContent = Annotated[
    str,
    AfterValidator(_normalize_and_escape),
    Field(
        min_length=2,
        max_length=5000,
        description="게시글 본문(2~5,000자)",
        examples=["오후 3시쯤 주요 산책로가 혼잡했습니다."],
    ),
]
PostPassword = Annotated[
    str,
    Field(
        min_length=4,
        max_length=30,
        description="수정·삭제에 사용할 게시글 비밀번호(4~30자)",
        examples=["1234"],
    ),
]


class PostWriteFields(APIModel):
    location_id: int | None = Field(
        default=None,
        ge=1,
        description="연결할 서비스 내부 장소 ID; 자유글은 null",
        examples=[101],
    )
    category: PostCategory = Field(description="게시글 카테고리", examples=["현장 제보"])
    status_tag: PostStatusTag | None = Field(
        default=None,
        description="선택 현장 상태 태그",
        examples=["혼잡"],
    )
    title: SafeTitle
    content: SafeContent
    visited_at: date | None = Field(
        default=None,
        description="실제 장소 방문일",
        examples=["2026-07-13"],
    )

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
    id: int = Field(description="연결 장소 ID", examples=[101])
    title: str = Field(description="연결 장소명", examples=["서울숲"])


class PostLocationDetail(PostLocationSummary):
    address: str | None = Field(description="연결 장소 주소")
    latitude: float | None = Field(description="연결 장소 WGS84 위도")
    longitude: float | None = Field(description="연결 장소 WGS84 경도")


class PostSummary(APIModel):
    id: int = Field(description="게시글 ID", examples=[15])
    location: PostLocationSummary | None = Field(description="연결 장소 요약")
    category: str = Field(description="게시글 카테고리")
    status_tag: str | None = Field(description="현장 상태 태그")
    title: str = Field(description="게시글 제목")
    content_preview: str = Field(description="목록용 본문 미리보기(최대 100자)")
    visited_at: date | None = Field(description="실제 장소 방문일")
    view_count: int = Field(ge=0, description="상세 조회수")
    created_at: datetime = Field(description="게시글 작성 시각(UTC 기준 저장)")
    updated_at: datetime = Field(description="게시글 최종 수정 시각(UTC 기준 저장)")


class PostDetail(APIModel):
    id: int = Field(description="게시글 ID", examples=[15])
    location: PostLocationDetail | None = Field(description="연결 장소 상세 요약")
    category: str = Field(description="게시글 카테고리")
    status_tag: str | None = Field(description="현장 상태 태그")
    title: str = Field(description="게시글 제목")
    content: str = Field(description="게시글 전체 본문")
    visited_at: date | None = Field(description="실제 장소 방문일")
    view_count: int = Field(ge=0, description="상세 조회수")
    created_at: datetime = Field(description="게시글 작성 시각(UTC 기준 저장)")
    updated_at: datetime = Field(description="게시글 최종 수정 시각(UTC 기준 저장)")


class PostMutation(APIModel):
    id: int = Field(description="게시글 ID", examples=[15])
    location: PostLocationSummary | None = Field(description="연결 장소 요약")
    category: str = Field(description="게시글 카테고리")
    status_tag: str | None = Field(description="현장 상태 태그")
    title: str = Field(description="게시글 제목")
    content: str = Field(description="게시글 전체 본문")
    visited_at: date | None = Field(description="실제 장소 방문일")
    view_count: int = Field(ge=0, description="상세 조회수")
    created_at: datetime = Field(description="게시글 작성 시각(UTC 기준 저장)")
    updated_at: datetime = Field(description="게시글 최종 수정 시각(UTC 기준 저장)")
