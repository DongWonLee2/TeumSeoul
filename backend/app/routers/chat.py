from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.common import DataResponse
from app.services.chat import handle_chat

router = APIRouter(prefix="/chat", tags=["chat"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=DataResponse[ChatResponse],
    response_model_exclude={"meta"},
)
def chat(payload: ChatRequest, db: DbSession) -> DataResponse[ChatResponse]:
    return DataResponse(data=handle_chat(db, payload))
