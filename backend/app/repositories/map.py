from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.location import Location


@dataclass(frozen=True)
class MapBounds:
    south: float
    west: float
    north: float
    east: float


def find_locations_in_bounds(
    db: Session,
    *,
    bounds: MapBounds,
    content_type_ids: set[int] | None,
    limit: int,
) -> tuple[list[Location], bool]:
    statement = select(Location).where(
        Location.latitude.is_not(None),
        Location.longitude.is_not(None),
        Location.latitude.between(bounds.south, bounds.north),
        Location.longitude.between(bounds.west, bounds.east),
    )
    if content_type_ids:
        statement = statement.where(Location.content_type_id.in_(content_type_ids))

    locations = list(db.scalars(statement.order_by(Location.id.asc()).limit(limit + 1)).all())
    truncated = len(locations) > limit
    return locations[:limit], truncated
