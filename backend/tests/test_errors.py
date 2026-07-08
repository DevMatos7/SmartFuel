import pytest
from httpx import AsyncClient

from app.core.exceptions import AppError
from app.main import app


@pytest.mark.asyncio
async def test_app_error_format(client: AsyncClient) -> None:
    async def raise_app_error() -> None:
        raise AppError("Regra de domínio violada.", status_code=400, code="VALIDATION_ERROR")

    app.add_api_route("/_test/app-error", raise_app_error, methods=["GET"])
    try:
        response = await client.get("/_test/app-error")
    finally:
        app.router.routes = [
            route
            for route in app.router.routes
            if getattr(route, "path", None) != "/_test/app-error"
        ]

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["message"] == "Regra de domínio violada."
    assert payload["error"]["request_id"]


@pytest.mark.asyncio
async def test_internal_error_format(client: AsyncClient) -> None:
    from app.core.exceptions import _error_payload

    payload = _error_payload(
        "INTERNAL_SERVER_ERROR",
        "Ocorreu um erro inesperado.",
        "8c88244b-6e2e-4e98-8bfe-7fe13bcd32cc",
    )
    assert payload == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "Ocorreu um erro inesperado.",
            "request_id": "8c88244b-6e2e-4e98-8bfe-7fe13bcd32cc",
        }
    }
