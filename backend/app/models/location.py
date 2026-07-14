from datetime import datetime

from sqlalchemy import Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Location(TimestampMixin, Base):
    __tablename__ = "locations"
    __table_args__ = (
        Index("ix_locations_content_type_district", "content_type_id", "district"),
        Index("ix_locations_coordinates", "latitude", "longitude"),
        Index("ix_locations_source_modified_at", "source_modified_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_content_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    content_type_id: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    address: Mapped[str | None] = mapped_column(String(500))
    district: Mapped[str | None] = mapped_column(String(20), index=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    image_url: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    telephone: Mapped[str | None] = mapped_column(String(255))
    copyright_code: Mapped[str | None] = mapped_column(String(20))
    category_code_1: Mapped[str | None] = mapped_column(String(20))
    category_code_2: Mapped[str | None] = mapped_column(String(20))
    category_code_3: Mapped[str | None] = mapped_column(String(20))
    classification_code_1: Mapped[str | None] = mapped_column(String(30))
    classification_code_2: Mapped[str | None] = mapped_column(String(30))
    classification_code_3: Mapped[str | None] = mapped_column(String(30))
    source_created_at: Mapped[datetime] = mapped_column(nullable=False)
    source_modified_at: Mapped[datetime] = mapped_column(nullable=False)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
