from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.map import MapBounds
from app.schemas.map import MapLocationsResponse
from app.services.map import get_map_locations

router = APIRouter(prefix="/map", tags=["지도"])


@router.get(
    "/locations",
    response_model=MapLocationsResponse,
    summary="지도 영역 장소 조회",
    description=(
        "현재 지도 경계 안에 좌표가 존재하는 장소를 최대 300건 반환합니다. "
        "목록·상세 API보다 필드가 적은 지도 전용 경량 응답입니다."
    ),
    responses={
        400: {"description": "지도 경계값의 범위 또는 순서가 잘못됨"},
        422: {"description": "콘텐츠 유형 또는 limit이 올바르지 않음"},
    },
)
def list_map_locations(
    db: Annotated[Session, Depends(get_db)],
    south: Annotated[float, Query(description="남쪽 경계 위도", examples=[37.50])],
    west: Annotated[float, Query(description="서쪽 경계 경도", examples=[126.95])],
    north: Annotated[float, Query(description="북쪽 경계 위도", examples=[37.58])],
    east: Annotated[float, Query(description="동쪽 경계 경도", examples=[127.08])],
    content_type_ids: Annotated[
        str | None,
        Query(description="쉼표로 구분한 콘텐츠 유형 ID", examples=["12,14"]),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=300, description="최대 반환 수(기본·최대 300)"),
    ] = 300,
) -> MapLocationsResponse:
    return get_map_locations(
        db,
        bounds=MapBounds(south=south, west=west, north=north, east=east),
        content_type_ids=content_type_ids,
        limit=limit,
    )
