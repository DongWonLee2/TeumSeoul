"""BE2 소유 API의 집계 라우터.

posts, chat 라우터를 이 파일에만 연결합니다.
"""

from fastapi import APIRouter

from app.routers.posts import router as posts_router

router = APIRouter()
router.include_router(posts_router)
