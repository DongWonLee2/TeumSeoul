from fastapi import APIRouter

from app.routers.be1 import router as be1_router
from app.routers.be2 import router as be2_router
from app.routers.system import router as system_router

api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(be1_router)
api_router.include_router(be2_router)

