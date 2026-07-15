import json
import math
import re
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from app.core.constants import CONTENT_TYPES
from app.core.exceptions import AppException, ResourceNotFoundError
from app.models.location import Location
from app.repositories.location import (
    LocationQuery,
    find_location_by_id,
    find_locations,
    find_nearby_candidates,
    find_related_posts,
)
from app.schemas.common import PaginationMeta
from app.schemas.location import (
    LocationDetail,
    LocationSummary,
    NearbyLocationSummary,
    RelatedPostSummary,
)

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
NEARBY_RADIUS_KM = 3.0
NEARBY_RESULT_LIMIT = 5
NEARBY_CANDIDATE_LIMIT = 200
RELATED_POST_LIMIT = 5
EARTH_RADIUS_KM = 6371.0088


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


def get_locations(
    db: Session,
    query: LocationQuery,
) -> tuple[list[LocationSummary], PaginationMeta]:
    if query.content_type_id is not None and query.content_type_id not in CONTENT_TYPES:
        raise AppException(
            status_code=422,
            detail="지원하지 않는 콘텐츠 유형입니다.",
            code="INVALID_QUERY_PARAMETER",
        )

    normalized_query = LocationQuery(
        q=_optional_text(query.q),
        content_type_id=query.content_type_id,
        district=_optional_text(query.district),
        has_image=query.has_image,
        modified_year=query.modified_year,
        sort=query.sort,
        page=query.page,
        size=query.size,
    )
    locations, total_items = find_locations(db, normalized_query)
    total_pages = math.ceil(total_items / query.size) if total_items else 0
    return (
        [_to_location_summary(location) for location in locations],
        PaginationMeta(
            page=query.page,
            size=query.size,
            total_items=total_items,
            total_pages=total_pages,
        ),
    )


def get_location_detail(db: Session, location_id: int) -> LocationDetail:
    location = find_location_by_id(db, location_id)
    if location is None:
        raise ResourceNotFoundError(
            detail="장소를 찾을 수 없습니다.",
            code="LOCATION_NOT_FOUND",
        )

    summary = _to_location_summary(location)
    detail_warnings = [
        *summary.warnings,
        "운영시간은 제공 데이터에 없어 방문 전 확인이 필요합니다.",
    ]
    related_posts, related_post_count = find_related_posts(
        db,
        location_id=location.id,
        limit=RELATED_POST_LIMIT,
    )
    return LocationDetail(
        **summary.model_dump(exclude={"warnings"}),
        thumbnail_url=location.thumbnail_url,
        telephone=location.telephone,
        copyright_code=location.copyright_code,
        class_codes=_class_codes(location),
        warnings=detail_warnings,
        related_post_count=related_post_count,
        related_posts=[RelatedPostSummary.model_validate(post) for post in related_posts],
        nearby_locations=_get_nearby_locations(db, location),
    )


def _to_location_summary(location: Location) -> LocationSummary:
    return LocationSummary(
        id=location.id,
        source_content_id=location.source_content_id,
        content_type_id=location.content_type_id,
        content_type=CONTENT_TYPES[location.content_type_id]["name"],
        title=location.title,
        address=location.address,
        district=location.district,
        latitude=location.latitude,
        longitude=location.longitude,
        image_url=location.image_url,
        source_modified_at=location.source_modified_at,
        warnings=_location_warnings(location),
    )


def _location_warnings(location: Location) -> list[str]:
    warnings: list[str] = []
    if location.address is None:
        warnings.append("주소 정보 없음")
    if location.image_url is None:
        warnings.append("대표 이미지 없음")
    if location.latitude is None or location.longitude is None:
        warnings.append("정확한 위치 정보 없음")
    if location.content_type_id == 25:
        warnings.append("대표 위치이며 전체 이동 경로가 아님")
    elif location.content_type_id == 15:
        warnings.append("행사 일정은 제공 데이터로 확인할 수 없음")
    elif location.content_type_id == 32:
        warnings.append("가격·객실·예약 가능 여부 미제공")
    return warnings


def _class_codes(location: Location) -> list[str]:
    return [
        code
        for code in (
            location.category_code_1,
            location.category_code_2,
            location.category_code_3,
            location.classification_code_1,
            location.classification_code_2,
            location.classification_code_3,
        )
        if code
    ]


def _get_nearby_locations(db: Session, location: Location) -> list[NearbyLocationSummary]:
    if location.latitude is None or location.longitude is None:
        return []

    latitude_delta = NEARBY_RADIUS_KM / 111.0
    longitude_scale = max(math.cos(math.radians(location.latitude)), 0.01)
    longitude_delta = NEARBY_RADIUS_KM / (111.0 * longitude_scale)
    candidates = find_nearby_candidates(
        db,
        location_id=location.id,
        latitude=location.latitude,
        longitude=location.longitude,
        latitude_delta=latitude_delta,
        longitude_delta=longitude_delta,
        candidate_limit=NEARBY_CANDIDATE_LIMIT,
    )

    results: list[tuple[Location, float]] = []
    for candidate in candidates:
        if candidate.latitude is None or candidate.longitude is None:
            continue
        distance = _haversine_distance_km(
            location.latitude,
            location.longitude,
            candidate.latitude,
            candidate.longitude,
        )
        if distance <= NEARBY_RADIUS_KM:
            results.append((candidate, distance))

    results.sort(key=lambda result: (result[1], result[0].id))
    return [
        NearbyLocationSummary(
            id=candidate.id,
            title=candidate.title,
            content_type=CONTENT_TYPES[candidate.content_type_id]["name"],
            distance_km=round(distance, 2),
        )
        for candidate, distance in results[:NEARBY_RESULT_LIMIT]
    ]


def _haversine_distance_km(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    latitude_delta = math.radians(latitude_2 - latitude_1)
    longitude_delta = math.radians(longitude_2 - longitude_1)
    latitude_1_radians = math.radians(latitude_1)
    latitude_2_radians = math.radians(latitude_2)
    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(latitude_1_radians)
        * math.cos(latitude_2_radians)
        * math.sin(longitude_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(haversine))
