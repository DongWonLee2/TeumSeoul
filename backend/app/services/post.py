from math import ceil

from sqlalchemy.orm import Session

from app.core.exceptions import AppException, ResourceNotFoundError
from app.models.mixins import utc_now
from app.models.post import Post
from app.repositories import post as post_repository
from app.schemas.common import PaginationMeta
from app.schemas.post import (
    PostCreate,
    PostDetail,
    PostLocationDetail,
    PostLocationSummary,
    PostMutation,
    PostSummary,
    PostUpdate,
)

CONTENT_PREVIEW_LENGTH = 100


def _location_summary(db: Session, location_id: int | None) -> PostLocationSummary | None:
    if location_id is None:
        return None
    location = post_repository.get_location_summary(db, location_id)
    return PostLocationSummary.model_validate(location) if location is not None else None


def _location_detail(db: Session, location_id: int | None) -> PostLocationDetail | None:
    if location_id is None:
        return None
    location = post_repository.get_location_detail(db, location_id)
    return PostLocationDetail.model_validate(location) if location is not None else None


def _preview(content: str) -> str:
    if len(content) <= CONTENT_PREVIEW_LENGTH:
        return content
    return f"{content[:CONTENT_PREVIEW_LENGTH]}..."


def to_summary(db: Session, post: Post) -> PostSummary:
    return PostSummary(
        id=post.id,
        location=_location_summary(db, post.location_id),
        category=post.category,
        status_tag=post.status_tag,
        title=post.title,
        content_preview=_preview(post.content),
        visited_at=post.visited_at,
        view_count=post.view_count,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


def to_detail(db: Session, post: Post) -> PostDetail:
    return PostDetail(
        id=post.id,
        location=_location_detail(db, post.location_id),
        category=post.category,
        status_tag=post.status_tag,
        title=post.title,
        content=post.content,
        visited_at=post.visited_at,
        view_count=post.view_count,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


def to_mutation(db: Session, post: Post) -> PostMutation:
    return PostMutation(
        id=post.id,
        location=_location_summary(db, post.location_id),
        category=post.category,
        status_tag=post.status_tag,
        title=post.title,
        content=post.content,
        visited_at=post.visited_at,
        view_count=post.view_count,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


def _ensure_location_exists(db: Session, location_id: int | None) -> None:
    if location_id is not None and not post_repository.location_exists(db, location_id):
        raise ResourceNotFoundError("요청한 장소를 찾을 수 없습니다.", "LOCATION_NOT_FOUND")


def _get_post_or_raise(db: Session, post_id: int) -> Post:
    post = post_repository.get_post(db, post_id)
    if post is None:
        raise ResourceNotFoundError("요청한 게시글을 찾을 수 없습니다.", "POST_NOT_FOUND")
    return post


def _verify_password(post: Post, password: str) -> None:
    if post.password != password:
        raise AppException(403, "게시글 비밀번호가 일치하지 않습니다.", "INVALID_POST_PASSWORD")


def list_posts(
    db: Session,
    *,
    q: str | None,
    category: str | None,
    status_tag: str | None,
    location_id: int | None,
    district: str | None,
    sort: str,
    page: int,
    size: int,
) -> tuple[list[PostSummary], PaginationMeta]:
    posts, total = post_repository.list_posts(
        db,
        q=q.strip() if q else None,
        category=category,
        status_tag=status_tag,
        location_id=location_id,
        district=district.strip() if district else None,
        sort=sort,
        page=page,
        size=size,
    )
    return [to_summary(db, post) for post in posts], PaginationMeta(
        page=page,
        size=size,
        total_items=total,
        total_pages=ceil(total / size),
    )


def create_post(db: Session, payload: PostCreate) -> PostMutation:
    _ensure_location_exists(db, payload.location_id)
    post = Post(**payload.model_dump())
    try:
        post_repository.add_post(db, post)
        db.commit()
        db.refresh(post)
        return to_mutation(db, post)
    except Exception:
        db.rollback()
        raise


def get_post_detail(db: Session, post_id: int) -> PostDetail:
    post = _get_post_or_raise(db, post_id)
    try:
        post_repository.increment_view_count(db, post_id)
        db.commit()
        db.refresh(post)
        return to_detail(db, post)
    except Exception:
        db.rollback()
        raise


def update_post(db: Session, post_id: int, payload: PostUpdate) -> PostMutation:
    post = _get_post_or_raise(db, post_id)
    _verify_password(post, payload.password)
    _ensure_location_exists(db, payload.location_id)
    changes = payload.model_dump(exclude={"password"})
    for field, value in changes.items():
        setattr(post, field, value)
    post.updated_at = utc_now()
    try:
        db.commit()
        db.refresh(post)
        return to_mutation(db, post)
    except Exception:
        db.rollback()
        raise


def delete_post(db: Session, post_id: int, password: str) -> None:
    post = _get_post_or_raise(db, post_id)
    _verify_password(post, password)
    try:
        post_repository.delete_post(db, post)
        db.commit()
    except Exception:
        db.rollback()
        raise
