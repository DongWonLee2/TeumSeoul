import argparse
from pathlib import Path

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.services.location import (
    EXPECTED_LOCATION_COUNT,
    get_location_count,
    load_location_records,
    seed_location_records,
)

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "locations"


def seed_locations(data_dir: Path = DEFAULT_DATA_DIR, *, force: bool = False) -> bool:
    init_db()
    with SessionLocal() as db:
        if not force and get_location_count(db) == EXPECTED_LOCATION_COUNT:
            return False

        records = load_location_records(data_dir)
        seed_location_records(db, records)
        location_count = get_location_count(db)
        if location_count != EXPECTED_LOCATION_COUNT:
            db.rollback()
            raise RuntimeError(
                f"seed 후 장소 건수가 {EXPECTED_LOCATION_COUNT}건이 아닙니다: {location_count}"
            )
        db.commit()
        return True


def main() -> None:
    parser = argparse.ArgumentParser(description="서울 장소 원본 데이터를 SQLite에 적재합니다.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument(
        "--force",
        action="store_true",
        help="6,518건이 있어도 원본으로 갱신합니다.",
    )
    args = parser.parse_args()

    seeded = seed_locations(args.data_dir, force=args.force)
    print("장소 6,518건 적재 완료" if seeded else "장소 6,518건이 이미 있어 건너뜀")


if __name__ == "__main__":
    main()
