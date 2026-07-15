from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.core.constants import POST_CATEGORIES, POST_STATUS_TAGS
from app.core.exceptions import AppException
from app.db.session import get_db
from app.schemas.common import DataResponse
from app.schemas.post import (
    PostCreate,
    PostDelete,
    PostDetail,
    PostMutation,
    PostSummary,
    PostUpdate,
)
from app.services import post as post_service

router = APIRouter(prefix="/posts", tags=["게시글"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "",
    response_model=DataResponse[list[PostSummary]],
    summary="게시글 목록 조회",
    description=(
        "익명 커뮤니티 게시글을 검색합니다. 키워드·카테고리·상태 태그·연결 장소·"
        "자치구를 조합해 필터링하고 최신순 또는 조회수순으로 정렬할 수 있습니다."
    ),
    responses={422: {"description": "쿼리 파라미터가 허용 범위를 벗어남"}},
)
def list_posts(
    db: DbSession,
    q: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=500,
            description="게시글 제목·내용·연결 장소명 검색어",
            examples=["서울숲"],
        ),
    ] = None,
    category: Annotated[
        str | None,
        Query(description="게시글 카테고리", examples=["현장 제보"]),
    ] = None,
    status_tag: Annotated[
        str | None,
        Query(description="현장 상태 태그", examples=["혼잡"]),
    ] = None,
    location_id: Annotated[
        int | None,
        Query(ge=1, description="연결된 서비스 내부 장소 ID", examples=[101]),
    ] = None,
    district: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=20,
            description="연결 장소의 서울 자치구",
            examples=["성동구"],
        ),
    ] = None,
    sort: Annotated[
        Literal["recent", "views"],
        Query(description="정렬: recent=최신순, views=조회수순"),
    ] = "recent",
    page: Annotated[int, Query(ge=1, description="페이지 번호(1부터 시작)")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="페이지당 결과 수(최대 100)")] = 20,
) -> DataResponse[list[PostSummary]]:
    if category is not None and category not in POST_CATEGORIES:
        raise AppException(422, "허용되지 않은 게시글 카테고리입니다.", "INVALID_QUERY_PARAMETER")
    if status_tag is not None and status_tag not in POST_STATUS_TAGS:
        raise AppException(422, "허용되지 않은 상태 태그입니다.", "INVALID_QUERY_PARAMETER")
    posts, meta = post_service.list_posts(
        db,
        q=q,
        category=category,
        status_tag=status_tag,
        location_id=location_id,
        district=district,
        sort=sort,
        page=page,
        size=size,
    )
    return DataResponse(data=posts, meta=meta)


@router.post(
    "",
    response_model=DataResponse[PostMutation],
    response_model_exclude={"meta"},
    status_code=status.HTTP_201_CREATED,
    summary="게시글 작성",
    description=(
        "장소 연결 여부를 선택해 익명 게시글을 작성합니다. 비밀번호는 이후 수정·삭제에 "
        "사용하며 응답에는 포함하지 않습니다. 입력 HTML은 안전하게 이스케이프해 저장합니다."
    ),
    responses={
        404: {"description": "연결할 장소를 찾을 수 없음"},
        422: {"description": "게시글 입력값이 올바르지 않음"},
    },
)
def create_post(payload: PostCreate, db: DbSession) -> DataResponse[PostMutation]:
    return DataResponse(data=post_service.create_post(db, payload))


@router.get(
    "/{post_id}",
    response_model=DataResponse[PostDetail],
    response_model_exclude={"meta"},
    summary="게시글 상세 조회",
    description=(
        "게시글 본문과 연결 장소 상세 요약을 반환합니다. 상세 조회에 성공할 때마다 "
        "조회수가 1 증가합니다."
    ),
    responses={404: {"description": "게시글을 찾을 수 없음"}},
)
def get_post(
    post_id: Annotated[int, Path(ge=1, description="게시글 ID", examples=[15])],
    db: DbSession,
) -> DataResponse[PostDetail]:
    return DataResponse(data=post_service.get_post_detail(db, post_id))


@router.put(
    "/{post_id}",
    response_model=DataResponse[PostMutation],
    response_model_exclude={"meta"},
    summary="게시글 수정",
    description=(
        "작성 시 설정한 비밀번호를 검증한 뒤 게시글 내용을 수정합니다. 비밀번호 자체는 "
        "변경할 수 없으며 수정 요청에는 전체 게시글 필드를 전달해야 합니다."
    ),
    responses={
        403: {"description": "게시글 비밀번호가 일치하지 않음"},
        404: {"description": "게시글 또는 연결 장소를 찾을 수 없음"},
        422: {"description": "게시글 입력값이 올바르지 않음"},
    },
)
def update_post(
    post_id: Annotated[int, Path(ge=1, description="수정할 게시글 ID", examples=[15])],
    payload: PostUpdate,
    db: DbSession,
) -> DataResponse[PostMutation]:
    return DataResponse(data=post_service.update_post(db, post_id, payload))


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="게시글 삭제",
    description=(
        "작성 시 설정한 비밀번호를 검증한 뒤 게시글을 물리 삭제합니다. "
        "삭제 성공 시 응답 본문 없이 204를 반환합니다."
    ),
    responses={
        403: {"description": "게시글 비밀번호가 일치하지 않음"},
        404: {"description": "게시글을 찾을 수 없음"},
        422: {"description": "비밀번호 입력값이 올바르지 않음"},
    },
)
def delete_post(
    post_id: Annotated[int, Path(ge=1, description="삭제할 게시글 ID", examples=[15])],
    db: DbSession,
    payload: Annotated[PostDelete, Body(description="게시글 삭제 비밀번호")],
) -> Response:
    post_service.delete_post(db, post_id, payload.password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
