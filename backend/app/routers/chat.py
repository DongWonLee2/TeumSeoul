from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.common import DataResponse
from app.services.chat import handle_chat

router = APIRouter(prefix="/chat", tags=["챗봇"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=DataResponse[ChatResponse],
    response_model_exclude={"meta"},
    summary="검색 기반 서울 장소 챗봇",
    description=(
        "자연어 질문에서 지역·시간·동행·분위기 등의 조건을 추출하고 서울 공공 장소와 "
        "익명 커뮤니티 게시글을 먼저 검색합니다. OpenAI는 검색 후보 안에서만 답변하며, "
        "API 키 누락·타임아웃·응답 오류 시 DB 검색 결과로 안전하게 폴백합니다."
    ),
    responses={
        422: {"description": "챗봇 질문 또는 대화 내역이 올바르지 않음"},
        503: {"description": "DB 검색 서비스를 사용할 수 없음"},
    },
)
def chat(payload: ChatRequest, db: DbSession) -> DataResponse[ChatResponse]:
    return DataResponse(data=handle_chat(db, payload))
