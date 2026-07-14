import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)


def error_response(status_code: int, detail: str, code: str) -> JSONResponse:
    payload = ErrorResponse(detail=detail, code=code)
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        del request
        return error_response(exc.status_code, exc.detail, exc.code)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        first_error = exc.errors()[0] if exc.errors() else None
        detail = (
            first_error.get("msg", "입력값이 올바르지 않습니다.")
            if first_error
            else "입력값이 올바르지 않습니다."
        )

        code = (
            "INVALID_POST_INPUT"
            if request.url.path.startswith("/api/posts")
            and request.method in {"POST", "PUT", "DELETE"}
            else "INVALID_QUERY_PARAMETER"
        )
        return error_response(422, str(detail), code)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        del request
        code = "RESOURCE_NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
        return error_response(exc.status_code, str(exc.detail), code)

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled server error: method=%s path=%s",
            request.method,
            request.url.path,
            exc_info=exc,
        )
        return error_response(500, "서버 내부 오류가 발생했습니다.", "INTERNAL_SERVER_ERROR")
