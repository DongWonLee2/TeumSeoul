from dataclasses import dataclass
from typing import Literal

from sqlalchemy import Select, extract, func, or_, select
from sqlalchemy.orm import Session

from app.models.location import Location


@dataclass(frozen=True)
class LocationQuery:
    q: str | None = None
    content_type_id: int | None = None
    district: str | None = None
    has_image: bool | None = None
    modified_year: int | None = None
    sort: Literal["recent", "title"] = "recent"
    page: int = 1
    size: int = 20


def find_locations(db: Session, query: LocationQuery) -> tuple[list[Location], int]:
    statement = _apply_location_filters(select(Location), query)
    count_statement = _apply_location_filters(
        select(func.count()).select_from(Location),
        query,
    )

    if query.sort == "title":
        statement = statement.order_by(Location.title.asc(), Location.id.asc())
    else:
        statement = statement.order_by(Location.source_modified_at.desc(), Location.id.asc())

    statement = statement.offset((query.page - 1) * query.size).limit(query.size)
    locations = list(db.scalars(statement).all())
    total_items = int(db.scalar(count_statement) or 0)
    return locations, total_items


def find_location_by_id(db: Session, location_id: int) -> Location | None:
    return db.get(Location, location_id)


def find_recommendation_candidates(
    db: Session,
    *,
    content_type_ids: set[int],
    district: str | None,
    limit: int,
) -> list[Location]:
    statement = select(Location).where(
        Location.content_type_id.in_(content_type_ids),
        Location.latitude.is_not(None),
        Location.longitude.is_not(None),
    )
    if district:
        statement = statement.where(Location.district == district)
    statement = statement.order_by(Location.source_modified_at.desc(), Location.id.asc()).limit(
        limit
    )
    return list(db.scalars(statement).all())


def find_nearby_candidates(
    db: Session,
    *,
    location_id: int,
    latitude: float,
    longitude: float,
    latitude_delta: float,
    longitude_delta: float,
    candidate_limit: int,
) -> list[Location]:
    approximate_distance = (
        (Location.latitude - latitude) * (Location.latitude - latitude)
        + (Location.longitude - longitude) * (Location.longitude - longitude)
    )
    statement = (
        select(Location)
        .where(
            Location.id != location_id,
            Location.latitude.is_not(None),
            Location.longitude.is_not(None),
            Location.latitude.between(latitude - latitude_delta, latitude + latitude_delta),
            Location.longitude.between(longitude - longitude_delta, longitude + longitude_delta),
        )
        .order_by(approximate_distance.asc(), Location.id.asc())
        .limit(candidate_limit)
    )
    return list(db.scalars(statement).all())


def _apply_location_filters(
    statement: Select[tuple[Location]] | Select[tuple[int]],
    query: LocationQuery,
) -> Select[tuple[Location]] | Select[tuple[int]]:
    if query.q:
        statement = statement.where(
            or_(
                Location.title.contains(query.q, autoescape=True),
                Location.address.contains(query.q, autoescape=True),
                Location.district.contains(query.q, autoescape=True),
            )
        )
    if query.content_type_id is not None:
        statement = statement.where(Location.content_type_id == query.content_type_id)
    if query.district:
        statement = statement.where(Location.district == query.district)
    if query.has_image is True:
        statement = statement.where(Location.image_url.is_not(None))
    elif query.has_image is False:
        statement = statement.where(Location.image_url.is_(None))
    if query.modified_year is not None:
        statement = statement.where(
            extract("year", Location.source_modified_at) == query.modified_year
        )
    return statement
