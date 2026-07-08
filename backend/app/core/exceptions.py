from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.core.middleware import get_request_id

logger = get_logger(__name__)


class AppError(Exception):
    def __init__(self, message: str, *, status_code: int = 400, code: str = "app_error") -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


def _error_payload(code: str, message: str, request_id: str) -> dict:
    return {"error": {"code": code, "message": message, "request_id": request_id}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        request_id = get_request_id(request)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(exc.code, exc.message, request_id),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = get_request_id(request)
        logger.exception("unhandled_error request_id=%s error=%s", request_id, type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content=_error_payload(
                "INTERNAL_SERVER_ERROR",
                "Ocorreu um erro inesperado.",
                request_id,
            ),
        )
