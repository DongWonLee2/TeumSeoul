from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.recommendation import (
    SituationalRecommendationRequest,
    SituationalRecommendationResponse,
)
from app.services.recommendation import recommend_situational

router = APIRouter(prefix="/recommend", tags=["상황형 추천"])


@router.post(
    "/situational",
    response_model=SituationalRecommendationResponse,
    summary="상황형 서울 여행코스 추천",
    description=(
        "시간·동행자·분위기·희망 지역을 바탕으로 SQLite 후보를 먼저 검색한 뒤 "
        "후보 안에서만 코스 최대 3개를 생성합니다. OpenAI를 사용할 수 없거나 결과 검증에 "
        "실패하면 규칙 기반 코스로 자동 전환합니다."
    ),
    responses={422: {"description": "추천 조건이 허용값과 일치하지 않음"}},
)
def create_situational_recommendation(
    request: SituationalRecommendationRequest,
    db: Annotated[Session, Depends(get_db)],
) -> SituationalRecommendationResponse:
    return recommend_situational(db, request)
