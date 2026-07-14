"""BE1 소유 API의 집계 라우터.

locations, map, recommend, meta 라우터를 이 파일에만 연결합니다.
"""

from fastapi import APIRouter

from app.routers.map import router as map_router
from app.routers.meta import router as meta_router

router = APIRouter()
router.include_router(map_router)
router.include_router(meta_router)

