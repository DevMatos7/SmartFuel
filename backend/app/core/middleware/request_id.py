import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or request_id
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def get_correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", getattr(request.state, "request_id", "unknown"))
