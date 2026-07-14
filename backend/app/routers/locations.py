from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.location import LocationQuery
from app.schemas.common import DataResponse
from app.schemas.location import LocationDetail, LocationSummary
from app.services.location import get_location_detail, get_locations

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get(
    "",
    response_model=DataResponse[list[LocationSummary]],
    summary="장소 목록 조회",
)
def list_locations(
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    content_type_id: Annotated[int | None, Query()] = None,
    district: Annotated[str | None, Query(max_length=20)] = None,
    has_image: Annotated[bool | None, Query()] = None,
    modified_year: Annotated[int | None, Query(ge=1900, le=2100)] = None,
    sort: Annotated[Literal["recent", "title"], Query()] = "recent",
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DataResponse[list[LocationSummary]]:
    locations, meta = get_locations(
        db,
        LocationQuery(
            q=q,
            content_type_id=content_type_id,
            district=district,
            has_image=has_image,
            modified_year=modified_year,
            sort=sort,
            page=page,
            size=size,
        ),
    )
    return DataResponse(data=locations, meta=meta)


@router.get(
    "/{location_id}",
    response_model=DataResponse[LocationDetail],
    summary="장소 상세 조회",
)
def retrieve_location(
    db: Annotated[Session, Depends(get_db)],
    location_id: Annotated[int, Path(ge=1)],
) -> DataResponse[LocationDetail]:
    return DataResponse(data=get_location_detail(db, location_id))
