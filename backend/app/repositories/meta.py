from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.location import Location


def find_districts(db: Session) -> list[str]:
    statement = (
        select(Location.district)
        .where(Location.district.is_not(None))
        .distinct()
        .order_by(Location.district.asc())
    )
    return [district for district in db.scalars(statement).all() if district]
