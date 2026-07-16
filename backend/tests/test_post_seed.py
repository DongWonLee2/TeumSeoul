from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.constants import POST_STATUS_TAGS_BY_CATEGORY
from app.db.base import Base
from app.models.location import Location
from app.models.post import Post
from app.services.location import (
    EXPECTED_LOCATION_COUNT,
    get_location_count,
    load_location_records,
    seed_location_records,
    seed_locations_if_needed,
)
from app.services.post_seed import (
    EXPECTED_POST_SEED_COUNT,
    get_post_count,
    load_post_seed_records,
    normalize_existing_post_contracts,
    seed_posts_if_needed,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
LOCATION_DATA_DIR = DATA_DIR / "locations"
POST_DATA_PATH = DATA_DIR / "posts" / "community_seed.json"


def test_post_seed_file_matches_contract_and_locations() -> None:
    post_records = load_post_seed_records(POST_DATA_PATH)
    location_source_ids = {
        record["source_content_id"] for record in load_location_records(LOCATION_DATA_DIR)
    }

    assert len(post_records) == EXPECTED_POST_SEED_COUNT
    assert len({record.seed_key for record in post_records}) == EXPECTED_POST_SEED_COUNT
    assert {record.category for record in post_records} == {"현장 제보", "방문 후기"}
    assert all(
        record.status_tag in POST_STATUS_TAGS_BY_CATEGORY[record.category]
        for record in post_records
    )
    assert all(
        record.location_source_content_id in location_source_ids for record in post_records
    )


def test_post_seed_is_idempotent_and_resolves_stable_location_ids() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    post_records = load_post_seed_records(POST_DATA_PATH)
    required_source_ids = {record.location_source_content_id for record in post_records}
    location_records = [
        record
        for record in load_location_records(LOCATION_DATA_DIR)
        if record["source_content_id"] in required_source_ids
    ]

    with Session(engine) as db:
        seed_location_records(db, location_records)
        db.commit()

        assert seed_posts_if_needed(db, POST_DATA_PATH) is True
        assert get_post_count(db) == EXPECTED_POST_SEED_COUNT
        posts = list(db.scalars(select(Post).order_by(Post.id)).all())
        assert all(4 <= len(post.password) <= 30 for post in posts)
        assert all("샘플" not in post.title and "더미" not in post.title for post in posts)

        joined_count = db.scalar(
            select(func.count())
            .select_from(Post)
            .join(Location, Post.location_id == Location.id)
            .where(Location.source_content_id.in_(required_source_ids))
        )
        assert joined_count == EXPECTED_POST_SEED_COUNT

        assert seed_posts_if_needed(db, POST_DATA_PATH) is False
        assert get_post_count(db) == EXPECTED_POST_SEED_COUNT

    engine.dispose()


def test_existing_posts_are_normalized_to_category_status_contract() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        db.add_all(
            [
                Post(
                    category="추천",
                    status_tag="사진 추천",
                    title="기존 추천글",
                    content="기존 추천 카테고리를 보정합니다.",
                    password="1234",
                ),
                Post(
                    category="방문 후기",
                    status_tag="혼잡",
                    title="기존 현장글",
                    content="상태 태그에 따라 카테고리를 보정합니다.",
                    password="1234",
                ),
                Post(
                    category="질문",
                    status_tag="알 수 없음",
                    title="기존 질문글",
                    content="알 수 없는 태그는 제거합니다.",
                    password="1234",
                ),
            ]
        )
        db.commit()

        assert normalize_existing_post_contracts(db) == 3
        posts = list(db.scalars(select(Post).order_by(Post.id)).all())
        assert [(post.category, post.status_tag) for post in posts] == [
            ("방문 후기", "사진 추천"),
            ("현장 제보", "혼잡"),
            ("방문 후기", None),
        ]
        assert normalize_existing_post_contracts(db) == 0

    engine.dispose()


def test_fresh_database_seeds_locations_before_community_posts() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        assert seed_locations_if_needed(db, LOCATION_DATA_DIR) is True
        assert seed_posts_if_needed(db, POST_DATA_PATH) is True
        assert get_location_count(db) == EXPECTED_LOCATION_COUNT
        assert get_post_count(db) == EXPECTED_POST_SEED_COUNT

    engine.dispose()
