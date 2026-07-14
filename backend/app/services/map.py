import math

from sqlalchemy.orm import Session

from app.core.constants import CONTENT_TYPES
from app.core.exceptions import AppException
from app.repositories.map import MapBounds, find_locations_in_bounds
from app.schemas.map import MapLocationsResponse, MapLocationSummary, MapResponseMeta


def get_map_locations(
    db: Session,
    *,
    bounds: MapBounds,
    content_type_ids: str | None,
    limit: int,
) -> MapLocationsResponse:
    _validate_bounds(bounds)
    parsed_content_type_ids = _parse_content_type_ids(content_type_ids)
    locations, truncated = find_locations_in_bounds(
        db,
        bounds=bounds,
        content_type_ids=parsed_content_type_ids,
        limit=limit,
    )
    data = [
        MapLocationSummary(
            id=location.id,
            title=location.title,
            content_type_id=location.content_type_id,
            content_type=CONTENT_TYPES[location.content_type_id]["name"],
            district=location.district,
            latitude=location.latitude,
            longitude=location.longitude,
            thumbnail_url=location.thumbnail_url,
        )
        for location in locations
        if location.latitude is not None and location.longitude is not None
    ]
    return MapLocationsResponse(
        data=data,
        meta=MapResponseMeta(count=len(data), limit=limit, truncated=truncated),
    )


def _validate_bounds(bounds: MapBounds) -> None:
    coordinates = (bounds.south, bounds.west, bounds.north, bounds.east)
    if not all(math.isfinite(coordinate) for coordinate in coordinates):
        _raise_invalid_bounds("지도 경계값은 유한한 숫자여야 합니다.")
    if not (-90 <= bounds.south <= 90 and -90 <= bounds.north <= 90):
        _raise_invalid_bounds("위도는 -90 이상 90 이하여야 합니다.")
    if not (-180 <= bounds.west <= 180 and -180 <= bounds.east <= 180):
        _raise_invalid_bounds("경도는 -180 이상 180 이하여야 합니다.")
    if bounds.south >= bounds.north or bounds.west >= bounds.east:
        _raise_invalid_bounds("south는 north보다 작고 west는 east보다 작아야 합니다.")


def _parse_content_type_ids(value: str | None) -> set[int] | None:
    if value is None:
        return None
    parts = value.split(",")
    if not parts or any(not part.strip() for part in parts):
        _raise_invalid_query("content_type_ids는 쉼표로 구분한 유형 ID여야 합니다.")
    try:
        content_type_ids = {int(part.strip()) for part in parts}
    except ValueError as exc:
        raise AppException(
            status_code=422,
            detail="content_type_ids는 쉼표로 구분한 정수여야 합니다.",
            code="INVALID_QUERY_PARAMETER",
        ) from exc

    invalid_ids = content_type_ids.difference(CONTENT_TYPES)
    if invalid_ids:
        _raise_invalid_query(
            f"지원하지 않는 콘텐츠 유형입니다: {', '.join(map(str, sorted(invalid_ids)))}"
        )
    return content_type_ids


def _raise_invalid_bounds(detail: str) -> None:
    raise AppException(status_code=400, detail=detail, code="INVALID_BOUNDS")


def _raise_invalid_query(detail: str) -> None:
    raise AppException(status_code=422, detail=detail, code="INVALID_QUERY_PARAMETER")
