import json
import re
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from app.models.location import Location

EXPECTED_CONTENT_TYPES = {
    12: ("관광지", 783),
    14: ("문화시설", 566),
    15: ("축제공연행사", 201),
    25: ("여행코스", 51),
    28: ("레포츠", 126),
    32: ("숙박", 423),
    38: ("쇼핑", 4368),
}
EXPECTED_LOCATION_COUNT = sum(count for _, count in EXPECTED_CONTENT_TYPES.values())
SEOUL_LONGITUDE_RANGE = (126.0, 128.0)
SEOUL_LATITUDE_RANGE = (37.0, 38.0)
DISTRICT_PATTERN = re.compile(r"서울(?:특별시|특별)?\s+([가-힣]+구)(?:\s|$)")
DATETIME_FORMAT = "%Y%m%d%H%M%S"
UPSERT_BATCH_SIZE = 500


class LocationSeedError(RuntimeError):
    """원본 데이터가 seed 계약을 만족하지 않을 때 발생합니다."""


def get_location_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Location)) or 0


def seed_locations_if_needed(db: Session, data_dir: Path) -> bool:
    """데이터가 완전하면 건너뛰고, 아니면 전체 원본을 검증해 upsert합니다."""
    if get_location_count(db) == EXPECTED_LOCATION_COUNT:
        return False

    records = load_location_records(data_dir)
    seed_location_records(db, records)

    location_count = get_location_count(db)
    if location_count != EXPECTED_LOCATION_COUNT:
        db.rollback()
        raise LocationSeedError(
            f"seed 후 장소 건수가 {EXPECTED_LOCATION_COUNT}건이 아닙니다: {location_count}"
        )

    db.commit()
    return True


def load_location_records(data_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_content_ids: set[str] = set()

    for content_type_id, (content_type_name, expected_count) in EXPECTED_CONTENT_TYPES.items():
        path = data_dir / f"서울_{content_type_name}.json"
        if not path.is_file():
            raise LocationSeedError(f"원본 데이터 파일이 없습니다: {path}")

        payload = json.loads(path.read_text(encoding="utf-8"))
        items = payload.get("items")
        if not isinstance(items, list):
            raise LocationSeedError(f"items가 배열이 아닙니다: {path.name}")
        if payload.get("region") != "서울":
            raise LocationSeedError(f"서울 데이터가 아닙니다: {path.name}")
        if int(payload.get("contentTypeId", 0)) != content_type_id:
            raise LocationSeedError(f"콘텐츠 유형이 일치하지 않습니다: {path.name}")
        if payload.get("contentType") != content_type_name:
            raise LocationSeedError(f"콘텐츠 유형명이 일치하지 않습니다: {path.name}")
        if payload.get("total") != expected_count or len(items) != expected_count:
            raise LocationSeedError(
                f"원본 건수가 일치하지 않습니다: {path.name} "
                f"(선언 {payload.get('total')}, 실제 {len(items)}, 기대 {expected_count})"
            )

        for item in items:
            source_content_id = _required_text(item, "contentid", path.name)
            if source_content_id in seen_content_ids:
                raise LocationSeedError(f"중복 contentid입니다: {source_content_id}")
            seen_content_ids.add(source_content_id)

            item_content_type_id = int(_required_text(item, "contenttypeid", path.name))
            if item_content_type_id != content_type_id:
                raise LocationSeedError(
                    f"항목의 콘텐츠 유형이 일치하지 않습니다: {source_content_id}"
                )
            records.append(_normalize_location(item, content_type_id, path.name))

    if len(records) != EXPECTED_LOCATION_COUNT:
        raise LocationSeedError(
            f"전체 원본 건수가 {EXPECTED_LOCATION_COUNT}건이 아닙니다: {len(records)}"
        )
    return records


def seed_location_records(db: Session, records: list[dict[str, Any]]) -> None:
    update_columns = {
        column.name: getattr(insert(Location).excluded, column.name)
        for column in Location.__table__.columns
        if column.name not in {"id", "source_content_id", "created_at"}
    }
    statement = insert(Location).on_conflict_do_update(
        index_elements=[Location.source_content_id],
        set_=update_columns,
    )
    try:
        for batch in _batched(records, UPSERT_BATCH_SIZE):
            db.execute(statement, batch)
        db.flush()
    except Exception:
        db.rollback()
        raise


def _normalize_location(
    item: dict[str, Any], content_type_id: int, source_name: str
) -> dict[str, Any]:
    address = _combine_address(item.get("addr1"), item.get("addr2"))
    longitude, latitude = _coordinates_or_none(item.get("mapx"), item.get("mapy"))
    copyright_code = _optional_text(item.get("cpyrhtDivCd"))

    return {
        "source_content_id": _required_text(item, "contentid", source_name),
        "content_type_id": content_type_id,
        "title": _required_text(item, "title", source_name),
        "address": address,
        "district": _extract_district(address),
        "latitude": latitude,
        "longitude": longitude,
        "image_url": _optional_text(item.get("firstimage")) if copyright_code else None,
        "thumbnail_url": _optional_text(item.get("firstimage2")) if copyright_code else None,
        "telephone": _optional_text(item.get("tel")),
        "copyright_code": copyright_code,
        "category_code_1": _optional_text(item.get("cat1")),
        "category_code_2": _optional_text(item.get("cat2")),
        "category_code_3": _optional_text(item.get("cat3")),
        "classification_code_1": _optional_text(item.get("lclsSystm1")),
        "classification_code_2": _optional_text(item.get("lclsSystm2")),
        "classification_code_3": _optional_text(item.get("lclsSystm3")),
        "source_created_at": _parse_datetime(item.get("createdtime"), "createdtime"),
        "source_modified_at": _parse_datetime(item.get("modifiedtime"), "modifiedtime"),
        "raw_json": json.dumps(item, ensure_ascii=False, separators=(",", ":")),
    }


def _required_text(item: dict[str, Any], field: str, source_name: str) -> str:
    value = _optional_text(item.get(field))
    if value is None:
        raise LocationSeedError(f"필수 필드 {field}가 비었습니다: {source_name}")
    return value


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = " ".join(str(value).split())
    return normalized or None


def _combine_address(addr1: Any, addr2: Any) -> str | None:
    parts = [part for value in (addr1, addr2) if (part := _optional_text(value))]
    return " ".join(parts) or None


def _extract_district(address: str | None) -> str | None:
    if address is None:
        return None
    match = DISTRICT_PATTERN.search(address)
    return match.group(1) if match else None


def _coordinates_or_none(mapx: Any, mapy: Any) -> tuple[float | None, float | None]:
    try:
        longitude = float(mapx)
        latitude = float(mapy)
    except (TypeError, ValueError):
        return None, None

    if not (
        SEOUL_LONGITUDE_RANGE[0] <= longitude <= SEOUL_LONGITUDE_RANGE[1]
        and SEOUL_LATITUDE_RANGE[0] <= latitude <= SEOUL_LATITUDE_RANGE[1]
    ):
        return None, None
    return longitude, latitude


def _parse_datetime(value: Any, field: str) -> datetime:
    try:
        return datetime.strptime(str(value), DATETIME_FORMAT)
    except (TypeError, ValueError) as exc:
        raise LocationSeedError(f"{field} 형식이 올바르지 않습니다: {value}") from exc


def _batched(records: list[dict[str, Any]], size: int) -> Iterator[list[dict[str, Any]]]:
    for index in range(0, len(records), size):
        yield records[index : index + size]
