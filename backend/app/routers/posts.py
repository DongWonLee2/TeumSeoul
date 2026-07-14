from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.constants import POST_CATEGORIES, POST_STATUS_TAGS
from app.core.exceptions import AppException
from app.db.session import get_db
from app.schemas.common import DataResponse
from app.schemas.post import (
    PostCreate,
    PostDelete,
    PostDetail,
    PostMutation,
    PostSummary,
    PostUpdate,
)
from app.services import post as post_service

router = APIRouter(prefix="/posts", tags=["posts"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=DataResponse[list[PostSummary]])
def list_posts(
    db: DbSession,
    q: Annotated[str | None, Query(min_length=1, max_length=500)] = None,
    category: Annotated[str | None, Query()] = None,
    status_tag: Annotated[str | None, Query()] = None,
    location_id: Annotated[int | None, Query(ge=1)] = None,
    district: Annotated[str | None, Query(min_length=1, max_length=20)] = None,
    sort: Literal["recent", "views"] = "recent",
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DataResponse[list[PostSummary]]:
    if category is not None and category not in POST_CATEGORIES:
        raise AppException(422, "허용되지 않은 게시글 카테고리입니다.", "INVALID_QUERY_PARAMETER")
    if status_tag is not None and status_tag not in POST_STATUS_TAGS:
        raise AppException(422, "허용되지 않은 상태 태그입니다.", "INVALID_QUERY_PARAMETER")
    posts, meta = post_service.list_posts(
        db,
        q=q,
        category=category,
        status_tag=status_tag,
        location_id=location_id,
        district=district,
        sort=sort,
        page=page,
        size=size,
    )
    return DataResponse(data=posts, meta=meta)


@router.post(
    "",
    response_model=DataResponse[PostMutation],
    response_model_exclude={"meta"},
    status_code=status.HTTP_201_CREATED,
)
def create_post(payload: PostCreate, db: DbSession) -> DataResponse[PostMutation]:
    return DataResponse(data=post_service.create_post(db, payload))


@router.get("/{post_id}", response_model=DataResponse[PostDetail], response_model_exclude={"meta"})
def get_post(post_id: int, db: DbSession) -> DataResponse[PostDetail]:
    return DataResponse(data=post_service.get_post_detail(db, post_id))


@router.put(
    "/{post_id}",
    response_model=DataResponse[PostMutation],
    response_model_exclude={"meta"},
)
def update_post(
    post_id: int, payload: PostUpdate, db: DbSession
) -> DataResponse[PostMutation]:
    return DataResponse(data=post_service.update_post(db, post_id, payload))


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    db: DbSession,
    payload: Annotated[PostDelete, Body()],
) -> Response:
    post_service.delete_post(db, post_id, payload.password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
