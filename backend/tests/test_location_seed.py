import json
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.location import Location
from app.models.post import Post
from app.services.location import (
    EXCLUDED_SOURCE_CONTENT_IDS,
    EXPECTED_LOCATION_COUNT,
    get_location_count,
    load_location_records,
    seed_location_records,
    seed_locations_if_needed,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "locations"


def test_location_source_files_match_seed_contract() -> None:
    records = load_location_records(DATA_DIR)

    assert len(records) == EXPECTED_LOCATION_COUNT
    assert len({record["source_content_id"] for record in records}) == EXPECTED_LOCATION_COUNT
    assert not EXCLUDED_SOURCE_CONTENT_IDS.intersection(
        record["source_content_id"] for record in records
    )
    assert sum(record["latitude"] is None for record in records) == 13
    assert sum(record["longitude"] is None for record in records) == 13
    assert sum(record["address"] is None for record in records) == 51

    invalid_source = next(record for record in records if record["source_content_id"] == "2611568")
    raw = json.loads(invalid_source["raw_json"])
    assert invalid_source["latitude"] is None
    assert invalid_source["longitude"] is None
    assert raw["mapx"] == "117.9925662504"
    assert raw["mapy"] == "19.6944274800"


def test_location_seed_is_idempotent() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    records = load_location_records(DATA_DIR)

    with Session(engine) as db:
        seed_location_records(db, records)
        db.commit()
        assert get_location_count(db) == EXPECTED_LOCATION_COUNT

        seed_location_records(db, records)
        db.commit()
        assert get_location_count(db) == EXPECTED_LOCATION_COUNT
        duplicate_count = db.scalar(
            select(func.count())
            .select_from(Location)
            .group_by(Location.source_content_id)
            .having(func.count() > 1)
        )
        assert duplicate_count is None


def test_location_startup_removes_excluded_location_from_existing_db() -> None:
    engine = create_engine("sqlite://")
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    records = load_location_records(DATA_DIR)
    excluded_record = {
        **records[0],
        "source_content_id": "128933",
        "title": "삼각산",
    }

    with Session(engine) as db:
        seed_location_records(db, records)
        excluded_location = Location(**excluded_record)
        db.add(excluded_location)
        db.flush()
        linked_post = Post(
            location_id=excluded_location.id,
            category="질문",
            status_tag=None,
            title="제외 장소 연결 게시글",
            content="장소가 제외되어도 게시글은 유지됩니다.",
            password="1234",
        )
        db.add(linked_post)
        db.commit()
        linked_post_id = linked_post.id
        assert get_location_count(db) == EXPECTED_LOCATION_COUNT + 1

        changed = seed_locations_if_needed(db, DATA_DIR)

        assert changed is True
        assert get_location_count(db) == EXPECTED_LOCATION_COUNT
        assert db.scalar(
            select(Location.id).where(Location.source_content_id == "128933")
        ) is None
        assert db.get(Post, linked_post_id).location_id is None
