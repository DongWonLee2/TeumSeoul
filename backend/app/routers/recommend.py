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
        "nearby 모드는 현재 위치 주변에서, district 모드는 지정 자치구 내부에서 후보를 "
        "검색합니다. 시간·동행자·분위기를 바탕으로 장소별 예상 "
        "체류시간·이동거리·경험 다양성을 검증한 코스 최대 3개를 생성합니다. AI는 검증된 "
        "코스 중 사용자 조건에 맞는 결과를 큐레이션하며, 사용할 수 없거나 결과 검증에 "
        "실패하면 서버가 선택한 검증 코스로 자동 전환합니다."
    ),
    responses={422: {"description": "추천 조건이 허용값과 일치하지 않음"}},
)
def create_situational_recommendation(
    request: SituationalRecommendationRequest,
    db: Annotated[Session, Depends(get_db)],
) -> SituationalRecommendationResponse:
    return recommend_situational(db, request)
