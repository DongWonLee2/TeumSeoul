from sqlalchemy.orm import Session

from app.core.constants import (
    AVAILABLE_MINUTES,
    COMPANIONS,
    CONTENT_TYPES,
    MOODS,
    POST_CATEGORIES,
    POST_STATUS_TAGS,
    POST_STATUS_TAGS_BY_CATEGORY,
)
from app.repositories.meta import find_districts
from app.schemas.meta import ContentTypeOption, Metadata, RecommendationOptions


def get_metadata(db: Session) -> Metadata:
    return Metadata(
        content_types=[
            ContentTypeOption(id=content_type_id, code=value["code"], name=value["name"])
            for content_type_id, value in CONTENT_TYPES.items()
        ],
        districts=find_districts(db),
        post_categories=list(POST_CATEGORIES),
        status_tags=list(POST_STATUS_TAGS),
        status_tags_by_category={
            category: list(status_tags)
            for category, status_tags in POST_STATUS_TAGS_BY_CATEGORY.items()
        },
        recommendation_options=RecommendationOptions(
            available_minutes=list(AVAILABLE_MINUTES),
            companions=list(COMPANIONS),
            moods=list(MOODS),
        ),
    )
