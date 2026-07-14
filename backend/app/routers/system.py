from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.db.session import get_db
from app.schemas.common import DataResponse
from app.schemas.system import HealthData

router = APIRouter(tags=["system"])


@router.get(
    "/health",
    response_model=DataResponse[HealthData],
    response_model_exclude_none=True,
    responses={503: {"description": "데이터베이스 연결 실패"}},
    summary="서버 및 데이터베이스 상태 확인",
)
def health_check(db: Annotated[Session, Depends(get_db)]) -> DataResponse[HealthData]:
    try:
        db.execute(text("SELECT 1"))
        location_count = 0
        if inspect(db.get_bind()).has_table("locations"):
            location_count = int(db.scalar(text("SELECT COUNT(*) FROM locations")) or 0)
    except SQLAlchemyError as exc:
        raise AppException(
            status_code=503,
            detail="데이터베이스 연결에 실패했습니다.",
            code="DATABASE_UNAVAILABLE",
        ) from exc

    return DataResponse(
        data=HealthData(
            status="ok",
            database="connected",
            location_count=location_count,
            timestamp=datetime.now().astimezone(),
        )
    )
