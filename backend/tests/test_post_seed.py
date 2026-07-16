from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

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


def test_fresh_database_seeds_locations_before_community_posts() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        assert seed_locations_if_needed(db, LOCATION_DATA_DIR) is True
        assert seed_posts_if_needed(db, POST_DATA_PATH) is True
        assert get_location_count(db) == EXPECTED_LOCATION_COUNT
        assert get_post_count(db) == EXPECTED_POST_SEED_COUNT

    engine.dispose()
