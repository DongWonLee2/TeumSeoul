from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.models.location import Location
from app.models.post import Post


def location_exists(db: Session, location_id: int) -> bool:
    return db.scalar(select(Location.id).where(Location.id == location_id)) is not None


def get_post(db: Session, post_id: int) -> Post | None:
    return db.scalar(select(Post).where(Post.id == post_id))


def get_location_summary(db: Session, location_id: int) -> dict[str, object] | None:
    row = db.execute(
        select(Location.id, Location.title).where(Location.id == location_id)
    ).mappings().one_or_none()
    return dict(row) if row is not None else None


def get_location_detail(db: Session, location_id: int) -> dict[str, object] | None:
    row = db.execute(
        select(
            Location.id,
            Location.title,
            Location.address,
            Location.latitude,
            Location.longitude,
        ).where(Location.id == location_id)
    ).mappings().one_or_none()
    return dict(row) if row is not None else None


def list_posts(
    db: Session,
    *,
    q: str | None,
    category: str | None,
    status_tag: str | None,
    location_id: int | None,
    district: str | None,
    sort: str,
    page: int,
    size: int,
) -> tuple[list[Post], int]:
    statement = select(Post)
    count_statement = select(func.count()).select_from(Post)

    needs_location_join = bool(district or q)
    if needs_location_join:
        statement = statement.outerjoin(Location, Post.location_id == Location.id)
        count_statement = count_statement.outerjoin(Location, Post.location_id == Location.id)

    conditions = []
    if q:
        pattern = f"%{q}%"
        conditions.append(
            or_(
                Post.title.ilike(pattern),
                Post.content.ilike(pattern),
                Location.title.ilike(pattern),
            )
        )
    if category:
        conditions.append(Post.category == category)
    if status_tag:
        conditions.append(Post.status_tag == status_tag)
    if location_id is not None:
        conditions.append(Post.location_id == location_id)
    if district:
        conditions.append(Location.district == district)

    if conditions:
        statement = statement.where(*conditions)
        count_statement = count_statement.where(*conditions)

    order_by = (
        (Post.view_count.desc(), Post.created_at.desc(), Post.id.desc())
        if sort == "views"
        else (Post.created_at.desc(), Post.id.desc())
    )
    statement = statement.order_by(*order_by).offset((page - 1) * size).limit(size)
    return list(db.scalars(statement).unique()), int(db.scalar(count_statement) or 0)


def add_post(db: Session, post: Post) -> None:
    db.add(post)


def increment_view_count(db: Session, post_id: int) -> None:
    db.execute(
        update(Post).where(Post.id == post_id).values(view_count=Post.view_count + 1)
    )


def delete_post(db: Session, post: Post) -> None:
    db.delete(post)
