from dataclasses import dataclass
from datetime import datetime
from math import asin, cos, radians, sin, sqrt

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.location import Location
from app.models.post import Post


@dataclass(frozen=True)
class LocationCandidate:
    id: int
    content_type_id: int
    title: str
    address: str | None
    district: str | None
    latitude: float | None
    longitude: float | None
    source_modified_at: datetime | None


@dataclass(frozen=True)
class PostCandidate:
    id: int
    location_id: int | None
    title: str
    content: str
    status_tag: str | None


def _location_columns():
    return (
        Location.id,
        Location.content_type_id,
        Location.title,
        Location.address,
        Location.district,
        Location.latitude,
        Location.longitude,
        Location.source_modified_at,
    )


def _to_location(row) -> LocationCandidate:
    return LocationCandidate(**dict(row._mapping))


def find_reference_location(db: Session, title: str) -> LocationCandidate | None:
    row = db.execute(
        select(*_location_columns())
        .where(Location.title.ilike(f"%{title}%"))
        .order_by(Location.title.asc(), Location.id.asc())
        .limit(1)
    ).first()
    return _to_location(row) if row is not None else None


def search_locations(
    db: Session,
    *,
    district: str | None,
    content_type_ids: tuple[int, ...],
    keywords: tuple[str, ...],
    reference: LocationCandidate | None,
    current_latitude: float | None,
    current_longitude: float | None,
    limit: int,
) -> list[LocationCandidate]:
    statement = select(*_location_columns())
    conditions = []
    if district:
        conditions.append(Location.district == district)
    if content_type_ids:
        conditions.append(Location.content_type_id.in_(content_type_ids))
    if keywords:
        keyword_conditions = []
        for keyword in keywords:
            pattern = f"%{keyword}%"
            keyword_conditions.extend(
                (Location.title.ilike(pattern), Location.address.ilike(pattern))
            )
        conditions.append(or_(*keyword_conditions))

    center_latitude = current_latitude
    center_longitude = current_longitude
    if reference and reference.latitude is not None and reference.longitude is not None:
        center_latitude = reference.latitude
        center_longitude = reference.longitude
        conditions.extend(
            (
                Location.id != reference.id,
                Location.latitude.between(center_latitude - 0.08, center_latitude + 0.08),
                Location.longitude.between(center_longitude - 0.1, center_longitude + 0.1),
            )
        )
    elif center_latitude is not None and center_longitude is not None:
        conditions.extend(
            (
                Location.latitude.between(center_latitude - 0.08, center_latitude + 0.08),
                Location.longitude.between(center_longitude - 0.1, center_longitude + 0.1),
            )
        )

    if conditions:
        statement = statement.where(*conditions)
    fetch_limit = min(max(limit * 10, 30), 100)
    statement = statement.order_by(
        Location.source_modified_at.desc(), Location.id.asc()
    ).limit(fetch_limit)
    candidates = [_to_location(row) for row in db.execute(statement)]

    if center_latitude is not None and center_longitude is not None:
        candidates.sort(
            key=lambda item: _distance_km(
                center_latitude,
                center_longitude,
                item.latitude,
                item.longitude,
            )
        )
    return _balance_content_types(candidates, limit)


def search_posts(
    db: Session,
    *,
    location_ids: tuple[int, ...],
    keywords: tuple[str, ...],
    limit: int = 3,
) -> list[PostCandidate]:
    statement = select(Post.id, Post.location_id, Post.title, Post.content, Post.status_tag)
    conditions = []
    if location_ids:
        conditions.append(Post.location_id.in_(location_ids))
    if keywords:
        keyword_conditions = []
        for keyword in keywords:
            pattern = f"%{keyword}%"
            keyword_conditions.extend((Post.title.ilike(pattern), Post.content.ilike(pattern)))
        conditions.append(or_(*keyword_conditions))
    if conditions:
        statement = statement.where(or_(*conditions))
    else:
        return []
    rows = db.execute(statement.order_by(Post.created_at.desc(), Post.id.desc()).limit(limit))
    return [PostCandidate(**dict(row._mapping)) for row in rows]


def _balance_content_types(
    candidates: list[LocationCandidate], limit: int
) -> list[LocationCandidate]:
    selected: list[LocationCandidate] = []
    seen_types: set[int] = set()
    for candidate in candidates:
        if candidate.content_type_id not in seen_types:
            selected.append(candidate)
            seen_types.add(candidate.content_type_id)
            if len(selected) == limit:
                return selected
    selected_ids = {candidate.id for candidate in selected}
    for candidate in candidates:
        if candidate.id not in selected_ids:
            selected.append(candidate)
            if len(selected) == limit:
                break
    return selected


def _distance_km(
    latitude: float,
    longitude: float,
    other_latitude: float | None,
    other_longitude: float | None,
) -> float:
    if other_latitude is None or other_longitude is None:
        return float("inf")
    lat1, lon1, lat2, lon2 = map(
        radians, (latitude, longitude, other_latitude, other_longitude)
    )
    delta_latitude = lat2 - lat1
    delta_longitude = lon2 - lon1
    value = (
        sin(delta_latitude / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(delta_longitude / 2) ** 2
    )
    return 6371.0 * 2 * asin(sqrt(value))
