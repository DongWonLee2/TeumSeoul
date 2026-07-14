from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.schemas.common import ErrorResponse
from app.services.location import seed_locations_if_needed

LOCATION_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "locations"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    del app
    init_db()
    with SessionLocal() as db:
        seed_locations_if_needed(db, LOCATION_DATA_DIR)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="2.2.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        responses={
            404: {"model": ErrorResponse, "description": "리소스 없음"},
            422: {"model": ErrorResponse, "description": "입력값 검증 실패"},
            500: {"model": ErrorResponse, "description": "서버 내부 오류"},
        },
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)

    return app


configure_logging(settings.log_level)
app = create_app()
