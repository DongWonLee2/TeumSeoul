from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import DataResponse
from app.schemas.meta import Metadata
from app.services.meta import get_metadata

router = APIRouter(tags=["메타데이터"])


@router.get(
    "/meta",
    response_model=DataResponse[Metadata],
    summary="필터 및 추천 옵션 조회",
    description=(
        "프런트엔드가 사용하는 장소 유형, 실제 데이터의 자치구, 게시글 옵션과 "
        "상황형 추천 입력 옵션을 한 번에 반환합니다."
    ),
)
def retrieve_metadata(
    db: Annotated[Session, Depends(get_db)],
) -> DataResponse[Metadata]:
    return DataResponse(data=get_metadata(db))
