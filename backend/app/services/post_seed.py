import json
import secrets
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.location import Location
from app.models.post import Post
from app.schemas.post import PostCategory, PostStatusTag

EXPECTED_POST_SEED_COUNT = 20


class PostSeedError(RuntimeError):
    """커뮤니티 초기 데이터가 시드 계약을 만족하지 않을 때 발생합니다."""


class PostSeedRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed_key: str = Field(min_length=1, max_length=50)
    location_source_content_id: str = Field(min_length=1, max_length=32)
    category: PostCategory
    status_tag: PostStatusTag | None
    title: str = Field(min_length=2, max_length=100)
    content: str = Field(min_length=2, max_length=5000)
    visited_at: date | None
    view_count: int = Field(ge=0)
    created_at: datetime


class PostSeedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1]
    description: str = Field(min_length=1)
    posts: list[PostSeedRecord]


def get_post_count(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(Post)) or 0)


def load_post_seed_records(path: Path) -> list[PostSeedRecord]:
    try:
        payload = PostSeedPayload.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, json.JSONDecodeError) as exc:
        raise PostSeedError(f"커뮤니티 시드 파일을 읽을 수 없습니다: {path}") from exc

    if len(payload.posts) != EXPECTED_POST_SEED_COUNT:
        raise PostSeedError(
            f"커뮤니티 시드 건수가 {EXPECTED_POST_SEED_COUNT}건이 아닙니다: "
            f"{len(payload.posts)}"
        )
    seed_keys = [record.seed_key for record in payload.posts]
    if len(seed_keys) != len(set(seed_keys)):
        raise PostSeedError("커뮤니티 시드 키가 중복되었습니다.")
    return payload.posts


def seed_posts_if_needed(db: Session, path: Path) -> bool:
    """게시글이 없을 때만 배포 초기 커뮤니티 데이터를 한 번 적재합니다."""
    if get_post_count(db) > 0:
        return False

    records = load_post_seed_records(path)
    source_content_ids = {record.location_source_content_id for record in records}
    location_rows = db.execute(
        select(Location.source_content_id, Location.id).where(
            Location.source_content_id.in_(source_content_ids)
        )
    ).all()
    location_ids = {
        source_content_id: location_id for source_content_id, location_id in location_rows
    }
    missing_ids = sorted(source_content_ids - location_ids.keys())
    if missing_ids:
        raise PostSeedError(f"커뮤니티 시드 장소를 찾을 수 없습니다: {missing_ids}")

    posts = [
        Post(
            location_id=location_ids[record.location_source_content_id],
            category=record.category,
            status_tag=record.status_tag,
            title=record.title,
            content=record.content,
            password=secrets.token_urlsafe(18),
            visited_at=record.visited_at,
            view_count=record.view_count,
            created_at=record.created_at,
            updated_at=record.created_at,
        )
        for record in records
    ]
    try:
        db.add_all(posts)
        db.flush()
        if get_post_count(db) != EXPECTED_POST_SEED_COUNT:
            raise PostSeedError("커뮤니티 시드 후 게시글 건수가 일치하지 않습니다.")
        db.commit()
    except Exception:
        db.rollback()
        raise
    return True
