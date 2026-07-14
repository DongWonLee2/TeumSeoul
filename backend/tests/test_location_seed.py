import json
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.location import Location
from app.services.location import (
    EXPECTED_LOCATION_COUNT,
    get_location_count,
    load_location_records,
    seed_location_records,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "locations"


def test_location_source_files_match_seed_contract() -> None:
    records = load_location_records(DATA_DIR)

    assert len(records) == EXPECTED_LOCATION_COUNT
    assert len({record["source_content_id"] for record in records}) == EXPECTED_LOCATION_COUNT
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
