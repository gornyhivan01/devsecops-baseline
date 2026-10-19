"""OWASP A05: Security Misconfiguration — security-заголовки и CORS."""

from __future__ import annotations

from httpx import AsyncClient

from app.core.security_headers import STRICT_CSP


async def test_security_headers_present(client: AsyncClient) -> None:
    response = await client.get("/health/live")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "default-src" in response.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["strict-transport-security"].startswith("max-age=")
    assert response.headers["cache-control"] == "no-store"


async def test_cors_allows_configured_origin(client: AsyncClient) -> None:
    response = await client.get("/health/live", headers={"Origin": "http://localhost:3000"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


async def test_cors_blocks_unknown_origin(client: AsyncClient) -> None:
    response = await client.get("/health/live", headers={"Origin": "http://evil.example.com"})
    assert "access-control-allow-origin" not in response.headers


async def test_api_csp_is_strict(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.headers["content-security-policy"] == STRICT_CSP


async def test_docs_served_without_external_cdn(client: AsyncClient) -> None:
    """Документация отдаётся офлайн: ассеты локальные, внешних CDN нет."""
    response = await client.get("/docs")
    assert response.status_code == 200
    assert "/static-offline-docs/swagger-ui-bundle.js" in response.text
    assert "cdn.jsdelivr.net" not in response.text
    assert "fastapi.tiangolo.com" not in response.text

    csp = response.headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "cdn.jsdelivr.net" not in csp


async def test_docs_static_asset_is_served(client: AsyncClient) -> None:
    """Локальный бандл Swagger UI доступен — нет runtime-зависимости от сети."""
    response = await client.get("/static-offline-docs/swagger-ui-bundle.js")
    assert response.status_code == 200
    assert len(response.content) > 0
