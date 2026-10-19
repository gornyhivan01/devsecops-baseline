"""Health-эндпоинты liveness и readiness."""

from __future__ import annotations

from httpx import AsyncClient


async def test_liveness(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


async def test_readiness(client: AsyncClient) -> None:
    response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"


async def test_openapi_schema_on_conventional_path(client: AsyncClient) -> None:
    """Схема должна отдаваться по стандартному /openapi.json (его ждут клиенты)."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    assert "/api/v1/items" in response.json()["paths"]
