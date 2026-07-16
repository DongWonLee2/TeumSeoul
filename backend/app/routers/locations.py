from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.location import LocationQuery
from app.schemas.common import DataResponse
from app.schemas.location import LocationDetail, LocationSummary
from app.services.location import get_location_detail, get_locations

router = APIRouter(prefix="/locations", tags=["장소"])


@router.get(
    "",
    response_model=DataResponse[list[LocationSummary]],
    summary="장소 목록 조회",
    description=(
        "서울 장소 6,517건을 검색합니다. 키워드·콘텐츠 유형·자치구·이미지 유무·"
        "원천 데이터 갱신연도를 조합해 필터링할 수 있습니다."
    ),
    responses={422: {"description": "쿼리 파라미터가 허용 범위를 벗어남"}},
)
def list_locations(
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[
        str | None,
        Query(max_length=100, description="장소명·주소·자치구 검색어", examples=["서울숲"]),
    ] = None,
    content_type_id: Annotated[
        int | None,
        Query(description="콘텐츠 유형 ID: 12, 14, 15, 25, 28, 32, 38", examples=[12]),
    ] = None,
    district: Annotated[
        str | None,
        Query(max_length=20, description="서울 자치구", examples=["성동구"]),
    ] = None,
    has_image: Annotated[
        bool | None,
        Query(description="대표 이미지 보유 여부"),
    ] = None,
    modified_year: Annotated[
        int | None,
        Query(ge=1900, le=2100, description="원천 데이터 최종 수정 연도", examples=[2026]),
    ] = None,
    sort: Annotated[
        Literal["recent", "title"],
        Query(description="정렬: recent=최근 갱신순, title=장소명순"),
    ] = "recent",
    page: Annotated[int, Query(ge=1, description="페이지 번호(1부터 시작)")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="페이지당 결과 수(최대 100)")] = 20,
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
    description=(
        "장소 기본 정보, 원천 데이터 주의사항과 반경 3km 내 주변 장소 최대 5건을 "
        "반환합니다. 주변 거리는 실제 이동거리가 아닌 근사 직선거리입니다."
    ),
    responses={404: {"description": "장소를 찾을 수 없음"}},
)
def retrieve_location(
    db: Annotated[Session, Depends(get_db)],
    location_id: Annotated[int, Path(ge=1, description="서비스 내부 장소 ID", examples=[101])],
) -> DataResponse[LocationDetail]:
    return DataResponse(data=get_location_detail(db, location_id))
