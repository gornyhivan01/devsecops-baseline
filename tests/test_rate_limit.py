"""OWASP A04: Insecure Design — rate limiting на базе slowapi.

Проверяется сам механизм ограничения частоты запросов. Для end-to-end теста
собирается отдельное мини-приложение с жёстким лимитом (основное приложение в
тестах использует завышенные лимиты, чтобы не мешать массовым запросам).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.rate_limit import limiter


def _build_limited_app() -> FastAPI:
    limiter = Limiter(key_func=get_remote_address)
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.get("/limited")
    @limiter.limit("2/minute")
    async def limited(request: Request) -> dict[str, str]:
        return {"ok": "true"}

    return app


async def test_rate_limiting_is_enforced() -> None:
    app = _build_limited_app()
    transport = ASGITransport(app=app, client=("127.0.0.1", 50001))
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        first = await c.get("/limited")
        second = await c.get("/limited")
        third = await c.get("/limited")

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429


def test_auth_endpoints_are_rate_limited() -> None:
    """Точки входа аутентификации зарегистрированы в лимитере slowapi."""
    registered = set(limiter._route_limits.keys())
    assert "app.api.v1.endpoints.auth.login" in registered
    assert "app.api.v1.endpoints.auth.register" in registered
