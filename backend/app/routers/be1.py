"""BE1 소유 API의 집계 라우터.

locations, map, recommend, meta 라우터를 이 파일에만 연결합니다.
"""

from fastapi import APIRouter

from app.routers.locations import router as locations_router

router = APIRouter()
router.include_router(locations_router)

